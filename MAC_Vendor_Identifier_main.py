

import sys
import argparse
import json
from typing import List
from MAC_Vendor_Identifier_vendor_lookup import VendorLookupEngine, MacAnalysisReport
from MAC_Vendor_Identifier_mac_analyzer import BatchMacProcessor, WindowsNetworkInspector
from MAC_Vendor_Identifier_oui_database import (OuiDatabase)


class ConsoleColor:
    """ANSI terminal styling codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    GRAY = "\033[90m"


def print_single_report(r: MacAnalysisReport) -> None:
    """Prints a detailed, colorized report for a single MAC address."""
    cc = ConsoleColor
    border = "=" * 76

    print(f"\n{cc.BOLD}{cc.CYAN}{border}{cc.RESET}")
    print(f" MAC Address Report : {cc.BOLD}{r.canonical_mac}{cc.RESET}")
    print(f"{cc.BOLD}{cc.CYAN}{border}{cc.RESET}")

    # Section 1: Vendor Information
    if r.is_randomized_private:
        status_color = cc.YELLOW
    elif r.vendor_country == "Unknown":
        status_color = cc.RED
    else:
        status_color = cc.GREEN

    print(f"{cc.BOLD}Manufacturer      :{cc.RESET} {status_color}{r.vendor_name}{cc.RESET}")
    print(f"{cc.BOLD}Country of Origin :{cc.RESET} {r.vendor_country}")
    print(f"{cc.BOLD}Device Category   :{cc.RESET} {r.vendor_category}")
    if r.vendor_notes:
        print(f"{cc.BOLD}Hardware Context  :{cc.RESET} {r.vendor_notes}")

    print(f"\n{cc.BOLD}{cc.MAGENTA}--- IEEE 802 Bitwise Architecture ---{cc.RESET}")
    print(f"OUI Hex (First 3B): {r.oui_string}")
    print(f"Byte 0 Bit Layout : {r.first_byte_binary}")
    print(f"Transmission Mode : {r.transmission_scope}")
    print(f"Admin Scope       : {r.administration_scope}")

    print(f"\n{cc.BOLD}{cc.MAGENTA}--- Privacy & Randomization Diagnostics ---{cc.RESET}")
    if r.is_randomized_private:
        print(f"Is Randomized     : {cc.BOLD}{cc.YELLOW}YES (Locally Administered Private Address){cc.RESET}")
    else:
        print(f"Is Randomized     : {cc.GREEN}NO (Globally Unique IEEE Hardware Address){cc.RESET}")
    print(f"Diagnostic Note   : {r.randomization_reason}")
    print(f"BLE Classification: {r.ble_classification}")

    print(f"\n{cc.BOLD}{cc.MAGENTA}--- Alternate Representations ---{cc.RESET}")
    print(f"Cisco Format      : {r.cisco_mac}")
    print(f"Raw Hex Stream    : {r.raw_hex}")
    print(f"{cc.BOLD}{cc.CYAN}{border}{cc.RESET}\n")


def print_table(reports: List[MacAnalysisReport]) -> None:
    """Renders a collection of MAC address reports as an aligned terminal table."""
    if not reports:
        print("No MAC addresses to display.")
        return

    headers = ["MAC Address", "Vendor / Manufacturer", "Scope", "Randomized?", "OUI"]
    widths = [19, 28, 14, 13, 10]

    header_line = " ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
    separator = " ".join("-" * w for w in widths)

    print(f"\n{ConsoleColor.BOLD}{header_line}{ConsoleColor.RESET}")
    print(separator)

    for r in reports:
        mac_col = f"{r.canonical_mac:<19}"
        vend_clean = (r.vendor_name[:25] + "...") if len(r.vendor_name) > 28 else r.vendor_name
        scope_clean = "Universal" if "Universally" in r.administration_scope else "Local (LAA)"

        if r.is_randomized_private:
            rand_col = f"{ConsoleColor.YELLOW}YES (Private){ConsoleColor.RESET}"
        else:
            rand_col = f"{ConsoleColor.GREEN}NO (UAA)    {ConsoleColor.RESET}"

        row_str = (
            f"{mac_col} "
            f"{vend_clean:<28} "
            f"{scope_clean:<14} "
            f"{rand_col} "
            f"{r.oui_string:<10}"
        )
        print(row_str)
    print()


def interactive_repl() -> None:
    """Launches an interactive prompt for continuous MAC address queries."""
    print(f"{ConsoleColor.BOLD}=== MAC Address Vendor Identifier (Interactive REPL) ==={ConsoleColor.RESET}")
    print("Type any MAC address (e.g. '00:17:F2:12:34:56' or 'f0-18-98-aa-bb-cc').")
    print("Type 'exit' or 'quit' to terminate.\n")

    while True:
        try:
            line = input(f"{ConsoleColor.CYAN}MAC > {ConsoleColor.RESET}").strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "q"):
                break
            report = VendorLookupEngine.analyze(line)
            print_single_report(report)
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as ex:
            print(f"{ConsoleColor.RED}[Error] {ex}{ConsoleColor.RESET}\n")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline MAC Address Vendor Identifier and Privacy Analyzer for Windows 11."
    )
    parser.add_argument(
        "-m", "--mac",
        type=str,
        help="Analyze a single MAC address string (e.g. '00:17:F2:01:02:03').",
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Read and parse all MAC addresses found within a text/log file.",
    )
    parser.add_argument(
        "--arp",
        action="store_true",
        help="Inspect Windows 11 local ARP cache ('arp -a') and identify LAN vendors.",
    )
    parser.add_argument(
        "--adapters",
        action="store_true",
        help="Inspect local Windows 11 physical network adapters ('getmac').",
    )
    parser.add_argument(
        "-s", "--search",
        type=str,
        help="Search local database for all OUIs assigned to a vendor (e.g. 'Apple' or 'Intel').",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch the interactive REPL shell.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Format output as JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    # 1. Search Database by Vendor Name
    if args.search:
        matches = OuiDatabase.search_by_vendor(args.search)
        if args.json:
            out = [{"oui": m[0], "vendor": m[1].company_name, "notes": m[1].notes} for m in matches]
            print(json.dumps(out, indent=2))
        else:
            print(f"\nMatches for '{args.search}': {len(matches)} found.")
            for oui, record in matches:
                print(f"  {ConsoleColor.BOLD}{oui}{ConsoleColor.RESET} -> {record.company_name} ({record.notes})")
            print()
        return

    # 2. Windows 11 Local ARP Table Analysis
    if args.arp:
        arp_entries = WindowsNetworkInspector.get_arp_table()
        if not arp_entries:
            print("No entries returned from local ARP cache.")
            return

        reports = []
        for entry in arp_entries:
            try:
                rep = VendorLookupEngine.analyze(entry["mac"])
                reports.append(rep)
            except Exception:
                continue

        if args.json:
            combined = []
            for idx, rep in enumerate(reports):
                item = rep.to_dict()
                item["ip_address"] = arp_entries[idx]["ip"]
                item["arp_type"] = arp_entries[idx]["type"]
                combined.append(item)
            print(json.dumps(combined, indent=2))
        else:
            print(f"\n{ConsoleColor.BOLD}=== Discovered Windows 11 ARP Neighbors ({len(reports)}) ==={ConsoleColor.RESET}")
            print_table(reports)
        return

    # 3. Windows 11 Local Network Adapters
    if args.adapters:
        adapters = WindowsNetworkInspector.get_local_adapters()
        if not adapters:
            print("No physical adapters discovered via 'getmac'.")
            return

        reports = []
        for adp in adapters:
            try:
                rep = VendorLookupEngine.analyze(adp["mac"])
                reports.append(rep)
            except Exception:
                continue

        if args.json:
            combined = []
            for idx, rep in enumerate(reports):
                item = rep.to_dict()
                item["connection_name"] = adapters[idx]["connection"]
                item["adapter_name"] = adapters[idx]["adapter"]
                combined.append(item)
            print(json.dumps(combined, indent=2))
        else:
            print(f"\n{ConsoleColor.BOLD}=== Local Windows 11 Network Adapters ==={ConsoleColor.RESET}")
            print_table(reports)
        return

    # 4. File-Based Analysis
    if args.file:
        try:
            reports = BatchMacProcessor.analyze_file(args.file)
            if args.json:
                print(json.dumps([r.to_dict() for r in reports], indent=2))
            else:
                print(f"Extracted {len(reports)} valid MAC address(es) from '{args.file}':")
                print_table(reports)
        except Exception as ex:
            sys.stderr.write(f"File analysis error: {ex}\n")
            sys.exit(1)
        return

    # 5. Single MAC Lookup
    if args.mac:
        try:
            report = VendorLookupEngine.analyze(args.mac)
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print_single_report(report)
        except Exception as ex:
            sys.stderr.write(f"Error parsing MAC: {ex}\n")
            sys.exit(1)
        return

    # 6. Interactive Mode (Default if no args provided)
    if args.interactive or len(sys.argv) == 1:
        interactive_repl()
        return


if __name__ == "__main__":
    main()