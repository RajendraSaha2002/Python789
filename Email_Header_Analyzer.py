import email
import re
import socket
import urllib.parse
import urllib.request
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime


def decode_email_header(value):
    """Decode MIME encoded-word email headers safely."""
    if not value:
        return ""

    decoded_parts = []

    for part, charset in decode_header(value):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(
                    part.decode(charset or "utf-8", errors="replace")
                )
            except LookupError:
                decoded_parts.append(
                    part.decode("utf-8", errors="replace")
                )
        else:
            decoded_parts.append(part)

    return "".join(decoded_parts)


def extract_domain(email_address):
    if not email_address or "@" not in email_address:
        return ""

    return email_address.rsplit("@", 1)[1].lower().strip()


def has_control_characters(value):
    if not value:
        return False

    return any(
        ord(character) < 32
        and character not in ("\r", "\n", "\t")
        for character in value
    )


def has_header_injection_pattern(value):
    if not value:
        return False

    return bool(
        re.search(
            r"[\r\n]\s*(?:to|from|subject|bcc|cc|reply-to|return-path)\s*:",
            value,
            flags=re.IGNORECASE,
        )
    )


def parse_received_header(received_header):
    """Extract useful information from one Received header."""
    cleaned = " ".join(received_header.split())

    from_match = re.search(
        r"\bfrom\s+([^\s(;,]+)",
        cleaned,
        flags=re.IGNORECASE,
    )

    by_match = re.search(
        r"\bby\s+([^\s(;,]+)",
        cleaned,
        flags=re.IGNORECASE,
    )

    with_match = re.search(
        r"\bwith\s+([^\s;,]+)",
        cleaned,
        flags=re.IGNORECASE,
    )

    ip_match = re.search(
        r"\[([0-9a-fA-F:.]+)\]",
        cleaned,
    )

    date_text = ""

    if ";" in cleaned:
        date_text = cleaned.rsplit(";", 1)[1].strip()

    parsed_date = None

    if date_text:
        try:
            parsed_date = parsedate_to_datetime(date_text)
        except (TypeError, ValueError, IndexError):
            parsed_date = None

    return {
        "raw": cleaned,
        "from": from_match.group(1) if from_match else "Unknown",
        "by": by_match.group(1) if by_match else "Unknown",
        "protocol": with_match.group(1) if with_match else "Unknown",
        "ip": ip_match.group(1) if ip_match else "Unknown",
        "date": parsed_date.isoformat() if parsed_date else date_text,
        "parsed_datetime": parsed_date,
    }


def query_spf_record(domain):
    """
    Query DNS TXT records using Cloudflare DNS-over-HTTPS.
    Returns SPF records when available.
    """
    if not domain:
        return {
            "status": "Skipped",
            "records": [],
            "error": "No domain available.",
        }

    try:
        encoded_domain = urllib.parse.quote(domain)
        url = (
            "https://cloudflare-dns.com/dns-query?"
            f"name={encoded_domain}&type=TXT"
        )

        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/dns-json",
                "User-Agent": "Email-Header-Forensic-Analyzer/1.0",
            },
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            content = response.read().decode("utf-8", errors="replace")

        records = re.findall(
            r'"data"\s*:\s*"([^"]+)"',
            content,
            flags=re.IGNORECASE,
        )

        spf_records = []

        for record in records:
            cleaned = record.replace('\\"', '"').strip('"')

            if cleaned.lower().startswith("v=spf1"):
                spf_records.append(cleaned)

        return {
            "status": "Success",
            "records": spf_records,
            "error": "",
        }

    except Exception as error:
        return {
            "status": "Failed",
            "records": [],
            "error": str(error),
        }


def resolve_ip_address(ip_address):
    if not ip_address or ip_address == "Unknown":
        return "Unknown"

    try:
        return socket.gethostbyaddr(ip_address)[0]
    except (socket.herror, socket.gaierror, OSError):
        return "No reverse DNS result"


