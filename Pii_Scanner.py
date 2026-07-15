import csv
import json
import re
from pathlib import Path


PATTERNS = {
    "Email address": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "IPv4 address": re.compile(
        r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)"
        r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b"
    ),
    "IPv6 address": re.compile(
        r"\b(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{1,4}\b"
    ),
    "US SSN": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    ),
    "India Aadhaar": re.compile(
        r"\b\d{4}\s?\d{4}\s?\d{4}\b"
    ),
    "India PAN": re.compile(
        r"\b[A-Z]{5}\d{4}[A-Z]\b"
    ),
    "UK National Insurance": re.compile(
        r"\b(?!BG|GB|KN|NK|NT|TN|ZZ)"
        r"[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b",
        re.IGNORECASE,
    ),
    "Passport number": re.compile(
        r"\b[A-Z]{1,2}\d{6,9}\b"
    ),
    "Date of birth": re.compile(
        r"\b(?:0[1-9]|[12]\d|3[01])[-/]"
        r"(?:0[1-9]|1[0-2])[-/]"
        r"(?:19\d{2}|20\d{2})\b"
    ),
    "IBAN": re.compile(
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"
    ),
    "Phone number": re.compile(
        r"(?<!\w)"
        r"(?:\+?\d{1,3}[-.\s]?)?"
        r"(?:\(?\d{2,4}\)?[-.\s]?)"
        r"\d{3,4}[-.\s]?\d{3,4}"
        r"(?!\w)"
    ),
}


RESTRICTED_TYPES = {
    "Credit card number",
    "US SSN",
    "India Aadhaar",
    "India PAN",
    "UK National Insurance",
    "Passport number",
    "IBAN",
}

CONFIDENTIAL_TYPES = {
    "Email address",
    "Phone number",
    "Date of birth",
}

INTERNAL_TYPES = {
    "IPv4 address",
    "IPv6 address",
}


def luhn_valid(number):
    digits = re.sub(r"\D", "", number)

    if len(digits) < 13 or len(digits) > 19:
        return False

    total = 0
    reverse_digits = digits[::-1]

    for index, character in enumerate(reverse_digits):
        digit = int(character)

        if index % 2 == 1:
            digit *= 2

            if digit > 9:
                digit -= 9

        total += digit

    return total % 10 == 0


def find_credit_cards(text):
    candidates = re.findall(
        r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)",
        text,
    )

    valid_cards = []

    for candidate in candidates:
        digits = re.sub(r"\D", "", candidate)

        if luhn_valid(digits):
            valid_cards.append(candidate)

    return valid_cards


def redact_value(value):
    visible_characters = 4
    compact_value = value.strip()

    if len(compact_value) <= visible_characters:
        return "*" * len(compact_value)

    return (
        "*" * (len(compact_value) - visible_characters)
        + compact_value[-visible_characters:]
    )


def classify_finding(finding_type):
    if finding_type in RESTRICTED_TYPES:
        return "Restricted"

    if finding_type in CONFIDENTIAL_TYPES:
        return "Confidential"

    if finding_type in INTERNAL_TYPES:
        return "Internal"

    return "Public"


def scan_text(text, source_name):
    findings = []

    for finding_type, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            value = match.group(0)

            if finding_type == "IPv4 address":
                octets = value.split(".")

                if any(int(octet) > 255 for octet in octets):
                    continue

            findings.append(
                {
                    "type": finding_type,
                    "classification": classify_finding(finding_type),
                    "source": source_name,
                    "position": match.start(),
                    "value_redacted": redact_value(value),
                    "validation": "Pattern match",
                }
            )

    for value in find_credit_cards(text):
        position = text.find(value)

        findings.append(
            {
                "type": "Credit card number",
                "classification": "Restricted",
                "source": source_name,
                "position": position,
                "value_redacted": redact_value(value),
                "validation": "Luhn checksum valid",
            }
        )

    return findings


def redact_text(text):
    replacements = []

    for finding_type, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            replacements.append(
                (
                    match.start(),
                    match.end(),
                    f"[REDACTED:{finding_type}]",
                )
            )

    for value in find_credit_cards(text):
        start = text.find(value)

        if start >= 0:
            replacements.append(
                (
                    start,
                    start + len(value),
                    "[REDACTED:Credit card number]",
                )
            )

    replacements.sort(reverse=True)

    output = text

    for start, end, replacement in replacements:
        output = output[:start] + replacement + output[end:]

    return output


def scan_text_file(path):
    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    findings = scan_text(text, str(path))
    redacted_text = redact_text(text)

    return findings, redacted_text


