import json
import re
import urllib.parse
from email import message_from_string
from email.header import decode_header


URGENT_WORDS = {
    "urgent", "immediately", "action required", "verify now",
    "account suspended", "limited time", "final warning",
    "act now", "within 24 hours", "unusual activity",
}

IMPERSONATION_WORDS = {
    "microsoft", "google", "apple", "paypal", "amazon",
    "netflix", "facebook", "instagram", "bank", "support",
    "security team", "it department",
}

SUSPICIOUS_TLDS = {
    ".zip", ".top", ".xyz", ".click", ".loan",
    ".country", ".gq", ".tk", ".work", ".link",
}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl",
    "is.gd", "cutt.ly", "rb.gy", "shorturl.at",
}

DANGEROUS_ATTACHMENTS = {
    ".exe", ".scr", ".bat", ".cmd", ".com", ".msi",
    ".js", ".vbs", ".ps1", ".jar", ".iso", ".img",
    ".zip", ".rar", ".7z", ".html", ".htm",
}


def decode_value(value):
    if not value:
        return ""

    output = []

    for part, charset in decode_header(value):
        if isinstance(part, bytes):
            try:
                output.append(
                    part.decode(charset or "utf-8", errors="replace")
                )
            except LookupError:
                output.append(
                    part.decode("utf-8", errors="replace")
                )
        else:
            output.append(part)

    return "".join(output)


def extract_domain(address):
    if not address or "@" not in address:
        return ""

    return address.rsplit("@", 1)[1].lower().strip()


def contains_ip_address_host(url):
    match = re.match(
        r"^[a-z]+://(\d{1,3}(?:\.\d{1,3}){3})(?:[:/]|$)",
        url.lower(),
    )

    return bool(match)


def has_homoglyph_characters(value):
    suspicious_ranges = [
        ("\u0400", "\u04ff"),  # Cyrillic
        ("\u0370", "\u03ff"),  # Greek
    ]

    for character in value:
        for start, end in suspicious_ranges:
            if start <= character <= end:
                return True

    return False


def extract_urls(text):
    return re.findall(
        r"https?://[^\s<>()\"']+",
        text,
        flags=re.IGNORECASE,
    )


def analyse_url(url):
    parsed = urllib.parse.urlparse(url)
    hostname = (parsed.hostname or "").lower()

    findings = []

    if parsed.scheme != "https":
        findings.append("URL does not use HTTPS.")

    if hostname in URL_SHORTENERS:
        findings.append("URL shortener detected.")

    if contains_ip_address_host(url):
        findings.append("IP address used instead of domain name.")

    if any(hostname.endswith(tld) for tld in SUSPICIOUS_TLDS):
        findings.append("Suspicious top-level domain detected.")

    if "@" in url:
        findings.append("At-sign found in URL; possible URL obfuscation.")

    if has_homoglyph_characters(hostname):
        findings.append("Possible Unicode homoglyph domain.")

    if len(hostname.split(".")) > 4:
        findings.append("Unusually deep subdomain structure.")

    return {
        "url": url,
        "hostname": hostname,
        "findings": findings,
    }


def attachment_risk(filename):
    filename = filename.lower().strip()

    for extension in DANGEROUS_ATTACHMENTS:
        if filename.endswith(extension):
            return extension

    return ""


