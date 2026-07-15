import html
import json
import re
import urllib.parse


RECOMMENDED_DIRECTIVES = {
    "default-src",
    "script-src",
    "object-src",
    "base-uri",
    "frame-ancestors",
}


def parse_csp(csp_value):
    directives = {}

    for part in csp_value.split(";"):
        part = part.strip()

        if not part:
            continue

        values = part.split()

        if not values:
            continue

        directive_name = values[0].lower()
        directive_values = values[1:]

        directives[directive_name] = directive_values

    return directives


def analyse_csp(csp_value):
    directives = parse_csp(csp_value)
    findings = []
    score = 0

    missing = sorted(
        RECOMMENDED_DIRECTIVES - set(directives)
    )

    if missing:
        score += len(missing) * 5
        findings.append(
            "Missing recommended directives: "
            + ", ".join(missing)
        )

    script_sources = directives.get(
        "script-src",
        directives.get("default-src", []),
    )

    if not script_sources:
        score += 20
        findings.append(
            "No script-src or default-src directive is defined."
        )

    if "'unsafe-inline'" in script_sources:
        score += 25
        findings.append(
            "script-src permits 'unsafe-inline'."
        )

    if "'unsafe-eval'" in script_sources:
        score += 20
        findings.append(
            "script-src permits 'unsafe-eval'."
        )

    if "*" in script_sources:
        score += 25
        findings.append(
            "script-src allows every source using wildcard '*'."
        )

    if "data:" in script_sources:
        score += 10
        findings.append(
            "script-src permits data: URLs."
        )

    if "blob:" in script_sources:
        score += 8
        findings.append(
            "script-src permits blob: URLs."
        )

    object_sources = directives.get("object-src", [])

    if object_sources and "'none'" not in object_sources:
        score += 10
        findings.append(
            "object-src is not restricted to 'none'."
        )

    if not object_sources:
        score += 10
        findings.append(
            "object-src is missing; set object-src 'none'."
        )

    if "base-uri" not in directives:
        score += 8
        findings.append(
            "base-uri is missing."
        )

    if "frame-ancestors" not in directives:
        score += 8
        findings.append(
            "frame-ancestors is missing."
        )

    if "require-trusted-types-for" not in directives:
        findings.append(
            "Trusted Types are not required; consider them for modern apps."
        )

    score = min(score, 100)

    if score >= 60:
        rating = "HIGH RISK"
    elif score >= 30:
        rating = "MEDIUM RISK"
    else:
        rating = "LOW RISK"

    return {
        "original_csp": csp_value,
        "directives": directives,
        "score": score,
        "rating": rating,
        "findings": findings,
    }


def analyse_html_input(value):
    findings = []

    decoded = html.unescape(value)
    url_decoded = urllib.parse.unquote(decoded)

    if re.search(
        r"<\s*script\b",
        url_decoded,
        flags=re.IGNORECASE,
    ):
        findings.append("Script element pattern detected.")

    if re.search(
        r"\bon[a-z]+\s*=",
        url_decoded,
        flags=re.IGNORECASE,
    ):
        findings.append("Inline event-handler attribute pattern detected.")

    if re.search(
        r"javascript\s*:",
        url_decoded,
        flags=re.IGNORECASE,
    ):
        findings.append("Script-URL scheme pattern detected.")

    if re.search(
        r"<\s*(iframe|object|embed|svg|math)\b",
        url_decoded,
        flags=re.IGNORECASE,
    ):
        findings.append("Potentially active HTML element detected.")

    if "<" in url_decoded or ">" in url_decoded:
        findings.append(
            "HTML delimiter characters remain after decoding."
        )

    classification = (
        "REQUIRES SANITISATION"
        if findings
        else "NO OBVIOUS ACTIVE HTML PATTERN"
    )

    return {
        "input": value,
        "html_decoded": decoded,
        "url_decoded": url_decoded,
        "classification": classification,
        "findings": findings,
    }


def safe_sanitise_html(value):
    """
    Defensive demonstration sanitizer.
    For production, use a maintained server-side HTML sanitizer.
    """
    value = html.escape(value, quote=True)

    return value


def print_csp_report(report):
    print("\n" + "=" * 72)
    print("CONTENT SECURITY POLICY ANALYSIS REPORT")
    print("=" * 72)
    print(f"Risk score: {report['score']} / 100")
    print(f"Rating: {report['rating']}")

    print("\nParsed directives:")

    for directive, values in report["directives"].items():
        print(f"  {directive}: {' '.join(values)}")

    print("\nFindings:")

    if report["findings"]:
        for finding in report["findings"]:
            print(f"  - {finding}")
    else:
        print("  No obvious weaknesses found.")


def print_html_report(report):
    print("\n" + "=" * 72)
    print("HTML INPUT SAFETY ANALYSIS")
    print("=" * 72)
    print(f"Classification: {report['classification']}")

    print("\nFindings:")

    if report["findings"]:
        for finding in report["findings"]:
            print(f"  - {finding}")
    else:
        print("  No obvious dangerous pattern found.")

    print("\nSafely escaped output:")
    print(safe_sanitise_html(report["input"]))


def main():
    print("CSP Defensive Analyser and HTML Sanitisation Checker")
    print("=" * 72)
    print("1 - Analyse a Content-Security-Policy header")
    print("2 - Analyse HTML input safely")
    print("3 - Run both checks")

    choice = input("\nChoose an option (1-3): ").strip()

    output = {}

    try:
        if choice in ("1", "3"):
            csp = input("\nPaste CSP header value: ").strip()

            if not csp:
                print("Error: CSP value cannot be empty.")
                return

            output["csp_report"] = analyse_csp(csp)
            print_csp_report(output["csp_report"])

        if choice in ("2", "3"):
            html_input = input(
                "\nPaste HTML/text input to analyse: "
            )

            output["html_report"] = analyse_html_input(html_input)
            print_html_report(output["html_report"])

        if choice not in ("1", "2", "3"):
            print("Error: choose 1, 2, or 3.")
            return

        save_choice = input(
            "\nSave JSON report? (y/n): "
        ).strip().lower()

        if save_choice == "y":
            with open(
                "csp_defensive_analysis_report.json",
                "w",
                encoding="utf-8",
            ) as file_handle:
                json.dump(output, file_handle, indent=2)

            print("Saved: csp_defensive_analysis_report.json")

    except KeyboardInterrupt:
        print("\nAnalysis cancelled.")

    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()