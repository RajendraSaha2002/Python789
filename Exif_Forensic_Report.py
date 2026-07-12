from pathlib import Path
import html
import struct
import sys


# TIFF field types: (display name, byte width).  Unknown types are preserved.
TIFF_TYPES = {
    1: ("BYTE", 1), 2: ("ASCII", 1), 3: ("SHORT", 2), 4: ("LONG", 4),
    5: ("RATIONAL", 8), 6: ("SBYTE", 1), 7: ("UNDEFINED", 1),
    8: ("SSHORT", 2), 9: ("SLONG", 4), 10: ("SRATIONAL", 8),
    11: ("FLOAT", 4), 12: ("DOUBLE", 8),
}

IFD0_TAGS = {
    0x0100: "ImageWidth", 0x0101: "ImageLength", 0x010E: "ImageDescription",
    0x010F: "Make", 0x0110: "Model", 0x0112: "Orientation", 0x011A: "XResolution",
    0x011B: "YResolution", 0x0128: "ResolutionUnit", 0x0131: "Software",
    0x0132: "DateTime", 0x013B: "Artist", 0x0213: "YCbCrPositioning",
    0x8298: "Copyright", 0x8769: "ExifIFDPointer", 0x8825: "GPSInfoIFDPointer",
}

EXIF_TAGS = {
    0x829A: "ExposureTime", 0x829D: "FNumber", 0x8822: "ExposureProgram",
    0x8827: "ISOSpeedRatings", 0x8830: "SensitivityType", 0x9000: "ExifVersion",
    0x9003: "DateTimeOriginal", 0x9004: "DateTimeDigitized", 0x9010: "OffsetTime",
    0x9011: "OffsetTimeOriginal", 0x9012: "OffsetTimeDigitized", 0x9101: "ComponentsConfiguration",
    0x9201: "ShutterSpeedValue", 0x9202: "ApertureValue", 0x9204: "ExposureBiasValue",
    0x9207: "MeteringMode", 0x9209: "Flash", 0x920A: "FocalLength", 0x927C: "MakerNote",
    0x9286: "UserComment", 0x9290: "SubSecTime", 0x9291: "SubSecTimeOriginal",
    0x9292: "SubSecTimeDigitized", 0xA000: "FlashpixVersion", 0xA001: "ColorSpace",
    0xA002: "PixelXDimension", 0xA003: "PixelYDimension", 0xA005: "InteroperabilityIFDPointer",
    0xA20E: "FocalPlaneXResolution", 0xA20F: "FocalPlaneYResolution", 0xA210: "FocalPlaneResolutionUnit",
    0xA217: "SensingMethod", 0xA300: "FileSource", 0xA301: "SceneType", 0xA401: "CustomRendered",
    0xA402: "ExposureMode", 0xA403: "WhiteBalance", 0xA404: "DigitalZoomRatio",
    0xA405: "FocalLengthIn35mmFilm", 0xA406: "SceneCaptureType", 0xA420: "ImageUniqueID",
    0xA431: "BodySerialNumber", 0xA432: "LensSpecification", 0xA433: "LensMake",
    0xA434: "LensModel", 0xA435: "LensSerialNumber", 0xA500: "Gamma", 0xC62F: "CameraSerialNumber",
}

GPS_TAGS = {
    0: "GPSVersionID", 1: "GPSLatitudeRef", 2: "GPSLatitude", 3: "GPSLongitudeRef",
    4: "GPSLongitude", 5: "GPSAltitudeRef", 6: "GPSAltitude", 7: "GPSTimeStamp",
    9: "GPSStatus", 10: "GPSMeasureMode", 11: "GPSDOP", 12: "GPSSpeedRef", 13: "GPSSpeed",
    16: "GPSImgDirectionRef", 17: "GPSImgDirection", 18: "GPSMapDatum", 29: "GPSDateStamp",
}

EDITOR_KEYWORDS = (
    "adobe", "photoshop", "lightroom", "gimp", "affinity", "paint.net", "canva",
    "snapseed", "picsart", "luminar", "capture one", "pixelmator", "imagemagick",
)


class ParseError(ValueError):
    """Raised when a binary structure cannot safely be parsed."""


class ByteReader:
    """Bounds-checked byte access relative to one byte sequence."""

    def __init__(self, data, label="data"):
        self.data = data
        self.label = label

    def require(self, offset, size):
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ParseError(f"{self.label}: read outside data at offset {offset} (size {size})")

    def slice(self, offset, size):
        self.require(offset, size)
        return self.data[offset:offset + size]

    def u16(self, offset, byte_order):
        self.require(offset, 2)
        return struct.unpack_from(byte_order + "H", self.data, offset)[0]

    def u32(self, offset, byte_order):
        self.require(offset, 4)
        return struct.unpack_from(byte_order + "I", self.data, offset)[0]


