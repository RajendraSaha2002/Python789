

from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
import threading
import time
from dataclasses import dataclass


HOST = "127.0.0.1"
PORT = 8765
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketError(Exception):
    pass


# ================================================================
# WebSocket frame constants
# ================================================================

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA

OPCODE_NAMES = {
    OPCODE_CONTINUATION: "CONTINUATION",
    OPCODE_TEXT: "TEXT",
    OPCODE_BINARY: "BINARY",
    OPCODE_CLOSE: "CLOSE",
    OPCODE_PING: "PING",
    OPCODE_PONG: "PONG",
}


@dataclass
class WebSocketFrame:
    fin: bool
    opcode: int
    payload: bytes
    masked: bool = False
    masking_key: bytes = b""

    @property
    def opcode_name(self) -> str:
        return OPCODE_NAMES.get(self.opcode, f"UNKNOWN({self.opcode})")

    def text(self) -> str:
        return self.payload.decode("utf-8", errors="replace")


# ================================================================
# Socket helpers
# ================================================================

def recv_exact(sock: socket.socket, length: int) -> bytes:
    """Read exactly length bytes from a socket."""
    data = bytearray()

    while len(data) < length:
        try:
            chunk = sock.recv(length - len(data))
        except socket.timeout as error:
            raise WebSocketError("Socket read timed out") from error

        if not chunk:
            raise WebSocketError("Connection closed unexpectedly")

        data.extend(chunk)

    return bytes(data)


def recv_http_headers(sock: socket.socket, limit: int = 16384) -> bytes:
    """Read HTTP headers until CRLF CRLF."""
    data = bytearray()

    while b"\r\n\r\n" not in data:
        chunk = sock.recv(1024)

        if not chunk:
            raise WebSocketError("Connection closed before HTTP headers completed")

        data.extend(chunk)

        if len(data) > limit:
            raise WebSocketError("HTTP headers exceed safe size limit")

    return bytes(data)


# ================================================================
# HTTP Upgrade handshake
# ================================================================

def websocket_accept_value(client_key: str) -> str:
    """Create Sec-WebSocket-Accept value defined by RFC 6455."""
    source = (client_key.strip() + WEBSOCKET_GUID).encode("ascii")
    sha1_hash = hashlib.sha1(source).digest()
    return base64.b64encode(sha1_hash).decode("ascii")


def parse_http_headers(request: bytes) -> tuple[str, dict[str, str]]:
    text = request.decode("iso-8859-1")
    lines = text.split("\r\n")

    if not lines or not lines[0]:
        raise WebSocketError("Invalid HTTP request")

    start_line = lines[0]
    headers: dict[str, str] = {}

    for line in lines[1:]:
        if not line:
            continue

        if ":" not in line:
            raise WebSocketError(f"Invalid HTTP header: {line}")

        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    return start_line, headers


def validate_upgrade_request(start_line: str, headers: dict[str, str]) -> str:
    """Validate a WebSocket HTTP Upgrade request and return client key."""
    if not start_line.startswith("GET "):
        raise WebSocketError("WebSocket handshake must use GET")

    if headers.get("upgrade", "").lower() != "websocket":
        raise WebSocketError("Missing Upgrade: websocket header")

    connection = headers.get("connection", "").lower()
    if "upgrade" not in connection:
        raise WebSocketError("Missing Connection: Upgrade header")

    if headers.get("sec-websocket-version") != "13":
        raise WebSocketError("Only WebSocket version 13 is supported")

    client_key = headers.get("sec-websocket-key", "")

    if not client_key:
        raise WebSocketError("Missing Sec-WebSocket-Key header")

    try:
        decoded_key = base64.b64decode(client_key.encode("ascii"), validate=True)
    except Exception as error:
        raise WebSocketError("Invalid Sec-WebSocket-Key encoding") from error

    if len(decoded_key) != 16:
        raise WebSocketError("Sec-WebSocket-Key must decode to 16 bytes")

    return client_key


def server_handshake(sock: socket.socket) -> None:
    request = recv_http_headers(sock)
    start_line, headers = parse_http_headers(request)
    client_key = validate_upgrade_request(start_line, headers)

    accept = websocket_accept_value(client_key)

    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    )

    sock.sendall(response.encode("ascii"))
    print("SERVER: HTTP Upgrade handshake accepted.")


