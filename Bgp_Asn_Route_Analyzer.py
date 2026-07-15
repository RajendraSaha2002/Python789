import ipaddress
import json
import socket
import urllib.parse
import urllib.request


class RouteAnalysisError(Exception):
    pass


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BGP-ASN-Route-Analyzer/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content = response.read().decode(
                "utf-8",
                errors="replace",
            )

        return json.loads(content)

    except Exception as error:
        raise RouteAnalysisError(
            f"API request failed: {error}"
        ) from error


def ripe_stat(endpoint, resource):
    encoded_resource = urllib.parse.quote(resource)

    url = (
        f"https://stat.ripe.net/data/{endpoint}/data.json"
        f"?resource={encoded_resource}"
    )

    response = fetch_json(url)

    if response.get("status") != "ok":
        raise RouteAnalysisError(
            f"RIPEstat returned an error for {endpoint}."
        )

    return response.get("data", {})


def normalise_input(value):
    value = value.strip()

    if not value:
        raise ValueError("Enter an IP address, ASN, or domain.")

    if value.upper().startswith("AS"):
        asn_text = value[2:]

        if not asn_text.isdigit():
            raise ValueError("Invalid ASN.")

        return "asn", f"AS{int(asn_text)}"

    try:
        address = ipaddress.ip_address(value)
        return "ip", str(address)
    except ValueError:
        pass

    try:
        addresses = socket.getaddrinfo(
            value,
            None,
            type=socket.SOCK_STREAM,
        )

        ip_address = addresses[0][4][0]
        return "domain", {
            "domain": value.lower(),
            "ip": ip_address,
        }

    except socket.gaierror as error:
        raise ValueError(
            f"Could not resolve domain: {error}"
        ) from error


def get_ip_network_info(ip_address):
    return ripe_stat("network-info", ip_address)


def get_prefix_overview(resource):
    return ripe_stat("prefix-overview", resource)


def get_as_overview(asn):
    return ripe_stat("as-overview", asn)


def get_announced_prefixes(asn):
    return ripe_stat("announced-prefixes", asn)


def extract_asn(network_info):
    asns = network_info.get("asns", [])

    if not asns:
        return ""

    return f"AS{asns[0]}"


def get_organisation_name(as_overview):
    holder = as_overview.get("holder", "")

    if holder:
        return holder

    return "Unknown"


def check_anomalies(
    target,
    network_info,
    prefix_overview,
    as_overview,
):
    findings = []

    asns = network_info.get("asns", [])
    prefix = prefix_overview.get("resource", "")
    announced = prefix_overview.get("announced", False)
    holder = get_organisation_name(as_overview)

    if not asns:
        findings.append(
            "No originating ASN was returned for this resource."
        )

    if not announced:
        findings.append(
            "Prefix is not currently marked as announced by RIPEstat."
        )

    if len(asns) > 1:
        findings.append(
            "Multiple origin ASNs were returned; review possible "
            "multi-origin routing."
        )

    if not prefix:
        findings.append(
            "No BGP prefix overview was returned."
        )

    if holder.lower() in ("", "unknown", "not available"):
        findings.append(
            "ASN organisation/holder information is unavailable."
        )

    if not findings:
        findings.append(
            "No obvious routing anomalies were identified from "
            "the available route context."
        )

    return findings


def build_report(target_type, target_value):
    domain = ""
    ip_address = ""
    asn = ""

    if target_type == "domain":
        domain = target_value["domain"]
        ip_address = target_value["ip"]

    elif target_type == "ip":
        ip_address = target_value

    elif target_type == "asn":
        asn = target_value

    network_info = {}
    prefix_overview = {}
    as_overview = {}
    announced_prefixes = {}

    if ip_address:
        network_info = get_ip_network_info(ip_address)
        asn = extract_asn(network_info)

        try:
            prefix_overview = get_prefix_overview(ip_address)
        except RouteAnalysisError:
            prefix_overview = {}

    if asn:
        try:
            as_overview = get_as_overview(asn)
        except RouteAnalysisError:
            as_overview = {}

        try:
            announced_prefixes = get_announced_prefixes(asn)
        except RouteAnalysisError:
            announced_prefixes = {}

    findings = check_anomalies(
        ip_address or asn,
        network_info,
        prefix_overview,
        as_overview,
    )

    prefixes = announced_prefixes.get("prefixes", [])

    return {
        "input_type": target_type,
        "domain": domain,
        "resolved_ip": ip_address,
        "origin_asn": asn or "Unknown",
        "organisation": get_organisation_name(as_overview),
        "network_info": network_info,
        "prefix_overview": prefix_overview,
        "announced_prefix_count": len(prefixes),
        "announced_prefixes_preview": prefixes[:25],
        "findings": findings,
        "limitations": [
            "This is passive OSINT analysis only.",
            "BGP paths differ by collector and network location.",
            "A routing anomaly alert requires manual verification.",
        ],
    }


def print_report(report):
    print("\n" + "=" * 72)
    print("BGP / ASN ROUTE ANALYSIS REPORT")
    print("=" * 72)

    print(f"Input type: {report['input_type']}")

    if report["domain"]:
        print(f"Domain: {report['domain']}")

    if report["resolved_ip"]:
        print(f"Resolved IP: {report['resolved_ip']}")

    print(f"Origin ASN: {report['origin_asn']}")
    print(f"Organisation: {report['organisation']}")
    print(f"Announced prefix count: {report['announced_prefix_count']}")

    network_info = report["network_info"]

    if network_info:
        print("\nNetwork information:")

        for key in ("prefix", "type", "resource"):
            if key in network_info:
                print(f"  {key.title()}: {network_info[key]}")

        asns = network_info.get("asns", [])

        if asns:
            print(
                "  Origin ASNs: "
                + ", ".join(f"AS{asn}" for asn in asns)
            )

    prefix_overview = report["prefix_overview"]

    if prefix_overview:
        print("\nPrefix overview:")

        for key in (
            "resource",
            "announced",
            "related_prefixes",
            "asns",
        ):
            if key in prefix_overview:
                print(f"  {key}: {prefix_overview[key]}")

    print("\nAnnounced prefix preview:")

    if report["announced_prefixes_preview"]:
        for prefix in report["announced_prefixes_preview"]:
            if isinstance(prefix, dict):
                print(f"  - {prefix.get('prefix', prefix)}")
            else:
                print(f"  - {prefix}")
    else:
        print("  No prefixes returned.")

    print("\nRouting findings:")

    for finding in report["findings"]:
        print(f"  - {finding}")

    print("\nLimitations:")

    for limitation in report["limitations"]:
        print(f"  - {limitation}")


def main():
    print("Autonomous System (BGP/ASN) Route Analyser")
    print("Enter a domain, IP address, or ASN.")
    print("Examples: example.com, 8.8.8.8, AS15169\n")

    user_input = input("Target: ").strip()

    try:
        target_type, target_value = normalise_input(user_input)

        print("\nQuerying public routing information...")
        report = build_report(target_type, target_value)

        print_report(report)

        save_report = input("\nSave JSON report? (y/n): ").strip().lower()

        if save_report == "y":
            output_file = "bgp_route_analysis_report.json"

            with open(output_file, "w", encoding="utf-8") as file_handle:
                json.dump(report, file_handle, indent=2)

            print(f"Report saved: {output_file}")

    except ValueError as error:
        print(f"Input error: {error}")

    except RouteAnalysisError as error:
        print(f"Lookup error: {error}")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()