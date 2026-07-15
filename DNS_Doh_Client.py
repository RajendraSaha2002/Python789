

import argparse
import base64
import ipaddress
import json
import random
import struct
import sys
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any


QTYPE = {
    "A": 1,
    "NS": 2,
    "CNAME": 5,
    "SOA": 6,
    "PTR": 12,
    "MX": 15,
    "TXT": 16,
    "AAAA": 28,
    "ANY": 255,
}

QCLASS = {"IN": 1}
TYPE_NAME = {value: key for key, value in QTYPE.items()}
CLASS_NAME = {value: key for key, value in QCLASS.items()}

DEFAULT_RESOLVERS = [
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/dns-query",
    "https://dns.quad9.net/dns-query",
]

RCODE_NAMES = {
    0: "NOERROR",
    1: "FORMERR",
    2: "SERVFAIL",
    3: "NXDOMAIN",
    4: "NOTIMP",
    5: "REFUSED",
}


class DNSError(Exception):
    """Raised for invalid DNS packets or DNS protocol errors."""


@dataclass
class Question:
    name: str
    qtype: int
    qclass: int


@dataclass
class ResourceRecord:
    name: str
    rtype: int
    rclass: int
    ttl: int
    rdata: Any


@dataclass
class DNSMessage:
    message_id: int
    flags: int
    questions: list[Question] = field(default_factory=list)
    answers: list[ResourceRecord] = field(default_factory=list)
    authorities: list[ResourceRecord] = field(default_factory=list)
    additionals: list[ResourceRecord] = field(default_factory=list)

    @property
    def rcode(self) -> int:
        return self.flags & 0x000F


def encode_name(name: str) -> bytes:
    """Encode a DNS domain name into RFC 1035 wire format."""
    name = name.strip().rstrip(".")

    if not name or name == ".":
        return b"\x00"

    output = bytearray()

    for label in name.split("."):
        encoded_label = label.encode("idna")

        if len(encoded_label) == 0 or len(encoded_label) > 63:
            raise DNSError(f"Invalid domain label: {label}")

        output.append(len(encoded_label))
        output.extend(encoded_label)

    output.append(0)

    if len(output) > 255:
        raise DNSError("Domain name is longer than 255 bytes")

    return bytes(output)


def decode_name(data: bytes, offset: int) -> tuple[str, int]:
    """
    Decode an RFC 1035 DNS name.
    Supports DNS compression pointers.
    """
    labels = []
    original_end = None
    jumps = 0

    while True:
        if offset >= len(data):
            raise DNSError("DNS name exceeds packet length")

        length = data[offset]

        if length == 0:
            offset += 1
            if original_end is None:
                original_end = offset
            break

        # Compression pointer: first two bits are 11.
        if (length & 0xC0) == 0xC0:
            if offset + 1 >= len(data):
                raise DNSError("Truncated DNS compression pointer")

            pointer = ((length & 0x3F) << 8) | data[offset + 1]

            if pointer >= len(data):
                raise DNSError("DNS compression pointer is outside packet")

            if original_end is None:
                original_end = offset + 2

            offset = pointer
            jumps += 1

            if jumps > 255:
                raise DNSError("DNS compression-pointer loop detected")

            continue

        # RFC 1035 normal label.
        if length & 0xC0:
            raise DNSError("Unsupported DNS label format")

        offset += 1

        if offset + length > len(data):
            raise DNSError("Truncated DNS label")

        try:
            labels.append(data[offset:offset + length].decode("idna"))
        except UnicodeError:
            labels.append(data[offset:offset + length].decode("utf-8", "replace"))

        offset += length

    return ".".join(labels) if labels else ".", original_end


def parse_rdata(data: bytes, rtype: int, start: int, length: int) -> Any:
    """Parse supported RDATA types."""
    end = start + length

    if end > len(data):
        raise DNSError("RDATA exceeds packet length")

    raw = data[start:end]

    if rtype == QTYPE["A"]:
        if length != 4:
            raise DNSError("A record must contain exactly 4 bytes")
        return str(ipaddress.IPv4Address(raw))

    if rtype == QTYPE["AAAA"]:
        if length != 16:
            raise DNSError("AAAA record must contain exactly 16 bytes")
        return str(ipaddress.IPv6Address(raw))

    if rtype in (QTYPE["CNAME"], QTYPE["PTR"], QTYPE["NS"]):
        hostname, next_offset = decode_name(data, start)
        if next_offset > end:
            raise DNSError("Hostname RDATA exceeds record length")
        return hostname

    if rtype == QTYPE["MX"]:
        if length < 3:
            raise DNSError("Invalid MX record length")

        preference = struct.unpack("!H", data[start:start + 2])[0]
        exchange, next_offset = decode_name(data, start + 2)

        if next_offset > end:
            raise DNSError("MX exchange exceeds record length")

        return {"preference": preference, "exchange": exchange}

    if rtype == QTYPE["TXT"]:
        values = []
        position = start

        while position < end:
            text_length = data[position]
            position += 1

            if position + text_length > end:
                raise DNSError("Truncated TXT record")

            values.append(
                data[position:position + text_length].decode("utf-8", "replace")
            )
            position += text_length

        return values

    # Preserve unsupported record data safely.
    return {"hex": raw.hex()}