def safe_text(value):
    """Produce a readable, bounded representation for HTML and reports."""
    if isinstance(value, bytes):
        return value.hex()
    text = str(value)
    return text if len(text) <= 500 else text[:497] + "..."


def decode_ascii(raw):
    return raw.rstrip(b"\x00").decode("latin-1", errors="replace")


def integer_values(raw, field_type, count, byte_order):
    formats = {1: "B", 3: "H", 4: "I", 6: "b", 8: "h", 9: "i"}
    if field_type not in formats:
        return None
    values = struct.unpack(byte_order + str(count) + formats[field_type], raw)
    return values[0] if count == 1 else list(values)


def rational_values(raw, field_type, count, byte_order):
    if field_type not in (5, 10):
        return None
    code = "I" if field_type == 5 else "i"
    values = []
    for index in range(count):
        numerator, denominator = struct.unpack_from(byte_order + code + code, raw, index * 8)
        values.append(None if denominator == 0 else numerator / denominator)
    return values[0] if count == 1 else values


def decode_tiff_value(raw, field_type, count, byte_order):
    """Decode one TIFF value into safe Python primitives."""
    if field_type == 2:
        return decode_ascii(raw)
    if field_type in (1, 3, 4, 6, 8, 9):
        return integer_values(raw, field_type, count, byte_order)
    if field_type in (5, 10):
        return rational_values(raw, field_type, count, byte_order)
    if field_type == 7:
        return raw.hex()
    if field_type == 11:
        values = struct.unpack(byte_order + str(count) + "f", raw)
        return values[0] if count == 1 else list(values)
    if field_type == 12:
        values = struct.unpack(byte_order + str(count) + "d", raw)
        return values[0] if count == 1 else list(values)
    return raw.hex()


class TiffExifParser:
    """Parser for TIFF-formatted data embedded after JPEG's Exif identifier."""

    def __init__(self, tiff_data):
        self.reader = ByteReader(tiff_data, "TIFF/EXIF")
        self.data = tiff_data
        self.issues = []
        self.fields = {}
        self.ifds_seen = set()
        self.byte_order = self._read_header()

    def _read_header(self):
        self.reader.require(0, 8)
        marker = self.data[:2]
        if marker == b"II":
            byte_order = "<"
        elif marker == b"MM":
            byte_order = ">"
        else:
            raise ParseError("TIFF byte-order marker is not II or MM")
        if self.reader.u16(2, byte_order) != 42:
            raise ParseError("TIFF magic number is not 42")
        return byte_order

    def parse(self):
        first_ifd = self.reader.u32(4, self.byte_order)
        self._parse_ifd(first_ifd, "IFD0", IFD0_TAGS)
        exif_pointer = self.fields.get("ExifIFDPointer")
        gps_pointer = self.fields.get("GPSInfoIFDPointer")
        if isinstance(exif_pointer, int):
            self._parse_ifd(exif_pointer, "EXIF", EXIF_TAGS)
        if isinstance(gps_pointer, int):
            self._parse_ifd(gps_pointer, "GPS", GPS_TAGS)
        self._derive_gps_values()
        return self.fields, self.issues

    def _parse_ifd(self, offset, ifd_name, known_tags):
        if offset == 0:
            return
        if offset in self.ifds_seen:
            self.issues.append(f"{ifd_name}: recursive/repeated IFD offset {offset}")
            return
        self.ifds_seen.add(offset)
        try:
            entry_count = self.reader.u16(offset, self.byte_order)
            # Cap avoids parsing a corrupted count into an unbounded loop.
            if entry_count > 4096:
                raise ParseError(f"{ifd_name}: implausible entry count {entry_count}")
            self.reader.require(offset + 2, entry_count * 12 + 4)
            for index in range(entry_count):
                self._parse_entry(offset + 2 + index * 12, ifd_name, known_tags)
        except ParseError as error:
            self.issues.append(str(error))

    def _parse_entry(self, entry_offset, ifd_name, known_tags):
        tag = self.reader.u16(entry_offset, self.byte_order)
        field_type = self.reader.u16(entry_offset + 2, self.byte_order)
        count = self.reader.u32(entry_offset + 4, self.byte_order)
        type_info = TIFF_TYPES.get(field_type)
        label = known_tags.get(tag, f"{ifd_name}:0x{tag:04X}")
        if type_info is None:
            self.issues.append(f"{label}: unknown TIFF field type {field_type}")
            return
        _, item_size = type_info
        total_size = count * item_size
        if count > 1_000_000 or total_size > len(self.data):
            self.issues.append(f"{label}: unsafe field size {total_size}")
            return
        try:
            if total_size <= 4:
                raw = self.reader.slice(entry_offset + 8, total_size)
            else:
                value_offset = self.reader.u32(entry_offset + 8, self.byte_order)
                raw = self.reader.slice(value_offset, total_size)
            value = decode_tiff_value(raw, field_type, count, self.byte_order)
            self.fields[label] = value
        except (ParseError, struct.error, UnicodeError) as error:
            self.issues.append(f"{label}: {error}")

    def _derive_gps_values(self):
        latitude = coordinate_to_decimal(self.fields.get("GPSLatitude"), self.fields.get("GPSLatitudeRef"))
        longitude = coordinate_to_decimal(self.fields.get("GPSLongitude"), self.fields.get("GPSLongitudeRef"))
        if latitude is not None:
            self.fields["GPSLatitudeDecimal"] = latitude
        if longitude is not None:
            self.fields["GPSLongitudeDecimal"] = longitude
            self.fields["GPSMapURL"] = f"https://www.openstreetmap.org/?mlat={latitude:.7f}&mlon={longitude:.7f}#map=16/{latitude:.7f}/{longitude:.7f}"
        altitude = self.fields.get("GPSAltitude")
        if isinstance(altitude, (int, float)):
            self.fields["GPSAltitudeMeters"] = -altitude if self.fields.get("GPSAltitudeRef") == 1 else altitude


