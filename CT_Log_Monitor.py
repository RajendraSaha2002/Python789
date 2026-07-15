import json
import ssl
import socket
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


def parse_datetime(value):
    if not value:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]

    cleaned = value.replace("Z", "").strip()

    for date_format in formats:
        try:
            return datetime.strptime(
                cleaned,
                date_format,
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def normalise_domain(domain):
    domain = domain.strip().lower()

    if domain.startswith("https://"):
        domain = domain[8:]

    if domain.startswith("http://"):
        domain = domain[7:]

    domain = domain.split("/", 1)[0]
    domain = domain.split(":", 1)[0]

    if not domain or "." not in domain:
        raise ValueError("Enter a valid domain, such as example.com.")

    return domain


def fetch_crtsh_certificates(domain):
    query_domain = urllib.parse.quote(f"%.{domain}")

    url = (
        "https://crt.sh/?q="
        f"{query_domain}"
        "&output=json"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CT-Log-Monitor/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            response_data = response.read().decode(
                "utf-8",
                errors="replace",
            )

        return json.loads(response_data)

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "crt.sh returned an unexpected response. "
            "Try again later."
        ) from error

    except Exception as error:
        raise RuntimeError(
            f"Could not query crt.sh: {error}"
        ) from error


def extract_sans(certificate):
    names = certificate.get("name_value", "")
    san_names = []

    for name in names.splitlines():
        name = name.strip().lower()

        if name and name not in san_names:
            san_names.append(name)

    common_name = certificate.get("common_name", "").strip().lower()

    if common_name and common_name not in san_names:
        san_names.append(common_name)

    return san_names


def deduplicate_certificates(certificates):
    unique_certificates = {}
    now = datetime.now(timezone.utc)

    for certificate in certificates:
        serial = certificate.get("serial_number", "")
        issuer = certificate.get("issuer_name", "")
        common_name = certificate.get("common_name", "")
        not_before = certificate.get("not_before", "")

        key = (
            serial,
            issuer,
            common_name,
            not_before,
        )

        entry_timestamp = parse_datetime(
            certificate.get("entry_timestamp", "")
        )

        if key not in unique_certificates:
            unique_certificates[key] = certificate
            continue

        previous_entry = parse_datetime(
            unique_certificates[key].get(
                "entry_timestamp",
                "",
            )
        )

        if (
            entry_timestamp
            and (
                previous_entry is None
                or entry_timestamp > previous_entry
            )
        ):
            unique_certificates[key] = certificate

    processed = []

    for certificate in unique_certificates.values():
        entry_time = parse_datetime(
            certificate.get("entry_timestamp", "")
        )

        not_before = parse_datetime(
            certificate.get("not_before", "")
        )

        not_after = parse_datetime(
            certificate.get("not_after", "")
        )

        sans = extract_sans(certificate)

        processed.append(
            {
                "certificate_id": certificate.get("id", ""),
                "issuer": certificate.get(
                    "issuer_name",
                    "Unknown",
                ),
                "common_name": certificate.get(
                    "common_name",
                    "Unknown",
                ),
                "serial_number": certificate.get(
                    "serial_number",
                    "Unknown",
                ),
                "entry_timestamp": (
                    entry_time.isoformat()
                    if entry_time
                    else certificate.get("entry_timestamp", "Unknown")
                ),
                "not_before": (
                    not_before.isoformat()
                    if not_before
                    else certificate.get("not_before", "Unknown")
                ),
                "not_after": (
                    not_after.isoformat()
                    if not_after
                    else certificate.get("not_after", "Unknown")
                ),
                "san_names": sans,
                "wildcard_names": [
                    san
                    for san in sans
                    if san.startswith("*.")
                ],
                "issued_last_24_hours": bool(
                    entry_time
                    and entry_time >= now - timedelta(hours=24)
                ),
            }
        )

    processed.sort(
        key=lambda item: item["entry_timestamp"],
        reverse=True,
    )

    return processed


def check_tls_certificate(domain):
    context = ssl.create_default_context()

    try:
        with socket.create_connection(
            (domain, 443),
            timeout=10,
        ) as tcp_socket:

            with context.wrap_socket(
                tcp_socket,
                server_hostname=domain,
            ) as tls_socket:

                certificate = tls_socket.getpeercert()
                cipher = tls_socket.cipher()

                return {
                    "status": "VALID",
                    "tls_version": tls_socket.version(),
                    "cipher": cipher[0] if cipher else "Unknown",
                    "subject": certificate.get("subject", []),
                    "issuer": certificate.get("issuer", []),
                    "not_after": certificate.get(
                        "notAfter",
                        "Unknown",
                    ),
                    "ocsp_status": (
                        "Not checked: Python standard ssl does not "
                        "implement complete OCSP request validation."
                    ),
                }

    except ssl.SSLCertVerificationError as error:
        return {
            "status": "INVALID",
            "error": f"Certificate validation failed: {error}",
            "ocsp_status": "Not checked",
        }

    except Exception as error:
        return {
            "status": "ERROR",
            "error": str(error),
            "ocsp_status": "Not checked",
        }


def analyse_certificates(domain, certificates, expected_issuers):
    findings = []

    wildcard_certificates = []
    recent_certificates = []
    unexpected_issuer_certificates = []

    expected_issuers = [
        issuer.lower().strip()
        for issuer in expected_issuers
        if issuer.strip()
    ]

    for certificate in certificates:
        if certificate["wildcard_names"]:
            wildcard_certificates.append(certificate)

        if certificate["issued_last_24_hours"]:
            recent_certificates.append(certificate)

        issuer_lower = certificate["issuer"].lower()

        if expected_issuers and not any(
            allowed_issuer in issuer_lower
            for allowed_issuer in expected_issuers
        ):
            unexpected_issuer_certificates.append(certificate)

    if recent_certificates:
        findings.append(
            f"{len(recent_certificates)} certificate(s) appeared "
            "in CT logs during the last 24 hours."
        )

    if wildcard_certificates:
        findings.append(
            f"{len(wildcard_certificates)} certificate(s) contain "
            "wildcard SAN entries."
        )

    if unexpected_issuer_certificates:
        findings.append(
            f"{len(unexpected_issuer_certificates)} certificate(s) "
            "were issued by an unexpected CA."
        )

    if not findings:
        findings.append(
            "No selected CT log risk indicators were detected."
        )

    return {
        "domain": domain,
        "certificate_count": len(certificates),
        "wildcard_certificates": wildcard_certificates,
        "recent_certificates": recent_certificates,
        "unexpected_issuer_certificates": (
            unexpected_issuer_certificates
        ),
        "findings": findings,
    }


def print_report(report):
    print("\n" + "=" * 72)
    print("CERTIFICATE TRANSPARENCY LOG REPORT")
    print("=" * 72)
    print(f"Domain: {report['domain']}")
    print(
        f"Unique certificates found: "
        f"{report['certificate_count']}"
    )

    print("\nFindings:")

    for finding in report["findings"]:
        print(f"  - {finding}")

    print("\nRecently issued certificates (last 24 hours):")

    if report["recent_certificates"]:
        for certificate in report["recent_certificates"][:10]:
            print(
                f"  CN: {certificate['common_name']} | "
                f"Issuer: {certificate['issuer']}"
            )
            print(
                f"    Logged: {certificate['entry_timestamp']}"
            )
    else:
        print("  None found.")

    print("\nWildcard certificates:")

    if report["wildcard_certificates"]:
        for certificate in report["wildcard_certificates"][:10]:
            print(
                f"  CN: {certificate['common_name']} | "
                f"Wildcards: {', '.join(certificate['wildcard_names'])}"
            )
    else:
        print("  None found.")

    print("\nUnexpected issuer certificates:")

    if report["unexpected_issuer_certificates"]:
        for certificate in report[
            "unexpected_issuer_certificates"
        ][:10]:
            print(
                f"  CN: {certificate['common_name']} | "
                f"Issuer: {certificate['issuer']}"
            )
    else:
        print("  None found.")


def print_tls_report(tls_report):
    print("\n" + "=" * 72)
    print("LIVE TLS CERTIFICATE CHECK")
    print("=" * 72)
    print(f"Status: {tls_report['status']}")

    if tls_report["status"] == "VALID":
        print(f"TLS version: {tls_report['tls_version']}")
        print(f"Cipher: {tls_report['cipher']}")
        print(f"Valid until: {tls_report['not_after']}")
        print(f"OCSP: {tls_report['ocsp_status']}")
    else:
        print(f"Error: {tls_report.get('error', 'Unknown error')}")


def main():
    print("SSL/TLS Certificate Transparency Log Monitor")
    print("=" * 72)

    domain_input = input(
        "Domain to monitor (example.com): "
    ).strip()

    expected_input = input(
        "Expected CA names, comma-separated "
        "(optional, e.g. Let's Encrypt,DigiCert): "
    ).strip()

    try:
        domain = normalise_domain(domain_input)

        expected_issuers = [
            item.strip()
            for item in expected_input.split(",")
            if item.strip()
        ]

        print("\nQuerying Certificate Transparency logs...")
        raw_certificates = fetch_crtsh_certificates(domain)

        certificates = deduplicate_certificates(raw_certificates)

        report = analyse_certificates(
            domain,
            certificates,
            expected_issuers,
        )

        print_report(report)

        print("\nChecking current TLS certificate...")
        tls_report = check_tls_certificate(domain)
        print_tls_report(tls_report)

        save = input("\nSave JSON report? (y/n): ").strip().lower()

        if save == "y":
            output = {
                "generated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "ct_report": report,
                "tls_report": tls_report,
            }

            output_path = "certificate_transparency_report.json"

            with open(output_path, "w", encoding="utf-8") as file_handle:
                json.dump(output, file_handle, indent=2)

            print(f"\nSaved report: {output_path}")

    except ValueError as error:
        print(f"Input error: {error}")

    except RuntimeError as error:
        print(f"Query error: {error}")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()