def parse_resource_record(data: bytes, offset: int) -> tuple[ResourceRecord, int]:
    name, offset = decode_name(data, offset)

    if offset + 10 > len(data):
        raise DNSError("Truncated DNS resource-record header")

    rtype, rclass, ttl, rdlength = struct.unpack(
        "!HHIH",
        data[offset:offset + 10]
    )

    rdata_start = offset + 10
    next_offset = rdata_start + rdlength

    if next_offset > len(data):
        raise DNSError("Truncated DNS resource-record data")

    rdata = parse_rdata(data, rtype, rdata_start, rdlength)

    return ResourceRecord(name, rtype, rclass, ttl, rdata), next_offset


def parse_dns_message(data: bytes) -> DNSMessage:
    """Decode a complete DNS response packet."""
    if len(data) < 12:
        raise DNSError("DNS response is smaller than the 12-byte header")

    message_id, flags, qdcount, ancount, nscount, arcount = struct.unpack(
        "!HHHHHH",
        data[:12]
    )

    offset = 12
    message = DNSMessage(message_id, flags)

    for _ in range(qdcount):
        name, offset = decode_name(data, offset)

        if offset + 4 > len(data):
            raise DNSError("Truncated DNS question")

        qtype, qclass = struct.unpack("!HH", data[offset:offset + 4])
        offset += 4
        message.questions.append(Question(name, qtype, qclass))

    sections = (
        (message.answers, ancount),
        (message.authorities, nscount),
        (message.additionals, arcount),
    )

    for section, count in sections:
        for _ in range(count):
            record, offset = parse_resource_record(data, offset)
            section.append(record)

    return message


def build_dns_query(domain: str, record_type: str) -> tuple[bytes, int]:
    """Build a recursive standard DNS query packet."""
    record_type = record_type.upper()

    if record_type not in QTYPE:
        raise DNSError(f"Unsupported record type: {record_type}")

    message_id = random.randint(0, 65535)
    flags = 0x0100  # Recursion desired.

    header = struct.pack(
        "!HHHHHH",
        message_id,
        flags,
        1,  # Questions
        0,  # Answers
        0,  # Authorities
        0,  # Additionals
    )

    question = (
        encode_name(domain)
        + struct.pack("!HH", QTYPE[record_type], QCLASS["IN"])
    )

    return header + question, message_id


def doh_query(resolver: str, wire_query: bytes, timeout: float) -> bytes:
    """Send an RFC 8484 DNS-over-HTTPS GET request."""
    encoded_query = base64.urlsafe_b64encode(wire_query).rstrip(b"=").decode("ascii")

    separator = "&" if "?" in resolver else "?"
    url = resolver + separator + urllib.parse.urlencode({"dns": encoded_query})

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/dns-message",
            "User-Agent": "Python-DNS-DoH-Client/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()

    except urllib.error.HTTPError as error:
        raise DNSError(f"HTTP error {error.code}: {error.reason}") from error

    except urllib.error.URLError as error:
        raise DNSError(f"Network error: {error.reason}") from error

    except TimeoutError as error:
        raise DNSError("Connection timed out") from error

    if not body:
        raise DNSError("DoH resolver returned an empty response")

    if "application/dns-message" not in content_type.lower():
        raise DNSError(f"Unexpected response type: {content_type}")

    return body


def rdata_to_text(record: ResourceRecord) -> str:
    if record.rtype == QTYPE["MX"]:
        return f'{record.rdata["preference"]} {record.rdata["exchange"]}'

    if record.rtype == QTYPE["TXT"]:
        return " ".join(f'"{value}"' for value in record.rdata)

    if isinstance(record.rdata, dict):
        return record.rdata.get("hex", json.dumps(record.rdata))

    return str(record.rdata)


def print_section(title: str, records: list[ResourceRecord]) -> None:
    print(f"\n{title}")

    if not records:
        print("  (empty)")
        return

    for record in records:
        type_name = TYPE_NAME.get(record.rtype, f"TYPE{record.rtype}")
        class_name = CLASS_NAME.get(record.rclass, f"CLASS{record.rclass}")

        print(
            f"  {record.name:<30} "
            f"{record.ttl:<8} "
            f"{class_name:<6} "
            f"{type_name:<7} "
            f"{rdata_to_text(record)}"
        )