def scan_csv_file(path):
    findings = []
    redacted_rows = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as file_handle:
        reader = csv.DictReader(file_handle)

        if not reader.fieldnames:
            raise ValueError("CSV does not contain column headers.")

        fieldnames = reader.fieldnames

        for row_number, row in enumerate(reader, start=2):
            clean_row = {}

            for column, value in row.items():
                value = value or ""
                source = f"{path} | row {row_number} | column {column}"

                cell_findings = scan_text(value, source)
                findings.extend(cell_findings)

                clean_row[column] = redact_text(value)

            redacted_rows.append(clean_row)

    return findings, fieldnames, redacted_rows


def calculate_overall_classification(findings):
    classifications = {
        finding["classification"]
        for finding in findings
    }

    if "Restricted" in classifications:
        return "Restricted"

    if "Confidential" in classifications:
        return "Confidential"

    if "Internal" in classifications:
        return "Internal"

    return "Public"


def create_gdpr_mapping_report(path, findings):
    categories = {}

    for finding in findings:
        finding_type = finding["type"]

        if finding_type not in categories:
            categories[finding_type] = {
                "classification": finding["classification"],
                "count": 0,
                "examples_redacted": [],
            }

        categories[finding_type]["count"] += 1

        example = finding["value_redacted"]

        if (
            example
            not in categories[finding_type]["examples_redacted"]
            and len(categories[finding_type]["examples_redacted"]) < 5
        ):
            categories[finding_type]["examples_redacted"].append(example)

    return {
        "source_file": str(path.resolve()),
        "overall_classification": calculate_overall_classification(
            findings
        ),
        "finding_count": len(findings),
        "data_categories": categories,
        "recommended_controls": [
            "Restrict access using least-privilege permissions.",
            "Encrypt files at rest and in transit.",
            "Store only data required for the defined purpose.",
            "Use redacted data in logs and test environments.",
            "Define retention and deletion policies.",
        ],
    }


def write_redacted_output(path, extension, content, fieldnames=None):
    output_path = Path(
        f"{path.stem}_redacted{extension}"
    )

    if extension == ".csv":
        with output_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file_handle:
            writer = csv.DictWriter(
                file_handle,
                fieldnames=fieldnames,
            )

            writer.writeheader()
            writer.writerows(content)
    else:
        output_path.write_text(
            content,
            encoding="utf-8",
        )

    return output_path


def print_report(report):
    print("\n" + "=" * 72)
    print("PII SCANNER AND DATA CLASSIFICATION REPORT")
    print("=" * 72)
    print(f"File: {report['source_file']}")
    print(
        f"Overall classification: "
        f"{report['overall_classification']}"
    )
    print(f"Total findings: {report['finding_count']}")

    print("\nDetected data categories:")

    if report["data_categories"]:
        for category, details in report["data_categories"].items():
            print(
                f"\n  {category}"
                f"\n    Classification: {details['classification']}"
                f"\n    Count: {details['count']}"
                f"\n    Redacted examples: "
                f"{', '.join(details['examples_redacted'])}"
            )
    else:
        print("  No supported PII patterns found.")

    print("\nRecommended controls:")

    for control in report["recommended_controls"]:
        print(f"  - {control}")


def main():
    print("PII Scanner and Data Classification Engine")
    print("=" * 72)
    print("Supported files: .txt, .log, .csv\n")

    file_path = input("Local file path: ").strip().strip('"')
    path = Path(file_path)

    if path.suffix.lower() not in {".txt", ".log", ".csv"}:
        print("Error: select a .txt, .log, or .csv file.")
        return

    try:
        if path.suffix.lower() == ".csv":
            findings, fieldnames, redacted_rows = scan_csv_file(path)

            redacted_path = write_redacted_output(
                path,
                ".csv",
                redacted_rows,
                fieldnames,
            )
        else:
            findings, redacted_text = scan_text_file(path)

            redacted_path = write_redacted_output(
                path,
                path.suffix,
                redacted_text,
            )

        report = create_gdpr_mapping_report(path, findings)
        report_path = Path(f"{path.stem}_gdpr_mapping_report.json")

        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        print_report(report)
        print(f"\nRedacted output: {redacted_path.resolve()}")
        print(f"JSON report: {report_path.resolve()}")

    except FileNotFoundError:
        print("Error: file not found.")

    except PermissionError:
        print("Error: permission denied.")

    except (ValueError, OSError) as error:
        print(f"File error: {error}")

    except KeyboardInterrupt:
        print("\nScan cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()