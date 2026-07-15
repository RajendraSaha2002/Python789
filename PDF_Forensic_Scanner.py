import re
import struct
import zlib
from pathlib import Path


class PDFError(Exception):
    pass


def shannon_entropy(data):
    if not data:
        return 0.0

    counts = [0] * 256

    for byte_value in data:
        counts[byte_value] += 1

    entropy = 0.0
    length = len(data)

    for count in counts:
        if count:
            probability = count / length
            entropy -= probability * (probability.bit_length() - 1)

    # Correct entropy calculation without external dependencies.
    import math
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts
        if count
    )


def read_pdf_string(data, start, limit=2048):
    if start >= len(data) or data[start:start + 1] != b"(":
        return ""

    result = bytearray()
    depth = 0
    escaped = False

    for index in range(start, min(start + limit, len(data))):
        character = data[index]

        if escaped:
            result.append(character)
            escaped = False
            continue

        if character == ord("\\"):
            escaped = True
            continue

        if character == ord("("):
            depth += 1

            if depth > 1:
                result.append(character)

            continue

        if character == ord(")"):
            depth -= 1

            if depth == 0:
                break

            result.append(character)
            continue

        result.append(character)

    return result.decode("latin-1", errors="replace")


def extract_pdf_objects(data):
    pattern = re.compile(
        rb"(?ms)(\d+)\s+(\d+)\s+obj\s*(.*?)\s*endobj"
    )

    objects = []

    for match in pattern.finditer(data):
        object_number = int(match.group(1))
        generation = int(match.group(2))
        raw_content = match.group(3)

        objects.append(
            {
                "object_number": object_number,
                "generation": generation,
                "offset": match.start(),
                "raw_content": raw_content,
                "raw_size": len(raw_content),
            }
        )

    return objects


def extract_stream_data(object_content):
    stream_match = re.search(
        rb"(?ms)\bstream\r?\n(.*?)\r?\nendstream",
        object_content,
    )

    if not stream_match:
        return None

    return stream_match.group(1)


def decompress_stream_if_possible(object_content, stream_data):
    if b"/FlateDecode" not in object_content:
        return stream_data, False

    try:
        return zlib.decompress(stream_data), True
    except zlib.error:
        return stream_data, False


def find_object_references(object_content):
    references = re.findall(
        rb"(\d+)\s+(\d+)\s+R",
        object_content,
    )

    return {
        int(object_number)
        for object_number, _ in references
    }


def analyse_invisible_text(stream_data):
    if not stream_data:
        return []

    text = stream_data.decode("latin-1", errors="replace")
    findings = []

    if re.search(r"\b0(?:\.0+)?\s+Tf\b", text):
        findings.append("Zero font-size text operator detected.")

    if re.search(
        r"\b(?:1(?:\.0+)?\s+){2}1(?:\.0+)?\s+rg\b",
        text,
    ):
        findings.append(
            "White non-stroking RGB text colour operator detected."
        )

    if re.search(r"\b3\s+Tr\b", text):
        findings.append(
            "Invisible text rendering mode (3 Tr) detected."
        )

    if re.search(r"\b7\s+Tr\b", text):
        findings.append(
            "Text clipping rendering mode (7 Tr) detected."
        )

    text_operators = re.findall(
        r"\((.{1,300}?)\)\s*Tj",
        text,
        flags=re.DOTALL,
    )

    suspicious_text = [
        value
        for value in text_operators
        if len(value.strip()) > 0
    ]

    if suspicious_text:
        findings.append(
            f"Text-show operators found: {len(suspicious_text)}"
        )

    return findings


def extract_metadata(data):
    metadata = {}

    fields = [
        "Title",
        "Author",
        "Subject",
        "Keywords",
        "Creator",
        "Producer",
        "CreationDate",
        "ModDate",
    ]

    for field in fields:
        pattern = rb"/" + field.encode("ascii") + rb"\s*\("

        match = re.search(pattern, data)

        if match:
            metadata[field] = read_pdf_string(
                data,
                match.end() - 1,
            )

    return metadata


