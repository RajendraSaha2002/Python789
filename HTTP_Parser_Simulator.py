

from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs, urlparse


# ================================================================
# Common safe helpers
# ================================================================

class ProtocolError(Exception):
    pass


def safe_decode(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def print_title(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ================================================================
# HTTP/1.1 parser
# ================================================================

@dataclass
class HTTP11Message:
    start_line: str
    headers: dict[str, str]
    body: bytes
    is_request: bool
    method: str = ""
    target: str = ""
    version: str = ""
    status_code: int = 0
    reason: str = ""

    def header(self, name: str, default: str = "") -> str:
        return self.headers.get(name.lower(), default)


@dataclass
class Cookie:
    name: str
    value: str
    path: str = "/"
    domain: str = ""


class CookieJar:
    def __init__(self) -> None:
        self.cookies: list[Cookie] = []

    def add_from_set_cookie(self, value: str) -> None:
        parts = [part.strip() for part in value.split(";") if part.strip()]
        if not parts or "=" not in parts[0]:
            return

        name, cookie_value = parts[0].split("=", 1)
        cookie = Cookie(name=name.strip(), value=cookie_value.strip())

        for part in parts[1:]:
            key, _, item_value = part.partition("=")
            key = key.strip().lower()

            if key == "path":
                cookie.path = item_value.strip() or "/"
            elif key == "domain":
                cookie.domain = item_value.strip().lower()

        self.cookies = [old for old in self.cookies if old.name != cookie.name]
        self.cookies.append(cookie)

    def header_for_url(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        path = parsed.path or "/"

        usable = []
        for cookie in self.cookies:
            domain_matches = not cookie.domain or host.endswith(cookie.domain)
            path_matches = path.startswith(cookie.path)

            if domain_matches and path_matches:
                usable.append(f"{cookie.name}={cookie.value}")

        return "; ".join(usable)


def parse_headers(header_bytes: bytes) -> tuple[str, dict[str, str]]:
    lines = safe_decode(header_bytes).split("\r\n")

    if not lines or not lines[0].strip():
        raise ProtocolError("Missing HTTP start line")

    start_line = lines[0]
    headers: dict[str, str] = {}

    for line in lines[1:]:
        if not line:
            continue

        if ":" not in line:
            raise ProtocolError(f"Invalid HTTP header line: {line!r}")

        name, value = line.split(":", 1)
        key = name.strip().lower()
        value = value.strip()

        # Combine repeated headers safely.
        if key in headers:
            headers[key] += ", " + value
        else:
            headers[key] = value

    return start_line, headers


def decode_chunked_body(data: bytes) -> bytes:
    """Decode an HTTP/1.1 chunked body."""
    stream = io.BytesIO(data)
    output = bytearray()

    while True:
        line = stream.readline()

        if not line:
            raise ProtocolError("Incomplete chunked body")

        if not line.endswith(b"\r\n"):
            raise ProtocolError("Invalid chunk-size line ending")

        size_text = safe_decode(line[:-2]).split(";", 1)[0].strip()

        try:
            chunk_size = int(size_text, 16)
        except ValueError as error:
            raise ProtocolError(f"Invalid chunk size: {size_text!r}") from error

        if chunk_size == 0:
            # Consume trailers until final empty line.
            while True:
                trailer = stream.readline()
                if trailer in (b"", b"\r\n"):
                    return bytes(output)

        chunk = stream.read(chunk_size)

        if len(chunk) != chunk_size:
            raise ProtocolError("Chunk data is shorter than announced size")

        ending = stream.read(2)
        if ending != b"\r\n":
            raise ProtocolError("Chunk is missing CRLF ending")

        output.extend(chunk)


def parse_http11(raw: bytes) -> HTTP11Message:
    """Parse a raw HTTP/1.1 request or response byte stream."""
    if b"\r\n\r\n" not in raw:
        raise ProtocolError("HTTP headers are incomplete")

    raw_headers, raw_body = raw.split(b"\r\n\r\n", 1)
    start_line, headers = parse_headers(raw_headers)

    transfer_encoding = headers.get("transfer-encoding", "").lower()

    if "chunked" in transfer_encoding:
        body = decode_chunked_body(raw_body)
    else:
        content_length = headers.get("content-length")

        if content_length:
            try:
                expected_length = int(content_length)
            except ValueError as error:
                raise ProtocolError("Invalid Content-Length") from error

            if expected_length < 0:
                raise ProtocolError("Negative Content-Length is invalid")

            body = raw_body[:expected_length]
        else:
            body = raw_body

    is_response = start_line.upper().startswith("HTTP/")

    if is_response:
        parts = start_line.split(" ", 2)

        if len(parts) < 2:
            raise ProtocolError("Invalid HTTP response start line")

        try:
            status_code = int(parts[1])
        except ValueError as error:
            raise ProtocolError("Invalid HTTP status code") from error

        return HTTP11Message(
            start_line=start_line,
            headers=headers,
            body=body,
            is_request=False,
            version=parts[0],
            status_code=status_code,
            reason=parts[2] if len(parts) > 2 else "",
        )

    parts = start_line.split(" ", 2)

    if len(parts) != 3:
        raise ProtocolError("Invalid HTTP request start line")

    return HTTP11Message(
        start_line=start_line,
        headers=headers,
        body=body,
        is_request=True,
        method=parts[0],
        target=parts[1],
        version=parts[2],
    )


def is_keep_alive(message: HTTP11Message) -> bool:
    connection = message.header("connection").lower()

    if message.version == "HTTP/1.1":
        return connection != "close"

    if message.version == "HTTP/1.0":
        return connection == "keep-alive"

    return False


def parse_multipart(body: bytes, content_type: str) -> list[dict[str, str]]:
    """Parse basic multipart/form-data bodies."""
    marker = "boundary="

    if marker not in content_type:
        return []

    boundary = content_type.split(marker, 1)[1].strip().strip('"')
    delimiter = b"--" + boundary.encode("utf-8")
    parts = []

    for raw_part in body.split(delimiter):
        raw_part = raw_part.strip(b"\r\n")

        if not raw_part or raw_part == b"--":
            continue

        if b"\r\n\r\n" not in raw_part:
            continue

        raw_headers, raw_value = raw_part.split(b"\r\n\r\n", 1)
        _, headers = parse_headers(b"X-Multipart: yes\r\n" + raw_headers)

        disposition = headers.get("content-disposition", "")
        result = {
            "headers": str(headers),
            "value": safe_decode(raw_value.rstrip(b"\r\n")),
        }

        for item in disposition.split(";"):
            item = item.strip()

            if item.startswith("name="):
                result["name"] = item.split("=", 1)[1].strip('"')

            if item.startswith("filename="):
                result["filename"] = item.split("=", 1)[1].strip('"')

        parts.append(result)

    return parts


# ================================================================
# HTTP/2 frame parser
# ================================================================

HTTP2_FRAME_TYPES = {
    0x0: "DATA",
    0x1: "HEADERS",
    0x2: "PRIORITY",
    0x3: "RST_STREAM",
    0x4: "SETTINGS",
    0x5: "PUSH_PROMISE",
    0x6: "PING",
    0x7: "GOAWAY",
    0x8: "WINDOW_UPDATE",
    0x9: "CONTINUATION",
}


@dataclass
class HTTP2Frame:
    frame_type: int
    flags: int
    stream_id: int
    payload: bytes

    @property
    def type_name(self) -> str:
        return HTTP2_FRAME_TYPES.get(self.frame_type, f"UNKNOWN({self.frame_type})")

    def encode(self) -> bytes:
        payload_length = len(self.payload)

        if payload_length > 0xFFFFFF:
            raise ProtocolError("HTTP/2 frame payload is too large")

        header = (
            payload_length.to_bytes(3, "big")
            + bytes([self.frame_type, self.flags])
            + struct.pack("!I", self.stream_id & 0x7FFFFFFF)
        )

        return header + self.payload


def parse_http2_frames(data: bytes) -> list[HTTP2Frame]:
    """Parse one or more HTTP/2 binary frames."""
    frames = []
    offset = 0

    while offset < len(data):
        if len(data) - offset < 9:
            raise ProtocolError("Incomplete HTTP/2 frame header")

        length = int.from_bytes(data[offset:offset + 3], "big")
        frame_type = data[offset + 3]
        flags = data[offset + 4]
        stream_id = struct.unpack("!I", data[offset + 5:offset + 9])[0] & 0x7FFFFFFF
        offset += 9

        if offset + length > len(data):
            raise ProtocolError("Incomplete HTTP/2 frame payload")

        payload = data[offset:offset + length]
        offset += length

        frames.append(HTTP2Frame(frame_type, flags, stream_id, payload))

    return frames


def make_settings_frame(settings: dict[int, int]) -> HTTP2Frame:
    payload = bytearray()

    for setting_id, value in settings.items():
        payload.extend(struct.pack("!HI", setting_id, value))

    return HTTP2Frame(frame_type=0x4, flags=0x0, stream_id=0, payload=bytes(payload))


def make_window_update_frame(stream_id: int, increment: int) -> HTTP2Frame:
    if increment < 1 or increment > 0x7FFFFFFF:
        raise ProtocolError("WINDOW_UPDATE increment must be 1 to 2147483647")

    return HTTP2Frame(
        frame_type=0x8,
        flags=0,
        stream_id=stream_id,
        payload=struct.pack("!I", increment),
    )


def make_goaway_frame(last_stream_id: int, error_code: int = 0) -> HTTP2Frame:
    payload = struct.pack("!II", last_stream_id & 0x7FFFFFFF, error_code)
    return HTTP2Frame(frame_type=0x7, flags=0, stream_id=0, payload=payload)


# ================================================================
# HPACK static-table support
# ================================================================

# Relevant HTTP/2 HPACK RFC 7541 static-table entries (index starts at 1).
HPACK_STATIC_TABLE = {
    1: (":authority", ""),
    2: (":method", "GET"),
    3: (":method", "POST"),
    4: (":path", "/"),
    5: (":path", "/index.html"),
    6: (":scheme", "http"),
    7: (":scheme", "https"),
    8: (":status", "200"),
    9: (":status", "204"),
    10: (":status", "206"),
    11: (":status", "304"),
    12: (":status", "400"),
    13: (":status", "404"),
    14: (":status", "500"),
    16: ("accept-encoding", "gzip, deflate"),
    19: ("accept", ""),
    23: ("authorization", ""),
    28: ("content-length", ""),
    31: ("content-type", ""),
    32: ("cookie", ""),
    33: ("date", ""),
    38: ("host", ""),
    54: ("server", ""),
    58: ("user-agent", ""),
}


def hpack_decode_static_indexed(header_block: bytes) -> list[tuple[str, str]]:
    """
    Decode basic HPACK indexed fields using static table only.

    Example:
    b'\\x82\\x87\\x84' -> :method GET, :scheme https, :path /
    """
    headers = []
    offset = 0

    while offset < len(header_block):
        first_byte = header_block[offset]

        # Indexed Header Field Representation: 1xxxxxxx
        if first_byte & 0x80:
            index = first_byte & 0x7F
            offset += 1

            if index == 0:
                raise ProtocolError("HPACK index zero is invalid")

            if index not in HPACK_STATIC_TABLE:
                raise ProtocolError(
                    f"HPACK index {index} is not in supported static table"
                )

            headers.append(HPACK_STATIC_TABLE[index])
            continue

        raise ProtocolError(
            "This demo supports only HPACK static indexed header fields"
        )

    return headers


def describe_http2_frame(frame: HTTP2Frame) -> str:
    details = (
        f"{frame.type_name}: stream={frame.stream_id}, "
        f"flags=0x{frame.flags:02X}, payload={len(frame.payload)} bytes"
    )

    if frame.type_name == "DATA":
        return details + f", data={safe_decode(frame.payload)!r}"

    if frame.type_name == "HEADERS":
        try:
            headers = hpack_decode_static_indexed(frame.payload)
            return details + f", decoded_headers={headers}"
        except ProtocolError as error:
            return details + f", HPACK={error}"

    if frame.type_name == "SETTINGS":
        if len(frame.payload) % 6 != 0:
            return details + ", invalid settings payload"

        settings = []
        for position in range(0, len(frame.payload), 6):
            setting_id, value = struct.unpack(
                "!HI",
                frame.payload[position:position + 6],
            )
            settings.append((setting_id, value))

        return details + f", settings={settings}"

    if frame.type_name == "WINDOW_UPDATE" and len(frame.payload) == 4:
        increment = struct.unpack("!I", frame.payload)[0] & 0x7FFFFFFF
        return details + f", increment={increment}"

    if frame.type_name == "GOAWAY" and len(frame.payload) >= 8:
        last_stream, error_code = struct.unpack("!II", frame.payload[:8])
        return details + (
            f", last_stream={last_stream & 0x7FFFFFFF}, error_code={error_code}"
        )

    return details


# ================================================================
# Demonstration
# ================================================================

def run_http11_demo() -> int:
    print_title("HTTP/1.1 REQUEST: CHUNKED BODY, COOKIE, KEEP-ALIVE")

    raw_request = (
        b"POST /upload?project=protocol HTTP/1.1\r\n"
        b"Host: example.local\r\n"
        b"User-Agent: Python-Protocol-Simulator/1.0\r\n"
        b"Connection: keep-alive\r\n"
        b"Cookie: session_id=abc123\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"7\r\n"
        b"message\r\n"
        b"6\r\n"
        b"=hello\r\n"
        b"0\r\n"
        b"\r\n"
    )

    request = parse_http11(raw_request)

    print("Start line:", request.start_line)
    print("Method:", request.method)
    print("Target:", request.target)
    print("Query parameters:", parse_qs(urlparse(request.target).query))
    print("Headers:", request.headers)
    print("Decoded body:", safe_decode(request.body))
    print("Keep-Alive:", is_keep_alive(request))

    print_title("HTTP/1.1 RESPONSE: COOKIE JAR")

    raw_response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Content-Length: 7\r\n"
        b"Set-Cookie: visitor=alice; Path=/\r\n"
        b"Connection: keep-alive\r\n"
        b"\r\n"
        b"Success"
    )

    response = parse_http11(raw_response)
    cookie_jar = CookieJar()
    cookie_jar.add_from_set_cookie(response.header("set-cookie"))

    print("Status:", response.status_code, response.reason)
    print("Body:", safe_decode(response.body))
    print("Keep-Alive:", is_keep_alive(response))
    print("Cookie sent to /dashboard:", cookie_jar.header_for_url(
        "https://example.local/dashboard"
    ))

    print_title("HTTP/1.1 MULTIPART/FORM-DATA")

    boundary = "----PythonBoundary2026"
    multipart_body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="username"\r\n'
        "\r\n"
        "alice\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="note.txt"\r\n'
        "Content-Type: text/plain\r\n"
        "\r\n"
        "Protocol engineering demo\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    multipart_parts = parse_multipart(
        multipart_body,
        f"multipart/form-data; boundary={boundary}",
    )

    for part in multipart_parts:
        print(part)

    return len(raw_request) + len(raw_response)


def run_http2_demo() -> int:
    print_title("HTTP/2 BINARY FRAME PARSER + HPACK STATIC TABLE")

    # HPACK indexes: 2=:method GET, 7=:scheme https, 4=:path /
    headers_frame = HTTP2Frame(
        frame_type=0x1,
        flags=0x5,  # END_STREAM + END_HEADERS
        stream_id=1,
        payload=b"\x82\x87\x84",
    )

    data_frame = HTTP2Frame(
        frame_type=0x0,
        flags=0x1,  # END_STREAM
        stream_id=1,
        payload=b"Hello HTTP/2",
    )

    settings_frame = make_settings_frame({
        0x1: 4096,     # HEADER_TABLE_SIZE
        0x3: 100,      # MAX_CONCURRENT_STREAMS
        0x4: 65535,    # INITIAL_WINDOW_SIZE
    })

    window_frame = make_window_update_frame(stream_id=1, increment=65535)
    goaway_frame = make_goaway_frame(last_stream_id=1, error_code=0)

    wire_data = b"".join(
        frame.encode()
        for frame in [
            settings_frame,
            headers_frame,
            data_frame,
            window_frame,
            goaway_frame,
        ]
    )

    frames = parse_http2_frames(wire_data)

    for frame in frames:
        print(describe_http2_frame(frame))

    return len(wire_data)


def main() -> None:
    try:
        http11_size = run_http11_demo()
        http2_size = run_http2_demo()

        print_title("HTTP/1.1 VS HTTP/2 PROTOCOL OVERHEAD")

        http11_estimated_header_bytes = 190
        http2_frame_header_bytes = 9 * 5
        hpack_header_block_bytes = 3

        print(f"HTTP/1.1 demo wire bytes: {http11_size}")
        print(f"HTTP/2 demo wire bytes:   {http2_size}")
        print(f"Example HTTP/1.1 header overhead: {http11_estimated_header_bytes} bytes")
        print(f"HTTP/2 frame-header overhead:      {http2_frame_header_bytes} bytes")
        print(f"HPACK compressed header block:      {hpack_header_block_bytes} bytes")
        print("\nCompleted successfully.")

    except ProtocolError as error:
        print(f"\nProtocol input error handled safely: {error}")

    except Exception as error:
        print(f"\nUnexpected error handled safely: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()