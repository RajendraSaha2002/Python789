import json
import math
import struct
from pathlib import Path


class PEFormatError(Exception):
    pass


def read_u16(data, offset):
    if offset < 0 or offset + 2 > len(data):
        raise PEFormatError(f"Invalid 16-bit read at offset 0x{offset:X}")
    return struct.unpack_from("<H", data, offset)[0]


def read_u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        raise PEFormatError(f"Invalid 32-bit read at offset 0x{offset:X}")
    return struct.unpack_from("<I", data, offset)[0]


def read_u64(data, offset):
    if offset < 0 or offset + 8 > len(data):
        raise PEFormatError(f"Invalid 64-bit read at offset 0x{offset:X}")
    return struct.unpack_from("<Q", data, offset)[0]


def read_string(data, offset, limit=512):
    if offset is None or offset < 0 or offset >= len(data):
        return ""

    end = min(offset + limit, len(data))
    chars = bytearray()

    for index in range(offset, end):
        if data[index] == 0:
            break
        chars.append(data[index])

    return chars.decode("ascii", errors="replace")


def calculate_entropy(data):
    if not data:
        return 0.0

    counts = [0] * 256

    for value in data:
        counts[value] += 1

    entropy = 0.0
    data_length = len(data)

    for count in counts:
        if count:
            probability = count / data_length
            entropy -= probability * math.log2(probability)

    return entropy