def coordinate_to_decimal(coordinates, reference):
    """Convert [degrees, minutes, seconds] plus N/S/E/W into decimal degrees."""
    if not isinstance(coordinates, list) or len(coordinates) != 3:
        return None
    if any(value is None or not isinstance(value, (int, float)) for value in coordinates):
        return None
    degrees, minutes, seconds = coordinates
    decimal = degrees + minutes / 60 + seconds / 3600
    ref = str(reference).upper()
    if ref in ("S", "W"):
        decimal = -decimal
    elif ref not in ("N", "E"):
        return None
    return decimal


def parse_jpeg_exif(data):
    """Find and parse Exif APP1 data from JPEG bytes, preserving parse issues."""
    result = {"fields": {}, "issues": [], "segments": [], "exif_found": False}
    if len(data) < 2 or data[:2] != b"\xFF\xD8":
        result["issues"].append("Not a JPEG: missing SOI marker (FFD8)")
        return result
    reader = ByteReader(data, "JPEG")
    offset = 2
    try:
        while offset < len(data):
            # JPEG permits fill bytes (FF FF ... marker); skip them safely.
            if data[offset] != 0xFF:
                offset += 1
                continue
            while offset < len(data) and data[offset] == 0xFF:
                offset += 1
            if offset >= len(data):
                break
            marker = data[offset]
            offset += 1
            if marker in (0xD8, 0xD9):
                continue
            if marker == 0xDA:  # Start of Scan: compressed bytes follow.
                result["segments"].append("SOS (compressed image data)")
                break
            if 0xD0 <= marker <= 0xD7 or marker == 0x01:
                result["segments"].append(f"marker FF{marker:02X}")
                continue
            length = reader.u16(offset, ">")
            if length < 2:
                raise ParseError(f"JPEG: invalid marker length {length} for FF{marker:02X}")
            payload_offset = offset + 2
            payload_size = length - 2
            payload = reader.slice(payload_offset, payload_size)
            result["segments"].append(f"FF{marker:02X} ({payload_size} bytes)")
            if marker == 0xE1 and payload.startswith(b"Exif\x00\x00") and not result["exif_found"]:
                result["exif_found"] = True
                try:
                    fields, issues = TiffExifParser(payload[6:]).parse()
                    result["fields"].update(fields)
                    result["issues"].extend(issues)
                except ParseError as error:
                    result["issues"].append(f"EXIF parse error: {error}")
            offset = payload_offset + payload_size
    except ParseError as error:
        result["issues"].append(str(error))
    if not result["exif_found"]:
        result["issues"].append("No Exif APP1 segment found")
    return result


def camera_fingerprint(fields):
    """Build a non-cryptographic camera/device identifier from stable fields."""
    keys = ("Make", "Model", "BodySerialNumber", "CameraSerialNumber", "LensMake", "LensModel", "LensSerialNumber")
    parts = [f"{key}={safe_text(fields[key])}" for key in keys if fields.get(key) not in (None, "")]
    return " | ".join(parts) if parts else "No camera-identifying fields available"