def client_handshake(sock: socket.socket) -> None:
    raw_key = os.urandom(16)
    client_key = base64.b64encode(raw_key).decode("ascii")

    request = (
        "GET /echo HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {client_key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )

    print("CLIENT: Sending HTTP Upgrade request.")
    sock.sendall(request.encode("ascii"))

    response = recv_http_headers(sock)
    start_line, headers = parse_http_headers(response)

    if not start_line.startswith("HTTP/1.1 101"):
        raise WebSocketError(f"Handshake failed: {start_line}")

    expected_accept = websocket_accept_value(client_key)
    received_accept = headers.get("sec-websocket-accept", "")

    if received_accept != expected_accept:
        raise WebSocketError("Sec-WebSocket-Accept verification failed")

    print("CLIENT: Server handshake verified successfully.")


# ================================================================
# WebSocket frame encode/decode
# ================================================================

def apply_mask(payload: bytes, masking_key: bytes) -> bytes:
    """Apply WebSocket XOR mask. Calling twice restores original data."""
    if len(masking_key) != 4:
        raise WebSocketError("Masking key must be exactly 4 bytes")

    return bytes(
        value ^ masking_key[index % 4]
        for index, value in enumerate(payload)
    )


def encode_frame(
    payload: bytes,
    opcode: int,
    fin: bool = True,
    mask: bool = False,
) -> bytes:
    """Encode a WebSocket frame according to RFC 6455."""
    if opcode not in OPCODE_NAMES:
        raise WebSocketError(f"Unsupported opcode: {opcode}")

    # Control frames must not be fragmented and must stay <=125 bytes.
    if opcode >= 0x8 and (not fin or len(payload) > 125):
        raise WebSocketError("Invalid control frame size or fragmentation")

    first_byte = (0x80 if fin else 0x00) | opcode
    payload_length = len(payload)
    second_byte = 0x80 if mask else 0x00

    encoded = bytearray([first_byte])

    if payload_length <= 125:
        encoded.append(second_byte | payload_length)

    elif payload_length <= 65535:
        encoded.append(second_byte | 126)
        encoded.extend(struct.pack("!H", payload_length))

    else:
        encoded.append(second_byte | 127)
        encoded.extend(struct.pack("!Q", payload_length))

    if mask:
        masking_key = os.urandom(4)
        encoded.extend(masking_key)
        encoded.extend(apply_mask(payload, masking_key))
    else:
        encoded.extend(payload)

    return bytes(encoded)


def decode_frame(sock: socket.socket, require_mask: bool | None = None) -> WebSocketFrame:
    """Read and parse one WebSocket frame from the socket."""
    first_two = recv_exact(sock, 2)

    first_byte = first_two[0]
    second_byte = first_two[1]

    fin = bool(first_byte & 0x80)
    rsv_bits = first_byte & 0x70
    opcode = first_byte & 0x0F

    if rsv_bits != 0:
        raise WebSocketError("RSV bits require an unsupported extension")

    if opcode not in OPCODE_NAMES:
        raise WebSocketError(f"Unsupported WebSocket opcode: {opcode}")

    masked = bool(second_byte & 0x80)
    payload_length = second_byte & 0x7F

    if require_mask is not None and masked != require_mask:
        expected = "masked" if require_mask else "unmasked"
        raise WebSocketError(f"Expected {expected} WebSocket frame")

    if payload_length == 126:
        payload_length = struct.unpack("!H", recv_exact(sock, 2))[0]

    elif payload_length == 127:
        payload_length = struct.unpack("!Q", recv_exact(sock, 8))[0]

        if payload_length & (1 << 63):
            raise WebSocketError("Invalid 64-bit WebSocket payload length")

    if opcode >= 0x8 and (not fin or payload_length > 125):
        raise WebSocketError("Invalid WebSocket control frame")

    if payload_length > 16 * 1024 * 1024:
        raise WebSocketError("Frame payload exceeds 16 MB safety limit")

    masking_key = recv_exact(sock, 4) if masked else b""
    received_payload = recv_exact(sock, payload_length)

    payload = (
        apply_mask(received_payload, masking_key)
        if masked
        else received_payload
    )

    return WebSocketFrame(
        fin=fin,
        opcode=opcode,
        payload=payload,
        masked=masked,
        masking_key=masking_key,
    )


def send_frame(
    sock: socket.socket,
    payload: bytes,
    opcode: int,
    mask: bool,
) -> None:
    frame = encode_frame(payload=payload, opcode=opcode, mask=mask)
    sock.sendall(frame)


# ================================================================
# Server and client loopback simulation
# ================================================================

class LocalWebSocketServer(threading.Thread):
    def __init__(self, ready: threading.Event) -> None:
        super().__init__(daemon=True)
        self.ready = ready
        self.error: Exception | None = None

    def run(self) -> None:
        server_socket: socket.socket | None = None
        client_socket: socket.socket | None = None

        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((HOST, PORT))
            server_socket.listen(1)
            server_socket.settimeout(10)

            print(f"SERVER: Listening on ws://{HOST}:{PORT}/echo")
            self.ready.set()

            client_socket, address = server_socket.accept()
            client_socket.settimeout(10)

            print(f"SERVER: Client connected from {address[0]}:{address[1]}")
            server_handshake(client_socket)

            while True:
                # RFC 6455 requires client-to-server frames to be masked.
                frame = decode_frame(client_socket, require_mask=True)

                print(
                    f"SERVER: Received {frame.opcode_name}, "
                    f"FIN={frame.fin}, payload={frame.payload!r}"
                )

                if frame.opcode == OPCODE_TEXT:
                    send_frame(
                        client_socket,
                        b"Echo: " + frame.payload,
                        OPCODE_TEXT,
                        mask=False,
                    )

                elif frame.opcode == OPCODE_BINARY:
                    send_frame(
                        client_socket,
                        frame.payload,
                        OPCODE_BINARY,
                        mask=False,
                    )

                elif frame.opcode == OPCODE_PING:
                    send_frame(
                        client_socket,
                        frame.payload,
                        OPCODE_PONG,
                        mask=False,
                    )

                elif frame.opcode == OPCODE_CLOSE:
                    send_frame(
                        client_socket,
                        frame.payload,
                        OPCODE_CLOSE,
                        mask=False,
                    )
                    print("SERVER: Close frame exchanged.")
                    break

        except Exception as error:
            self.error = error
            print(f"SERVER: Handled error: {type(error).__name__}: {error}")
            self.ready.set()

        finally:
            if client_socket:
                try:
                    client_socket.close()
                except OSError:
                    pass

            if server_socket:
                try:
                    server_socket.close()
                except OSError:
                    pass


def client_demo() -> None:
    sock: socket.socket | None = None

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((HOST, PORT))

        client_handshake(sock)

        print("\nCLIENT: Sending TEXT frame.")
        send_frame(sock, b"Hello from Python client", OPCODE_TEXT, mask=True)
        response = decode_frame(sock, require_mask=False)
        print(f"CLIENT: Received {response.opcode_name}: {response.text()}")

        print("\nCLIENT: Sending BINARY frame.")
        send_frame(sock, bytes([1, 2, 3, 4, 255]), OPCODE_BINARY, mask=True)
        response = decode_frame(sock, require_mask=False)
        print(f"CLIENT: Received {response.opcode_name}: {response.payload!r}")

        print("\nCLIENT: Sending PING frame.")
        send_frame(sock, b"are-you-alive", OPCODE_PING, mask=True)
        response = decode_frame(sock, require_mask=False)
        print(f"CLIENT: Received {response.opcode_name}: {response.payload!r}")

        print("\nCLIENT: Sending CLOSE frame.")
        close_payload = struct.pack("!H", 1000) + b"Normal closure"
        send_frame(sock, close_payload, OPCODE_CLOSE, mask=True)
        response = decode_frame(sock, require_mask=False)

        close_code = struct.unpack("!H", response.payload[:2])[0]
        close_reason = response.payload[2:].decode("utf-8", errors="replace")

        print(
            f"CLIENT: Received {response.opcode_name}, "
            f"code={close_code}, reason={close_reason!r}"
        )

    except Exception as error:
        print(f"CLIENT: Handled error: {type(error).__name__}: {error}")

    finally:
        if sock:
            try:
                sock.close()
            except OSError:
                pass


def main() -> None:
    print("=" * 72)
    print("WEBSOCKET RFC 6455 HANDSHAKE AND FRAME CODEC SIMULATOR")
    print("=" * 72)

    ready = threading.Event()
    server = LocalWebSocketServer(ready)
    server.start()

    if not ready.wait(timeout=5):
        print("Could not start local server.")
        return

    if server.error:
        print(f"Server startup failed: {server.error}")
        return

    time.sleep(0.2)
    client_demo()

    server.join(timeout=5)

    if server.is_alive():
        print("Server did not stop in time.")
    elif server.error:
        print(f"Server finished with handled error: {server.error}")
    else:
        print("\nSimulation completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as error:
        print(f"\nUnexpected error handled safely: {type(error).__name__}: {error}")