class PEAnalyzer:
    IMPORT_DIRECTORY = 1
    RESOURCE_DIRECTORY = 2
    SECURITY_DIRECTORY = 4
    TLS_DIRECTORY = 9

    PACKER_SECTIONS = {
        "UPX0": "UPX",
        "UPX1": "UPX",
        "UPX2": "UPX",
        ".ASPACK": "ASPack",
        ".MPRESS1": "MPRESS",
        ".MPRESS2": "MPRESS",
        ".THEMIDA": "Themida",
        ".VMP0": "VMProtect",
        ".VMP1": "VMProtect",
        ".PETITE": "Petite",
    }

    SUSPICIOUS_APIS = {
        "virtualalloc",
        "virtualprotect",
        "virtualprotectex",
        "writeprocessmemory",
        "createremotethread",
        "ntcreatethreadex",
        "loadlibrarya",
        "loadlibraryw",
        "getprocaddress",
        "urldownloadtofilea",
        "urldownloadtofilew",
        "winexec",
        "shellexecutea",
        "shellexecutew",
        "internetopenurl",
        "connect",
        "send",
        "recv",
    }

    def __init__(self, file_path):
        self.path = Path(file_path.strip().strip('"'))

        if not self.path.is_file():
            raise FileNotFoundError(f"File not found: {self.path}")

        self.data = self.path.read_bytes()
        self.file_size = len(self.data)

        self.pe_offset = 0
        self.coff_offset = 0
        self.optional_header_offset = 0
        self.section_table_offset = 0

        self.machine = 0
        self.section_count = 0
        self.timestamp = 0
        self.optional_header_size = 0
        self.is_64bit = False
        self.image_base = 0
        self.entry_point_rva = 0
        self.headers_size = 0

        self.directories = []
        self.sections = []

    def parse(self):
        self.parse_headers()
        self.parse_sections()
        return self

    def parse_headers(self):
        if self.file_size < 64:
            raise PEFormatError("File is too small to be a PE file.")

        if self.data[0:2] != b"MZ":
            raise PEFormatError("Invalid DOS header: MZ signature not found.")

        self.pe_offset = read_u32(self.data, 0x3C)

        if self.pe_offset + 24 > self.file_size:
            raise PEFormatError("PE header is outside the file.")

        if self.data[self.pe_offset:self.pe_offset + 4] != b"PE\x00\x00":
            raise PEFormatError("Invalid PE signature.")

        self.coff_offset = self.pe_offset + 4
        self.machine = read_u16(self.data, self.coff_offset)
        self.section_count = read_u16(self.data, self.coff_offset + 2)
        self.timestamp = read_u32(self.data, self.coff_offset + 4)
        self.optional_header_size = read_u16(self.data, self.coff_offset + 16)

        self.optional_header_offset = self.coff_offset + 20

        if self.optional_header_offset + self.optional_header_size > self.file_size:
            raise PEFormatError("Optional header is outside the file.")

        magic = read_u16(self.data, self.optional_header_offset)

        if magic == 0x10B:
            self.is_64bit = False
            self.entry_point_rva = read_u32(
                self.data,
                self.optional_header_offset + 16,
            )
            self.image_base = read_u32(
                self.data,
                self.optional_header_offset + 28,
            )
            self.headers_size = read_u32(
                self.data,
                self.optional_header_offset + 60,
            )
            directory_count = read_u32(
                self.data,
                self.optional_header_offset + 92,
            )
            directory_offset = self.optional_header_offset + 96

        elif magic == 0x20B:
            self.is_64bit = True
            self.entry_point_rva = read_u32(
                self.data,
                self.optional_header_offset + 16,
            )
            self.image_base = read_u64(
                self.data,
                self.optional_header_offset + 24,
            )
            self.headers_size = read_u32(
                self.data,
                self.optional_header_offset + 60,
            )
            directory_count = read_u32(
                self.data,
                self.optional_header_offset + 108,
            )
            directory_offset = self.optional_header_offset + 112

        else:
            raise PEFormatError(
                f"Unsupported PE optional-header magic: 0x{magic:04X}"
            )

        for index in range(min(directory_count, 16)):
            offset = directory_offset + (index * 8)

            if offset + 8 > len(self.data):
                break

            self.directories.append(
                {
                    "rva": read_u32(self.data, offset),
                    "size": read_u32(self.data, offset + 4),
                }
            )

        self.section_table_offset = (
            self.optional_header_offset + self.optional_header_size
        )

    def parse_sections(self):
        for index in range(self.section_count):
            offset = self.section_table_offset + (index * 40)

            if offset + 40 > self.file_size:
                raise PEFormatError("Invalid section table.")

            name_bytes = self.data[offset:offset + 8]
            name = name_bytes.split(b"\x00", 1)[0].decode(
                "ascii",
                errors="replace",
            )

            virtual_size = read_u32(self.data, offset + 8)
            virtual_address = read_u32(self.data, offset + 12)
            raw_size = read_u32(self.data, offset + 16)
            raw_offset = read_u32(self.data, offset + 20)
            characteristics = read_u32(self.data, offset + 36)

            section_data = b""

            if raw_offset < self.file_size and raw_size > 0:
                section_data = self.data[
                    raw_offset:min(raw_offset + raw_size, self.file_size)
                ]

            self.sections.append(
                {
                    "name": name or "<unnamed>",
                    "virtual_address": virtual_address,
                    "virtual_size": virtual_size,
                    "raw_offset": raw_offset,
                    "raw_size": raw_size,
                    "characteristics": characteristics,
                    "entropy": round(calculate_entropy(section_data), 4),
                }
            )

    def get_directory(self, index):
        if 0 <= index < len(self.directories):
            return self.directories[index]

        return {"rva": 0, "size": 0}

    def rva_to_offset(self, rva):
        if rva < self.headers_size and rva < self.file_size:
            return rva

        for section in self.sections:
            section_start = section["virtual_address"]
            section_size = max(
                section["virtual_size"],
                section["raw_size"],
            )
            section_end = section_start + section_size

            if section_start <= rva < section_end:
                file_offset = section["raw_offset"] + (
                    rva - section_start
                )

                if file_offset < self.file_size:
                    return file_offset

        return None

    def parse_imports(self):
        directory = self.get_directory(self.IMPORT_DIRECTORY)

        if not directory["rva"] or not directory["size"]:
            return []

        offset = self.rva_to_offset(directory["rva"])

        if offset is None:
            return []

        pointer_size = 8 if self.is_64bit else 4
        ordinal_mask = (
            0x8000000000000000
            if self.is_64bit
            else 0x80000000
        )

        imports = []

        while offset + 20 <= self.file_size:
            original_first_thunk = read_u32(self.data, offset)
            name_rva = read_u32(self.data, offset + 12)
            first_thunk = read_u32(self.data, offset + 16)

            if (
                original_first_thunk == 0
                and name_rva == 0
                and first_thunk == 0
            ):
                break

            library_offset = self.rva_to_offset(name_rva)
            library = read_string(self.data, library_offset) or "Unknown"

            thunk_rva = original_first_thunk or first_thunk
            thunk_offset = self.rva_to_offset(thunk_rva)
            functions = []

            if thunk_offset is not None:
                while thunk_offset + pointer_size <= self.file_size:
                    if self.is_64bit:
                        thunk_value = read_u64(self.data, thunk_offset)
                    else:
                        thunk_value = read_u32(self.data, thunk_offset)

                    if thunk_value == 0:
                        break

                    if thunk_value & ordinal_mask:
                        functions.append(
                            f"Ordinal_{thunk_value & 0xFFFF}"
                        )
                    else:
                        function_offset = self.rva_to_offset(thunk_value)

                        if function_offset is not None:
                            function_name = read_string(
                                self.data,
                                function_offset + 2,
                            )

                            if function_name:
                                functions.append(function_name)

                    thunk_offset += pointer_size

                    if len(functions) >= 5000:
                        break

            imports.append(
                {
                    "library": library,
                    "functions": functions,
                }
            )

            offset += 20

            if len(imports) >= 1000:
                break

        return imports

    def parse_tls_callbacks(self):
        directory = self.get_directory(self.TLS_DIRECTORY)

        if not directory["rva"] or not directory["size"]:
            return []

        tls_offset = self.rva_to_offset(directory["rva"])

        if tls_offset is None:
            return []

        pointer_size = 8 if self.is_64bit else 4
        callbacks_offset_in_tls = 24 if self.is_64bit else 12

        if tls_offset + callbacks_offset_in_tls + pointer_size > self.file_size:
            return []

        if self.is_64bit:
            callback_table_va = read_u64(
                self.data,
                tls_offset + callbacks_offset_in_tls,
            )
        else:
            callback_table_va = read_u32(
                self.data,
                tls_offset + callbacks_offset_in_tls,
            )

        if not callback_table_va or callback_table_va < self.image_base:
            return []

        callback_table_rva = callback_table_va - self.image_base
        callback_offset = self.rva_to_offset(callback_table_rva)

        if callback_offset is None:
            return []

        callbacks = []

        for _ in range(256):
            if callback_offset + pointer_size > self.file_size:
                break

            if self.is_64bit:
                callback_va = read_u64(self.data, callback_offset)
            else:
                callback_va = read_u32(self.data, callback_offset)

            if callback_va == 0:
                break

            callbacks.append(f"0x{callback_va:X}")
            callback_offset += pointer_size

        return callbacks

    def get_overlay(self):
        final_section_end = self.headers_size

        for section in self.sections:
            section_end = section["raw_offset"] + section["raw_size"]
            final_section_end = max(final_section_end, section_end)

        security = self.get_directory(self.SECURITY_DIRECTORY)
        certificate_offset = security["rva"]
        certificate_size = security["size"]

        # Security directory uses a file offset, not an RVA.
        if certificate_offset and certificate_size:
            final_section_end = max(
                final_section_end,
                certificate_offset + certificate_size,
            )

        final_section_end = min(final_section_end, self.file_size)
        overlay_data = self.data[final_section_end:]

        return {
            "offset": final_section_end,
            "size": len(overlay_data),
            "entropy": round(calculate_entropy(overlay_data), 4),
        }

    def score_packer_indicators(self, imports, overlay):
        score = 0
        indicators = []

        high_entropy = [
            section["name"]
            for section in self.sections
            if section["raw_size"] >= 512 and section["entropy"] >= 7.2
        ]

        if high_entropy:
            score += len(high_entropy) * 2
            indicators.append(
                "High-entropy sections: " + ", ".join(high_entropy)
            )

        section_names = {
            section["name"].upper()
            for section in self.sections
        }

        for marker, packer_name in self.PACKER_SECTIONS.items():
            if marker in section_names:
                score += 4
                indicators.append(
                    f"Known packer section: {marker} ({packer_name})"
                )

        imported_apis = {
            function.lower()
            for imported_library in imports
            for function in imported_library["functions"]
        }

        suspicious = sorted(imported_apis.intersection(self.SUSPICIOUS_APIS))

        if suspicious:
            score += min(len(suspicious), 3)
            indicators.append(
                "Suspicious API imports: " + ", ".join(suspicious)
            )

        total_imports = sum(
            len(imported_library["functions"])
            for imported_library in imports
        )

        if total_imports == 0:
            score += 3
            indicators.append("No imports found or imports could not be parsed.")
        elif total_imports < 5:
            score += 1
            indicators.append("Very small import table.")

        if overlay["size"] > 0:
            score += 1
            indicators.append(f"Overlay detected: {overlay['size']} bytes.")

            if overlay["entropy"] >= 7.2:
                score += 2
                indicators.append("Overlay has high entropy.")

        if score >= 8:
            risk = "HIGH"
        elif score >= 4:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "risk": risk,
            "score": score,
            "indicators": indicators,
        }

    def create_report(self):
        imports = self.parse_imports()
        tls_callbacks = self.parse_tls_callbacks()
        overlay = self.get_overlay()

        resource = self.get_directory(self.RESOURCE_DIRECTORY)
        security = self.get_directory(self.SECURITY_DIRECTORY)
        packer = self.score_packer_indicators(imports, overlay)

        return {
            "file_path": str(self.path.resolve()),
            "file_size_bytes": self.file_size,
            "format": "PE32+" if self.is_64bit else "PE32",
            "machine": f"0x{self.machine:04X}",
            "compile_timestamp_raw": self.timestamp,
            "image_base": f"0x{self.image_base:X}",
            "entry_point_rva": f"0x{self.entry_point_rva:X}",
            "sections": self.sections,
            "imports": imports,
            "tls_callbacks": tls_callbacks,
            "resource_directory_present": bool(resource["rva"]),
            "digital_signature_directory": {
                "present": bool(security["rva"] and security["size"]),
                "file_offset": security["rva"],
                "size": security["size"],
            },
            "overlay": overlay,
            "packer_analysis": packer,
        }