def detect_software_watermark(fields):
    """Report editor/software metadata and common textual modification indicators."""
    findings = []
    for key in ("Software", "ImageDescription", "UserComment", "Artist", "Copyright"):
        value = fields.get(key)
        if not value:
            continue
        text = safe_text(value).lower()
        matched = [word for word in EDITOR_KEYWORDS if word in text]
        if matched:
            findings.append(f"{key} contains editor indicator(s): {', '.join(matched)}")
    software = fields.get("Software")
    if software:
        findings.append(f"Software metadata present: {safe_text(software)}")
    return findings


def timestamp_parts(value):
    """Return (date, time) for canonical EXIF timestamp strings, else None."""
    text = str(value)
    if len(text) >= 19 and text[4:5] == ":" and text[7:8] == ":" and text[10:11] == " ":
        return text[:10], text[11:19]
    return None


def detect_inconsistencies(fields, file_path=None):
    """Return cautious metadata anomalies that may warrant closer examination."""
    findings = []
    original = fields.get("DateTimeOriginal")
    digitized = fields.get("DateTimeDigitized")
    modified = fields.get("DateTime")
    if original and digitized and original != digitized:
        findings.append("DateTimeOriginal differs from DateTimeDigitized")
    if original and modified and original != modified:
        findings.append("DateTimeOriginal differs from DateTime (file modification metadata)")
    for label, value in (("DateTimeOriginal", original), ("DateTimeDigitized", digitized), ("DateTime", modified)):
        if value and timestamp_parts(value) is None:
            findings.append(f"{label} is not in canonical EXIF YYYY:MM:DD HH:MM:SS format")
    if ("GPSLatitudeDecimal" in fields) != ("GPSLongitudeDecimal" in fields):
        findings.append("Only one of latitude/longitude could be decoded")
    if fields.get("GPSMapDatum") and str(fields["GPSMapDatum"]).upper() not in ("WGS-84", "WGS84"):
        findings.append(f"GPS map datum is unusual: {safe_text(fields['GPSMapDatum'])}")
    if fields.get("PixelXDimension") and fields.get("ImageWidth") and fields["PixelXDimension"] != fields["ImageWidth"]:
        findings.append("EXIF PixelXDimension differs from IFD ImageWidth")
    if fields.get("PixelYDimension") and fields.get("ImageLength") and fields["PixelYDimension"] != fields["ImageLength"]:
        findings.append("EXIF PixelYDimension differs from IFD ImageLength")
    if file_path and file_path.suffix.lower() not in (".jpg", ".jpeg"):
        findings.append("File extension is not .jpg/.jpeg although JPEG parsing was attempted")
    if not fields:
        findings.append("No readable EXIF fields: metadata may be stripped, absent, or malformed")
    return findings


def file_record(path):
    """Parse one JPEG file into a report-ready record without stopping a batch."""
    record = {"path": str(path), "fields": {}, "issues": [], "segments": [], "findings": [], "software_findings": []}
    try:
        data = path.read_bytes()
        parsed = parse_jpeg_exif(data)
        record.update(parsed)
        record["size_bytes"] = len(data)
        record["fingerprint"] = camera_fingerprint(record["fields"])
        record["software_findings"] = detect_software_watermark(record["fields"])
        record["findings"] = detect_inconsistencies(record["fields"], path)
    except OSError as error:
        record["issues"].append(f"Could not read file: {error}")
        record["fingerprint"] = "Unavailable"
        record["size_bytes"] = 0
    return record


def find_jpegs(input_path):
    """Return sorted JPEG candidates; accepts one image or recursively scans a folder."""
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")
    candidates = []
    for path in input_path.rglob("*"):
        if path.is_file() and path.suffix.lower() in (".jpg", ".jpeg"):
            candidates.append(path)
    return sorted(candidates)


def html_list(items, empty="None"):
    if not items:
        return f"<p class='empty'>{html.escape(empty)}</p>"
    return "<ul>" + "".join(f"<li>{html.escape(safe_text(item))}</li>" for item in items) + "</ul>"