def normalized_answers(message: DNSMessage) -> set[tuple[str, str, str]]:
    """Create TTL-independent answer data for resolver comparison."""
    return {
        (
            record.name.lower().rstrip("."),
            TYPE_NAME.get(record.rtype, f"TYPE{record.rtype}"),
            rdata_to_text(record).lower().rstrip("."),
        )
        for record in message.answers
    }


def message_as_dict(message: DNSMessage) -> dict[str, Any]:
    def record_dict(record: ResourceRecord) -> dict[str, Any]:
        return {
            "name": record.name,
            "type": TYPE_NAME.get(record.rtype, f"TYPE{record.rtype}"),
            "class": CLASS_NAME.get(record.rclass, f"CLASS{record.rclass}"),
            "ttl": record.ttl,
            "rdata": record.rdata,
        }

    return {
        "id": message.message_id,
        "flags": f"0x{message.flags:04X}",
        "rcode": RCODE_NAMES.get(message.rcode, f"RCODE{message.rcode}"),
        "answers": [record_dict(x) for x in message.answers],
        "authorities": [record_dict(x) for x in message.authorities],
        "additionals": [record_dict(x) for x in message.additionals],
    }


def get_interactive_values() -> tuple[str, str]:
    print("=" * 60)
    print(" DNS RFC 1035 + DNS-over-HTTPS Client")
    print("=" * 60)

    while True:
        domain = input("\nEnter domain name (example: google.com): ").strip()

        if domain:
            break

        print("Domain name cannot be empty.")

    allowed = ", ".join(QTYPE.keys())

    while True:
        record_type = input(f"Enter record type [{allowed}] (default A): ").strip().upper()

        if not record_type:
            record_type = "A"

        if record_type in QTYPE:
            break

        print(f"Invalid record type. Choose: {allowed}")

    return domain, record_type


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RFC 1035 DNS parser and DNS-over-HTTPS client"
    )

    parser.add_argument("domain", nargs="?", help="Domain name, e.g. example.com")
    parser.add_argument(
        "-t",
        "--type",
        default="A",
        choices=sorted(QTYPE.keys()),
        help="DNS record type",
    )
    parser.add_argument(
        "-r",
        "--resolver",
        action="append",
        help="DoH resolver URL. Can be used multiple times.",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    # No command-line domain: run safely in interactive mode.
    if not args.domain:
        try:
            args.domain, args.type = get_interactive_values()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return 0

    try:
        wire_query, query_id = build_dns_query(args.domain, args.type)
    except DNSError as error:
        print(f"\nInput error: {error}")
        return 1

    resolvers = args.resolver if args.resolver else DEFAULT_RESOLVERS
    successful_results: dict[str, DNSMessage] = {}
    failed_results: dict[str, str] = {}

    for resolver in resolvers:
        try:
            response = doh_query(resolver, wire_query, args.timeout)
            message = parse_dns_message(response)

            if message.message_id != query_id:
                raise DNSError("Response transaction ID does not match the query")

            successful_results[resolver] = message

        except Exception as error:
            failed_results[resolver] = str(error)

    if args.json:
        output = {
            "domain": args.domain,
            "record_type": args.type,
            "results": {
                resolver: message_as_dict(message)
                for resolver, message in successful_results.items()
            },
            "failures": failed_results,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    else:
        print(f"\nQuery: {args.domain} ({args.type})")

        for resolver, message in successful_results.items():
            print("\n" + "=" * 72)
            print(f"Resolver: {resolver}")
            print(f"Response status: {RCODE_NAMES.get(message.rcode, message.rcode)}")
            print_section("ANSWER SECTION", message.answers)
            print_section("AUTHORITY SECTION", message.authorities)
            print_section("ADDITIONAL SECTION", message.additionals)

        for resolver, error in failed_results.items():
            print("\n" + "=" * 72)
            print(f"Resolver: {resolver}")
            print(f"Connection/query failed: {error}")

    if len(successful_results) >= 2:
        answer_groups: dict[frozenset, list[str]] = {}

        for resolver, message in successful_results.items():
            answer_set = frozenset(normalized_answers(message))
            answer_groups.setdefault(answer_set, []).append(resolver)

        print("\n" + "=" * 72)

        if len(answer_groups) == 1:
            print("Resolver comparison: CONSISTENT")
        else:
            print("Resolver comparison: INCONSISTENT ANSWERS DETECTED")

            for answer_set, resolver_list in answer_groups.items():
                print(f"\nResolvers: {', '.join(resolver_list)}")

                if not answer_set:
                    print("  (no answer records)")

                for name, record_type, value in sorted(answer_set):
                    print(f"  {name}  {record_type}  {value}")

    if not successful_results:
        print("\nNo resolver returned a valid DNS response.")
        return 1

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
        raise SystemExit(0)
    except Exception as unexpected_error:
        print(f"\nUnexpected error handled safely: {unexpected_error}")
        raise SystemExit(1)