def print_report(report):
    print("\n" + "=" * 70)
    print("PE FILE STATIC ANALYSIS REPORT")
    print("=" * 70)
    print(f"File: {report['file_path']}")
    print(f"Size: {report['file_size_bytes']} bytes")
    print(f"Format: {report['format']}")
    print(f"Machine: {report['machine']}")
    print(f"Entry point RVA: {report['entry_point_rva']}")
    print(f"Resource directory: {report['resource_directory_present']}")
    print(
        "Digital signature directory: "
        f"{report['digital_signature_directory']['present']}"
    )

    print("\nSections:")
    for section in report["sections"]:
        print(
            f"  {section['name']:<12} "
            f"Raw size: {section['raw_size']:<9} "
            f"Entropy: {section['entropy']:.4f}"
        )

    print("\nImports:")
    if not report["imports"]:
        print("  No imports found.")
    else:
        for imported_library in report["imports"]:
            functions = imported_library["functions"]
            preview = ", ".join(functions[:8])

            if len(functions) > 8:
                preview += ", ..."

            print(
                f"  {imported_library['library']} "
                f"({len(functions)} APIs)"
            )

            if preview:
                print(f"    {preview}")

    print("\nTLS callbacks:")
    if report["tls_callbacks"]:
        for callback in report["tls_callbacks"]:
            print(f"  {callback}")
    else:
        print("  None found.")

    overlay = report["overlay"]
    print(
        f"\nOverlay: {overlay['size']} bytes, "
        f"entropy: {overlay['entropy']:.4f}"
    )

    packer = report["packer_analysis"]
    print("\nPacker / obfuscation heuristic:")
    print(f"  Risk: {packer['risk']}")
    print(f"  Score: {packer['score']}")

    if packer["indicators"]:
        for indicator in packer["indicators"]:
            print(f"  - {indicator}")
    else:
        print("  - No strong packer indicators found.")

    print("\nNote: heuristic findings are not proof of malware.")


def main():
    print("PE Static Analyzer and Packer Detector")
    print("Enter a Windows EXE or DLL file path.")
    print("Example: C:\\Windows\\System32\\notepad.exe\n")

    file_path = input("PE file path: ").strip()

    if not file_path:
        print("Error: No file path entered.")
        return

    try:
        analyzer = PEAnalyzer(file_path)
        report = analyzer.parse().create_report()
        print_report(report)

        save_json = input("\nSave JSON report? (y/n): ").strip().lower()

        if save_json == "y":
            output_path = Path("pe_analysis_report.json")
            output_path.write_text(
                json.dumps(report, indent=2),
                encoding="utf-8",
            )
            print(f"JSON report saved: {output_path.resolve()}")

    except FileNotFoundError as error:
        print(f"Error: {error}")

    except PermissionError:
        print("Error: Permission denied while reading this file.")

    except PEFormatError as error:
        print(f"PE parsing error: {error}")

    except OSError as error:
        print(f"File error: {error}")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()