def analyse_headers(raw_headers):
    message = email.message_from_string(raw_headers)

    findings = []

    from_raw = message.get("From", "")
    reply_to_raw = message.get("Reply-To", "")
    return_path_raw = message.get("Return-Path", "")
    subject_raw = message.get("Subject", "")
    message_id_raw = message.get("Message-ID", "")
    authentication_results = message.get("Authentication-Results", "")

    from_display_name, from_email = parseaddr(
        decode_email_header(from_raw)
    )

    reply_to_display_name, reply_to_email = parseaddr(
        decode_email_header(reply_to_raw)
    )

    _, return_path_email = parseaddr(
        decode_email_header(return_path_raw)
    )

    from_domain = extract_domain(from_email)
    return_path_domain = extract_domain(return_path_email)
    reply_to_domain = extract_domain(reply_to_email)

    if not from_email:
        findings.append("Missing or malformed From address.")

    if return_path_email and from_domain != return_path_domain:
        findings.append(
            "From domain and Return-Path domain do not match."
        )

    if reply_to_email and reply_to_domain != from_domain:
        findings.append(
            "Reply-To domain differs from the From domain."
        )

    if from_display_name:
        display_name_lower = from_display_name.lower()
        domain_name_hint = from_domain.split(".")[0] if from_domain else ""

        if domain_name_hint and domain_name_hint not in display_name_lower:
            findings.append(
                "Display name does not resemble the sender domain."
            )

    all_headers = list(message.items())

    for header_name, header_value in all_headers:
        combined_value = f"{header_name}: {header_value}"

        if has_control_characters(combined_value):
            findings.append(
                f"Control character detected in header: {header_name}"
            )

        if has_header_injection_pattern(header_value):
            findings.append(
                f"Possible header injection pattern in: {header_name}"
            )

    received_headers = message.get_all("Received", [])
    received_path = [
        parse_received_header(value)
        for value in received_headers
    ]

    for item in received_path:
        item["reverse_dns"] = resolve_ip_address(item["ip"])

    parsed_dates = [
        item["parsed_datetime"]
        for item in received_path
        if item["parsed_datetime"] is not None
    ]

    timezone_warning = ""

    if len(parsed_dates) >= 2:
        for index in range(len(parsed_dates) - 1):
            current_date = parsed_dates[index]
            next_date = parsed_dates[index + 1]

            if current_date < next_date:
                timezone_warning = (
                    "Received header chronology is inconsistent. "
                    "This can indicate clock skew, timezone issues, or spoofing."
                )
                findings.append(timezone_warning)
                break

    spf_header_match = re.search(
        r"\bspf=(pass|fail|softfail|neutral|none|temperror|permerror)",
        authentication_results,
        flags=re.IGNORECASE,
    )

    dkim_header_match = re.search(
        r"\bdkim=(pass|fail|neutral|none|temperror|permerror)",
        authentication_results,
        flags=re.IGNORECASE,
    )

    dmarc_header_match = re.search(
        r"\bdmarc=(pass|fail|bestguesspass|none|temperror|permerror)",
        authentication_results,
        flags=re.IGNORECASE,
    )

    spf_result = (
        spf_header_match.group(1).lower()
        if spf_header_match
        else "Not found"
    )

    dkim_result = (
        dkim_header_match.group(1).lower()
        if dkim_header_match
        else "Not found"
    )

    dmarc_result = (
        dmarc_header_match.group(1).lower()
        if dmarc_header_match
        else "Not found"
    )

    if spf_result in ("fail", "softfail", "permerror", "temperror"):
        findings.append(f"SPF authentication result: {spf_result}")

    if dkim_result in ("fail", "permerror", "temperror"):
        findings.append(f"DKIM authentication result: {dkim_result}")

    if dmarc_result in ("fail", "permerror", "temperror"):
        findings.append(f"DMARC authentication result: {dmarc_result}")

    if not message_id_raw:
        findings.append("Message-ID header is missing.")

    spf_dns = query_spf_record(return_path_domain or from_domain)

    if not spf_dns["records"] and spf_dns["status"] == "Success":
        findings.append(
            "No SPF TXT record found for the selected sender domain."
        )

    return {
        "from": {
            "raw": decode_email_header(from_raw),
            "display_name": from_display_name,
            "email": from_email,
            "domain": from_domain,
        },
        "reply_to": {
            "raw": decode_email_header(reply_to_raw),
            "display_name": reply_to_display_name,
            "email": reply_to_email,
            "domain": reply_to_domain,
        },
        "return_path": {
            "raw": decode_email_header(return_path_raw),
            "email": return_path_email,
            "domain": return_path_domain,
        },
        "subject": decode_email_header(subject_raw),
        "message_id": message_id_raw,
        "mime_version": message.get("MIME-Version", "Not found"),
        "authentication_results_raw": authentication_results,
        "authentication_results": {
            "spf": spf_result,
            "dkim": dkim_result,
            "dmarc": dmarc_result,
        },
        "spf_dns_lookup": spf_dns,
        "received_path": received_path,
        "findings": findings,
    }


