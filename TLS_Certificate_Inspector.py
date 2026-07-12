import json
import socket
import ssl
from datetime import datetime, timezone


def parse_host_input(value):
    value = value.strip()

    if not value:
        raise ValueError("Host cannot be empty.")

    if value.startswith("https://"):
        value = value[8:]

    if value.startswith("http://"):
        value = value[7:]

    value = value.split("/", 1)[0]

    if ":" in value:
        host, port_text = value.rsplit(":", 1)

        try:
            port = int(port_text)
        except ValueError:
            raise ValueError("Port must be a valid number.")

        if not 1 <= port <= 65535:
            raise ValueError("Port must be between 1 and 65535.")

        return host, port

    return value, 443


def format_certificate_name(name_parts):
    if not name_parts:
        return "Not available"

    values = []

    for group in name_parts:
        for key, value in group:
            values.append(f"{key}={value}")

    return ", ".join(values)


def get_san_names(certificate):
    san_entries = certificate.get("subjectAltName", [])
    return [
        f"{entry_type}: {entry_value}"
        for entry_type, entry_value in san_entries
    ]


def get_certificate_dates(certificate):
    not_before_text = certificate.get("notBefore", "")
    not_after_text = certificate.get("notAfter", "")

    not_before = None
    not_after = None

    try:
        not_before = datetime.strptime(
            not_before_text,
            "%b %d %H:%M:%S %Y %Z",
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    try:
        not_after = datetime.strptime(
            not_after_text,
            "%b %d %H:%M:%S %Y %Z",
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    return not_before, not_after


def calculate_certificate_health(not_before, not_after):
    now = datetime.now(timezone.utc)
    warnings = []

    if not_before is None or not_after is None:
        warnings.append("Certificate validity dates could not be parsed.")

        return {
            "status": "UNKNOWN",
            "days_remaining": None,
            "warnings": warnings,
        }

    days_remaining = (not_after - now).total_seconds() / 86400

    if now < not_before:
        warnings.append("Certificate is not valid yet.")
        status = "CRITICAL"

    elif now > not_after:
        warnings.append("Certificate has expired.")
        status = "CRITICAL"

    elif days_remaining < 14:
        warnings.append("Certificate expires in less than 14 days.")
        status = "WARNING"

    elif days_remaining < 30:
        warnings.append("Certificate expires in less than 30 days.")
        status = "NOTICE"

    else:
        status = "HEALTHY"

    return {
        "status": status,
        "days_remaining": round(days_remaining, 2),
        "warnings": warnings,
    }


def send_https_head_request(ssl_socket, host):
    request = (
        f"HEAD / HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"User-Agent: TLS-Certificate-Inspector/1.0\r\n"
        f"Connection: close\r\n\r\n"
    ).encode("utf-8")

    ssl_socket.sendall(request)

    response = bytearray()

    while len(response) < 16384:
        try:
            chunk = ssl_socket.recv(4096)
        except socket.timeout:
            break

        if not chunk:
            break

        response.extend(chunk)

        if b"\r\n\r\n" in response:
            break

    return response.decode("iso-8859-1", errors="replace")


def parse_http_headers(http_response):
    if not http_response:
        return {
            "status_line": "",
            "headers": {},
        }

    lines = http_response.split("\r\n")
    status_line = lines[0] if lines else ""
    headers = {}

    for line in lines[1:]:
        if not line.strip():
            break

        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

    return {
        "status_line": status_line,
        "headers": headers,
    }


def inspect_tls_host(host, port):
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    report = {
        "host": host,
        "port": port,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "connection": {},
        "certificate": {},
        "security_headers": {},
        "health": {},
        "warnings": [],
    }

    try:
        with socket.create_connection(
            (host, port),
            timeout=10,
        ) as tcp_socket:

            with context.wrap_socket(
                tcp_socket,
                server_hostname=host,
            ) as tls_socket:

                tls_socket.settimeout(5)

                certificate = tls_socket.getpeercert()
                certificate_der = tls_socket.getpeercert(binary_form=True)

                cipher = tls_socket.cipher()
                tls_version = tls_socket.version()

                report["connection"] = {
                    "tls_version": tls_version,
                    "cipher_name": cipher[0] if cipher else "Unknown",
                    "cipher_protocol": cipher[1] if cipher else "Unknown",
                    "cipher_bits": cipher[2] if cipher else 0,
                    "chain_validation": "VALIDATED against system CA bundle",
                }

                not_before, not_after = get_certificate_dates(
                    certificate
                )

                report["certificate"] = {
                    "subject": format_certificate_name(
                        certificate.get("subject", [])
                    ),
                    "issuer": format_certificate_name(
                        certificate.get("issuer", [])
                    ),
                    "serial_number": certificate.get(
                        "serialNumber",
                        "Not available",
                    ),
                    "version": certificate.get(
                        "version",
                        "Not available",
                    ),
                    "not_before": (
                        not_before.isoformat()
                        if not_before
                        else certificate.get("notBefore", "Not available")
                    ),
                    "not_after": (
                        not_after.isoformat()
                        if not_after
                        else certificate.get("notAfter", "Not available")
                    ),
                    "subject_alternative_names": get_san_names(
                        certificate
                    ),
                    "leaf_certificate_der_size": len(certificate_der),
                    "chain_note": (
                        "The TLS handshake successfully validated the "
                        "server chain using the system CA bundle."
                    ),
                }

                health = calculate_certificate_health(
                    not_before,
                    not_after,
                )

                report["health"] = health
                report["warnings"].extend(health["warnings"])

                try:
                    response = send_https_head_request(
                        tls_socket,
                        host,
                    )

                    parsed_headers = parse_http_headers(response)
                    headers = parsed_headers["headers"]
                    hsts_value = headers.get(
                        "strict-transport-security",
                        "",
                    )

                    report["security_headers"] = {
                        "http_status": parsed_headers["status_line"],
                        "hsts_present": bool(hsts_value),
                        "hsts_value": hsts_value or "Not present",
                    }

                    if not hsts_value:
                        report["warnings"].append(
                            "HSTS header was not present in the HTTPS response."
                        )

                except (socket.timeout, OSError):
                    report["security_headers"] = {
                        "http_status": "Could not retrieve HTTP headers",
                        "hsts_present": False,
                        "hsts_value": "Not checked",
                    }

    except ssl.SSLCertVerificationError as error:
        report["connection"] = {
            "chain_validation": "FAILED",
        }

        report["health"] = {
            "status": "CRITICAL",
            "days_remaining": None,
        }

        report["warnings"].append(
            f"Certificate chain validation failed: {error}"
        )

    except ssl.SSLError as error:
        report["connection"] = {
            "chain_validation": "TLS ERROR",
        }

        report["health"] = {
            "status": "CRITICAL",
            "days_remaining": None,
        }

        report["warnings"].append(f"TLS error: {error}")

    except socket.gaierror:
        report["connection"] = {
            "chain_validation": "NOT CHECKED",
        }

        report["health"] = {
            "status": "CRITICAL",
            "days_remaining": None,
        }

        report["warnings"].append("Host name could not be resolved.")

    except socket.timeout:
        report["connection"] = {
            "chain_validation": "NOT CHECKED",
        }

        report["health"] = {
            "status": "CRITICAL",
            "days_remaining": None,
        }

        report["warnings"].append("Connection timed out.")

    except OSError as error:
        report["connection"] = {
            "chain_validation": "NOT CHECKED",
        }

        report["health"] = {
            "status": "CRITICAL",
            "days_remaining": None,
        }

        report["warnings"].append(f"Network error: {error}")

    return report


def print_report(report):
    print("\n" + "=" * 72)
    print("TLS CERTIFICATE HEALTH REPORT")
    print("=" * 72)
    print(f"Host: {report['host']}:{report['port']}")
    print(f"Checked: {report['checked_at_utc']}")

    connection = report["connection"]

    print("\nConnection")
    print("-" * 72)

    for key, value in connection.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    certificate = report["certificate"]

    if certificate:
        print("\nCertificate")
        print("-" * 72)
        print(f"Subject: {certificate.get('subject')}")
        print(f"Issuer: {certificate.get('issuer')}")
        print(f"Serial number: {certificate.get('serial_number')}")
        print(f"Valid from: {certificate.get('not_before')}")
        print(f"Valid until: {certificate.get('not_after')}")

        print("\nSubject Alternative Names:")

        for san in certificate.get(
            "subject_alternative_names",
            [],
        ):
            print(f"  - {san}")

    headers = report["security_headers"]

    if headers:
        print("\nHTTPS Security Headers")
        print("-" * 72)
        print(f"HTTP response: {headers.get('http_status')}")
        print(f"HSTS present: {headers.get('hsts_present')}")
        print(f"HSTS value: {headers.get('hsts_value')}")

    health = report["health"]

    print("\nHealth")
    print("-" * 72)
    print(f"Status: {health.get('status')}")

    if health.get("days_remaining") is not None:
        print(f"Days remaining: {health.get('days_remaining')}")

    print("\nWarnings")

    if report["warnings"]:
        for warning in report["warnings"]:
            print(f"  - {warning}")
    else:
        print("  No warnings found.")


def main():
    print("TLS Certificate Inspector and Chain Validator")
    print("Examples: example.com or example.com:443\n")

    value = input("Enter HTTPS host: ").strip()

    try:
        host, port = parse_host_input(value)
        report = inspect_tls_host(host, port)
        print_report(report)

        save = input("\nSave JSON report? (y/n): ").strip().lower()

        if save == "y":
            filename = "tls_certificate_health_report.json"

            with open(filename, "w", encoding="utf-8") as file_handle:
                json.dump(report, file_handle, indent=2)

            print(f"Report saved as: {filename}")

    except ValueError as error:
        print(f"Input error: {error}")

    except KeyboardInterrupt:
        print("\nCancelled by user.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()