def analyse_email(raw_email):
    message = message_from_string(raw_email)

    from_header = decode_value(message.get("From", ""))
    reply_to_header = decode_value(message.get("Reply-To", ""))
    subject = decode_value(message.get("Subject", ""))

    from_match = re.search(
        r"<([^>]+)>",
        from_header,
    )

    from_email = (
        from_match.group(1)
        if from_match
        else from_header
    )

    reply_to_match = re.search(
        r"<([^>]+)>",
        reply_to_header,
    )

    reply_to_email = (
        reply_to_match.group(1)
        if reply_to_match
        else reply_to_header
    )

    body_parts = []
    attachments = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            filename = part.get_filename()

            if filename:
                attachments.append(filename)

            if (
                content_type == "text/plain"
                and disposition != "attachment"
            ):
                payload = part.get_payload(decode=True)

                if payload:
                    body_parts.append(
                        payload.decode("utf-8", errors="replace")
                    )
    else:
        payload = message.get_payload(decode=True)

        if payload:
            body_parts.append(
                payload.decode("utf-8", errors="replace")
            )
        else:
            body_parts.append(str(message.get_payload()))

    body = "\n".join(body_parts)
    combined_text = f"{subject}\n{body}".lower()

    score = 0
    findings = []

    urgent_matches = [
        word
        for word in URGENT_WORDS
        if word in combined_text
    ]

    if urgent_matches:
        score += min(len(urgent_matches) * 6, 24)
        findings.append(
            "Urgency language: " + ", ".join(urgent_matches)
        )

    impersonation_matches = [
        word
        for word in IMPERSONATION_WORDS
        if word in combined_text
    ]

    if impersonation_matches:
        score += min(len(impersonation_matches) * 5, 20)
        findings.append(
            "Brand/organisation references: "
            + ", ".join(impersonation_matches)
        )

    from_domain = extract_domain(from_email)
    reply_to_domain = extract_domain(reply_to_email)

    if reply_to_domain and from_domain != reply_to_domain:
        score += 15
        findings.append(
            "From and Reply-To domains do not match."
        )

    if has_homoglyph_characters(from_header):
        score += 15
        findings.append(
            "Possible Unicode homoglyph characters in sender."
        )

    urls = extract_urls(body)
    url_results = []

    for url in urls:
        url_result = analyse_url(url)
        url_results.append(url_result)

        if url_result["findings"]:
            score += min(len(url_result["findings"]) * 8, 24)
            findings.append(
                f"Suspicious URL: {url_result['url']}"
            )

    dangerous_files = []

    for filename in attachments:
        extension = attachment_risk(filename)

        if extension:
            dangerous_files.append(filename)
            score += 20

    if dangerous_files:
        findings.append(
            "Risky attachment types: "
            + ", ".join(dangerous_files)
        )

    score = min(score, 100)

    if score >= 60:
        classification = "PHISHING LIKELY"
    elif score >= 30:
        classification = "SUSPICIOUS"
    else:
        classification = "CLEAN / LOW RISK"

    return {
        "from": from_header,
        "from_domain": from_domain,
        "reply_to": reply_to_header,
        "reply_to_domain": reply_to_domain,
        "subject": subject,
        "attachments": attachments,
        "url_analysis": url_results,
        "score": score,
        "classification": classification,
        "findings": findings,
    }


def print_report(report):
    print("\n" + "=" * 72)
    print("PHISHING EMAIL ANALYSIS REPORT")
    print("=" * 72)
    print(f"From: {report['from']}")
    print(f"Reply-To: {report['reply_to'] or 'Not present'}")
    print(f"Subject: {report['subject']}")
    print(f"Score: {report['score']} / 100")
    print(f"Classification: {report['classification']}")

    print("\nLinks:")

    if report["url_analysis"]:
        for item in report["url_analysis"]:
            print(f"  URL: {item['url']}")

            if item["findings"]:
                for finding in item["findings"]:
                    print(f"    - {finding}")
            else:
                print("    - No obvious URL indicator.")
    else:
        print("  No URLs found.")

    print("\nAttachments:")

    if report["attachments"]:
        for attachment in report["attachments"]:
            print(f"  - {attachment}")
    else:
        print("  No attachments found.")

    print("\nFindings:")

    if report["findings"]:
        for finding in report["findings"]:
            print(f"  - {finding}")
    else:
        print("  No major phishing indicators found.")


def read_email():
    print("\nPaste raw email text below.")
    print("Type END on a new line when finished.\n")

    lines = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines)


def main():
    print("Phishing Email Template Analyser and Scorer")
    print("Analysis only — no links are opened or emails sent.")

    raw_email = read_email()

    if not raw_email.strip():
        print("Error: no email text entered.")
        return

    try:
        report = analyse_email(raw_email)
        print_report(report)

        save_choice = input(
            "\nSave JSON report? (y/n): "
        ).strip().lower()

        if save_choice == "y":
            with open(
                "phishing_analysis_report.json",
                "w",
                encoding="utf-8",
            ) as file_handle:
                json.dump(report, file_handle, indent=2)

            print("Saved: phishing_analysis_report.json")

    except KeyboardInterrupt:
        print("\nAnalysis cancelled.")

    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()