def scan_pdf(pdf_path):
    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    data = path.read_bytes()

    if not data.startswith(b"%PDF-"):
        raise PDFError("File does not have a valid PDF header.")

    objects = extract_pdf_objects(data)

    if not objects:
        raise PDFError("No PDF objects could be parsed.")

    all_object_numbers = {
        item["object_number"]
        for item in objects
    }

    referenced_objects = set()
    stream_report = []
    suspicious_findings = []

    for item in objects:
        raw_content = item["raw_content"]
        referenced_objects.update(find_object_references(raw_content))

        stream_data = extract_stream_data(raw_content)

        if stream_data is None:
            continue

        decoded_stream, was_decompressed = decompress_stream_if_possible(
            raw_content,
            stream_data,
        )

        stream_entropy = shannon_entropy(stream_data)
        invisible_text = analyse_invisible_text(decoded_stream)

        stream_info = {
            "object": item["object_number"],
            "compressed": was_decompressed,
            "raw_stream_size": len(stream_data),
            "decoded_stream_size": len(decoded_stream),
            "entropy": round(stream_entropy, 4),
            "invisible_text_indicators": invisible_text,
        }

        stream_report.append(stream_info)

        if stream_entropy >= 7.5 and len(stream_data) > 256:
            suspicious_findings.append(
                f"Object {item['object_number']}: high-entropy stream "
                f"({stream_entropy:.2f})."
            )

        for finding in invisible_text:
            suspicious_findings.append(
                f"Object {item['object_number']}: {finding}"
            )

    comments = re.findall(
        rb"(?m)^%([^\r\n]{1,1000})",
        data,
    )

    non_header_comments = [
        comment.decode("latin-1", errors="replace")
        for comment in comments
        if not comment.startswith(b"PDF-")
    ]

    for comment in non_header_comments:
        if len(comment.strip()) > 20:
            suspicious_findings.append(
                "Long PDF comment detected."
            )

    root_match = re.search(
        rb"/Root\s+(\d+)\s+\d+\s+R",
        data,
    )

    root_object = (
        int(root_match.group(1))
        if root_match
        else None
    )

    possible_unused_objects = sorted(
        all_object_numbers
        - referenced_objects
        - ({root_object} if root_object else set())
    )

    metadata = extract_metadata(data)

    trailer_count = len(
        re.findall(rb"(?m)^trailer\b", data)
    )

    startxref_count = len(
        re.findall(rb"(?m)^startxref\b", data)
    )

    if trailer_count > 1 or startxref_count > 1:
        suspicious_findings.append(
            "Multiple trailer/startxref sections detected; "
            "incremental updates may be present."
        )

    if possible_unused_objects:
        suspicious_findings.append(
            f"{len(possible_unused_objects)} potentially unreferenced "
            f"object(s) detected."
        )

    return {
        "file": str(path.resolve()),
        "file_size_bytes": len(data),
        "pdf_version": data[:8].decode(
            "latin-1",
            errors="replace",
        ).strip(),
        "object_count": len(objects),
        "metadata": metadata,
        "pdf_comments": non_header_comments,
        "trailer_count": trailer_count,
        "startxref_count": startxref_count,
        "root_object": root_object,
        "possible_unused_objects": possible_unused_objects,
        "streams": stream_report,
        "suspicious_findings": suspicious_findings,
    }


def print_report(report):
    print("\n" + "=" * 72)
    print("PDF FORENSIC STEGANOGRAPHY SCAN REPORT")
    print("=" * 72)
    print(f"File: {report['file']}")
    print(f"PDF version: {report['pdf_version']}")
    print(f"Size: {report['file_size_bytes']} bytes")
    print(f"Objects parsed: {report['object_count']}")
    print(f"Trailer sections: {report['trailer_count']}")
    print(f"startxref sections: {report['startxref_count']}")

    print("\nMetadata:")

    if report["metadata"]:
        for key, value in report["metadata"].items():
            print(f"  {key}: {value}")
    else:
        print("  No standard metadata fields found.")

    print("\nComments:")

    if report["pdf_comments"]:
        for comment in report["pdf_comments"][:10]:
            print(f"  %{comment}")
    else:
        print("  No comments found.")

    print("\nPotentially unused objects:")

    if report["possible_unused_objects"]:
        print(
            "  "
            + ", ".join(
                str(number)
                for number in report["possible_unused_objects"][:50]
            )
        )
    else:
        print("  None identified.")

    print("\nStream analysis:")

    if report["streams"]:
        for stream in report["streams"]:
            print(
                f"  Object {stream['object']}: "
                f"{stream['raw_stream_size']} bytes, "
                f"entropy={stream['entropy']}, "
                f"Flate decoded={stream['compressed']}"
            )

            for finding in stream["invisible_text_indicators"]:
                print(f"    - {finding}")
    else:
        print("  No streams found.")

    print("\nSuspicious findings:")

    if report["suspicious_findings"]:
        for finding in report["suspicious_findings"]:
            print(f"  - {finding}")
    else:
        print("  No obvious hidden-content indicators found.")

    print(
        "\nNote: This is a forensic heuristic scanner. Findings require "
        "manual review and do not prove that hidden data exists."
    )


def main():
    print("PDF Metadata and Stream Forensic Scanner")
    print("This tool reads PDF structure without rendering the document.\n")

    file_path = input("Enter PDF file path: ").strip().strip('"')

    if not file_path:
        print("Error: no PDF file path entered.")
        return

    try:
        report = scan_pdf(file_path)
        print_report(report)

    except FileNotFoundError as error:
        print(f"File error: {error}")

    except PermissionError:
        print("Permission error: unable to read this PDF.")

    except PDFError as error:
        print(f"PDF parsing error: {error}")

    except OSError as error:
        print(f"File system error: {error}")

    except KeyboardInterrupt:
        print("\nScan cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()