def fields_table(fields):
    if not fields:
        return "<p class='empty'>No parsed EXIF fields.</p>"
    rows = []
    for key in sorted(fields):
        value = fields[key]
        text = safe_text(value)
        if key == "GPSMapURL" and isinstance(value, str) and value.startswith("https://"):
            display = f"<a href='{html.escape(value, quote=True)}'>{html.escape(value)}</a>"
        else:
            display = html.escape(text)
        rows.append(f"<tr><th>{html.escape(key)}</th><td>{display}</td></tr>")
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def render_html(records, report_path):
    """Write a standalone forensic HTML report; output values are HTML-escaped."""
    cards = []
    for record in records:
        severity = "warning" if record["findings"] or record["issues"] else "ok"
        cards.append(
            f"<article class='card {severity}'>"
            f"<h2>{html.escape(record['path'])}</h2>"
            f"<p><b>Size:</b> {record.get('size_bytes', 0):,} bytes<br>"
            f"<b>Camera fingerprint:</b> {html.escape(record.get('fingerprint', 'Unavailable'))}</p>"
            "<h3>EXIF metadata</h3>" + fields_table(record["fields"]) +
            "<h3>JPEG segments</h3>" + html_list(record["segments"], "No segments recorded") +
            "<h3>Software / watermark indicators</h3>" + html_list(record["software_findings"], "No editor indicator found") +
            "<h3>Metadata consistency checks</h3>" + html_list(record["findings"], "No inconsistency flagged") +
            "<h3>Parser observations</h3>" + html_list(record["issues"], "No parser issue") +
            "</article>"
        )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>JPEG EXIF Forensic Report</title>
<style>
body{{font-family:system-ui,sans-serif;line-height:1.45;margin:2rem;background:#f5f7fb;color:#18212f}}
h1{{margin-bottom:.15rem}} .note{{color:#4a5568}} .card{{background:white;border-left:6px solid #2f855a;padding:1.25rem;margin:1.25rem 0;box-shadow:0 1px 3px #ccd}}
.card.warning{{border-left-color:#c05621}} table{{border-collapse:collapse;width:100%;font-size:.92rem}} th,td{{border:1px solid #d9e0ea;padding:.45rem;text-align:left;vertical-align:top}}
th{{width:31%;background:#eef2f7}} ul{{margin-top:.35rem}} .empty{{color:#667085;font-style:italic}} code{{background:#eef2f7;padding:.1rem .25rem}}
</style></head><body><h1>JPEG EXIF Forensic Report</h1>
<p class="note">Generated from byte-level JPEG/TIFF parsing. Findings are investigative leads, not conclusive tamper proof.</p>
<p class="note">Files examined: {len(records)}. Report: {html.escape(str(report_path))}</p>{''.join(cards)}
</body></html>"""
    report_path.write_text(document, encoding="utf-8")


def make_self_test_jpeg():
    """Create a minimal JPEG with a valid little-endian EXIF Make field."""
    # TIFF: header, IFD with one ASCII Make entry, no next IFD, then string.
    tiff = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)
    tiff += struct.pack("<H", 1)
    tiff += struct.pack("<HHI", 0x010F, 2, 6) + struct.pack("<I", 26)
    tiff += struct.pack("<I", 0) + b"Canon\x00"
    app1 = b"Exif\x00\x00" + tiff
    return b"\xFF\xD8\xFF\xE1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xFF\xD9"


def self_test():
    """Run deterministic parser and GPS conversion checks without external files."""
    parsed = parse_jpeg_exif(make_self_test_jpeg())
    assert parsed["fields"]["Make"] == "Canon"
    assert coordinate_to_decimal([12.0, 30.0, 0.0], "S") == -12.5
    assert coordinate_to_decimal([77.0, 35.0, 30.0], "E") == 77.59166666666667
    malformed = parse_jpeg_exif(b"not jpeg")
    assert malformed["issues"] and "Not a JPEG" in malformed["issues"][0]
    print("EXIF parser self-test passed")


def main(arguments):
    if arguments == ["--self-test"]:
        self_test()
        return 0
    if not arguments or arguments[0] in ("-h", "--help"):
        # Do not depend on __doc__: it becomes None when a file is copied with
        # its opening module docstring removed or moved below executable code.
        print("Usage:\n"
              "  python exif_forensic_report.py photo.jpg\n"
              "  python exif_forensic_report.py folder_with_jpegs --output report.html\n"
              "  python exif_forensic_report.py --self-test")
        return 0
    output = None
    input_name = arguments[0]
    remaining = arguments[1:]
    if remaining:
        if len(remaining) != 2 or remaining[0] != "--output":
            print("Usage: exif_forensic_report.py INPUT [--output report.html]", file=sys.stderr)
            return 2
        output = Path(remaining[1])
    input_path = Path(input_name)
    try:
        images = find_jpegs(input_path)
    except (OSError, FileNotFoundError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    if not images:
        print("No .jpg/.jpeg files found.", file=sys.stderr)
        return 1
    if output is None:
        output = Path("exif_forensic_report.html")
    records = [file_record(path) for path in images]
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        render_html(records, output)
    except OSError as error:
        print(f"Could not write report: {error}", file=sys.stderr)
        return 2
    print(f"Wrote report for {len(records)} JPEG file(s): {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