def print_report(report):
    print("\n" + "=" * 72)
    print("EMAIL HEADER FORENSIC REPORT")
    print("=" * 72)

    print("\nSender details:")
    print(f"  From: {report['from']['raw']}")
    print(f"  From domain: {report['from']['domain'] or 'Unknown'}")
    print(f"  Reply-To: {report['reply_to']['raw'] or 'Not present'}")
    print(
        f"  Return-Path: "
        f"{report['return_path']['raw'] or 'Not present'}"
    )

    print("\nMessage details:")
    print(f"  Subject: {report['subject']}")
    print(f"  Message-ID: {report['message_id'] or 'Not present'}")
    print(f"  MIME-Version: {report['mime_version']}")

    print("\nAuthentication results:")
    print(f"  SPF: {report['authentication_results']['spf']}")
    print(f"  DKIM: {report['authentication_results']['dkim']}")
    print(f"  DMARC: {report['authentication_results']['dmarc']}")

    spf_dns = report["spf_dns_lookup"]

    print("\nSPF DNS lookup:")
    print(f"  Status: {spf_dns['status']}")

    if spf_dns["records"]:
        for record in spf_dns["records"]:
            print(f"  Record: {record}")
    elif spf_dns["error"]:
        print(f"  Error: {spf_dns['error']}")
    else:
        print("  No SPF record found.")

    print("\nReceived delivery path:")

    if report["received_path"]:
        for index, item in enumerate(report["received_path"], start=1):
            print(f"\n  Hop {index}")
            print(f"    From: {item['from']}")
            print(f"    By: {item['by']}")
            print(f"    IP: {item['ip']}")
            print(f"    Reverse DNS: {item['reverse_dns']}")
            print(f"    Protocol: {item['protocol']}")
            print(f"    Date: {item['date']}")
    else:
        print("  No Received headers found.")

    print("\nForensic findings:")

    if report["findings"]:
        for finding in report["findings"]:
            print(f"  - {finding}")
    else:
        print("  No obvious spoofing indicators found.")

    print(
        "\nNote: DKIM cryptographic verification requires the original "
        "email body and a dedicated DKIM verifier. This script reports "
        "the sender-provided Authentication-Results header only."
    )


def read_multiline_headers():
    print("\nPaste raw email headers below.")
    print("Type END on a new line when finished.\n")

    lines = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines)


def main():
    print("Email Header Analyser and Spoofing Detector")
    print("=" * 72)

    raw_headers = read_multiline_headers()

    if not raw_headers.strip():
        print("Error: no headers were entered.")
        return

    try:
        report = analyse_headers(raw_headers)
        print_report(report)

    except KeyboardInterrupt:
        print("\nAnalysis cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()