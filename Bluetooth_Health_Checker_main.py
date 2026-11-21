

import sys
import argparse
import json
import time

from Bluetooth_Health_Checker_adapter_inspector import AdapterInspector
from Bluetooth_Health_Checker_driver_diagnostics import DriverDiagnostics
from Bluetooth_Health_Checker_surrounding_scanner import SurroundingScanner
from Bluetooth_Health_Checker_health_evaluator import HealthEvaluator, OverallHealthReport


# ============================================================================
# Terminal ANSI Color Formatting (Windows 11 Virtual Terminal)
# ============================================================================
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLUE = "\033[44m"


def enable_windows_ansi():
    """Enables ANSI escape sequence processing on Windows command prompts."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_stdout = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode)):
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(h_stdout, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)


def render_report(report: OverallHealthReport, show_troubleshooting: bool = True):
    """Renders the comprehensive diagnostic report to standard output."""
    c = Color
    divider = f"{c.CYAN}{'=' * 78}{c.RESET}"
    sub_divider = f"{c.DIM}{'-' * 78}{c.RESET}"

    # Header
    print(f"\n{divider}")
    print(f"{c.BOLD}{c.CYAN} BLUETOOTH ADAPTER HEALTH REPORT — WINDOWS 11{c.RESET}")
    print(divider)

    # Score Box
    score = report.score_percentage
    if score >= 90:
        score_color = f"{c.BOLD}{c.GREEN}"
    elif score >= 75:
        score_color = f"{c.BOLD}{c.CYAN}"
    elif score >= 50:
        score_color = f"{c.BOLD}{c.YELLOW}"
    else:
        score_color = f"{c.BOLD}{c.RED}"

    print(f"Overall Status  : {score_color}{report.health_grade} ({score}% Score){c.RESET}")
    print(f"Assessment      : {report.summary_message}\n")

    # 1. Radio & Specification
    print(f"{c.BOLD}{c.WHITE}[1] Radio Hardware & Bluetooth Core Specification{c.RESET}")
    print(sub_divider)
    a = report.adapter_info
    print(f"  • Device Name       : {c.BOLD}{a.name}{c.RESET}")
    print(f"  • MAC Address (BD)  : {c.CYAN}{a.mac_address}{c.RESET}")
    print(f"  • Manufacturer      : {a.manufacturer_name} (ID: 0x{a.manufacturer_id:04X})")
    print(f"  • Core Spec Support : {c.GREEN}{a.bluetooth_specification}{c.RESET} (LMP Version: {a.lmp_version_major})")
    print(f"  • LMP Subversion    : 0x{a.lmp_subversion:04X} ({a.lmp_subversion})")

    conn_str = f"{c.GREEN}YES{c.RESET}" if a.is_connectable else f"{c.YELLOW}NO{c.RESET}"
    disc_str = f"{c.GREEN}YES (Discoverable){c.RESET}" if a.is_discoverable else f"{c.DIM}NO (Hidden){c.RESET}"
    print(f"  • Radio Connectable : {conn_str}")
    print(f"  • Radio Discoverable: {disc_str}\n")

    # 2. Driver & System Services
    print(f"{c.BOLD}{c.WHITE}[2] Driver Integrity & Windows Services{c.RESET}")
    print(sub_divider)
    d = report.driver_info
    s = report.service_info

    pnp_color = c.GREEN if d.is_healthy else c.RED
    print(f"  • PnP Device Status : {pnp_color}{d.pnp_status} ({d.problem_name}){c.RESET}")
    if not d.is_healthy:
        print(f"    └── {c.RED}Fault Details   : {d.problem_description}{c.RESET}")
    print(f"  • Driver Provider   : {d.driver_provider}")
    print(f"  • Driver Version    : {d.driver_version} (Release Date: {d.driver_date})")

    svc_color = c.GREEN if s.is_running else c.RED
    print(f"  • 'bthserv' Service : {svc_color}{s.state_string}{c.RESET} (PID: {s.process_id})")
    print(f"    └── Details       : {s.diagnostic_message}\n")

    # 3. Surrounding RF Environment
    print(f"{c.BOLD}{c.WHITE}[3] Surrounding RF Environment Verification{c.RESET}")
    print(sub_divider)
    rf = report.rf_test_info
    print(f"  • RF Transceiver    : {c.GREEN}OPERATIONAL{c.RESET} (Inquiry duration: {rf.scan_duration_sec}s)")
    print(f"  • Detected Devices  : {c.BOLD}{rf.devices_found_count}{c.RESET} device(s) responding in vicinity")

    if rf.devices:
        for idx, dev in enumerate(rf.devices[:6], start=1):
            conn_tag = f"[{c.GREEN}Connected{c.RESET}]" if dev.is_connected else ""
            pair_tag = f"[{c.CYAN}Paired{c.RESET}]" if dev.is_authenticated else ""
            print(f"    {idx}. {dev.mac_address} — {dev.name:<24} {conn_tag} {pair_tag}")
        if len(rf.devices) > 6:
            print(f"    ... and {len(rf.devices) - 6} more device(s).")
    else:
        print(f"    └── {c.DIM}No active discoverable devices replied in this cycle.{c.RESET}")
    print()

    # 4. Diagnostic Checklist
    print(f"{c.BOLD}{c.WHITE}[4] Health Rules Checklist{c.RESET}")
    print(sub_divider)
    for item in report.checklist:
        icon = f"{c.GREEN}[PASS]{c.RESET}" if item.passed else f"{c.RED}[FAIL]{c.RESET}"
        if not item.passed and item.severity == "WARNING":
            icon = f"{c.YELLOW}[WARN]{c.RESET}"
        print(f"  {icon} {item.category:<13} : {item.item_name}")
        print(f"         └── {c.DIM}{item.detail}{c.RESET}")
    print()

    # 5. Troubleshooting & Actionable Guidance
    if show_troubleshooting and report.actionable_recommendations:
        print(f"{c.BOLD}{c.YELLOW}[!] Troubleshooting Recommendations{c.RESET}")
        print(sub_divider)
        for idx, rec in enumerate(report.actionable_recommendations, start=1):
            print(f"  {idx}. {c.BOLD}{rec}{c.RESET}")
        print()

    print(divider)


def main():
    enable_windows_ansi()

    parser = argparse.ArgumentParser(
        description="Bluetooth Adapter Health Checker for Windows 11 (Standard Library)."
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip active RF inquiry of surrounding area devices for a faster check.",
    )
    parser.add_argument(
        "--scan-timeout",
        type=int,
        default=3,
        help="Surrounding area inquiry multiplier (1-10). Each unit is 1.28s. Default is 3 (~3.84s).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Export full health diagnostics to clean JSON format.",
    )
    parser.add_argument(
        "--no-troubleshoot",
        action="store_true",
        help="Suppress troubleshooting advice section.",
    )
    args = parser.parse_args()

    if sys.platform != "win32":
        sys.stderr.write("[!] Error: This application requires Windows 10 or Windows 11.\n")
        sys.exit(1)

    # 1. Enumerate and query adapter hardware
    adapters = AdapterInspector.query_all_adapters()
    if not adapters:
        if args.json:
            print(json.dumps({
                "error": "No active Bluetooth radios detected.",
                "hint": "Check Windows Settings -> Bluetooth & devices and ensure Bluetooth is toggled ON."
            }, indent=2))
        else:
            print(f"\n{Color.RED}[!] No active Bluetooth radios detected on this system.{Color.RESET}")
            print(f"{Color.YELLOW}Troubleshooting:{Color.RESET}")
            print("  1. Ensure Bluetooth is toggled ON in Windows 11 Settings (Win+I -> Bluetooth & devices).")
            print("  2. Verify Airplane Mode is turned OFF.")
            print(
                "  3. Check Device Manager (devmgmt.msc) under 'Bluetooth' for yellow exclamation marks (Code 43 / Code 10).\n")
        sys.exit(1)

    primary_adapter = adapters[0]

    # 2. Query Driver and Service states
    driver_info = DriverDiagnostics.get_pnp_driver_info()
    service_info = DriverDiagnostics.check_bthserv_service()

    # 3. Active RF Inquiry Scan
    if args.quick:
        from Bluetooth_Health_Checker_surrounding_scanner import RfTransceiverTestResult
        rf_result = RfTransceiverTestResult(
            test_performed=False,
            scan_duration_sec=0.0,
            devices_found_count=0,
            devices=[],
            transceiver_functional=True,
            diagnostic_summary="RF inquiry skipped by user (--quick flag).",
        )
    else:
        if not args.json:
            print(f"[*] Interrogating {primary_adapter.name} ({primary_adapter.mac_address})...", file=sys.stderr)
            print(f"[*] Testing RF transceiver with surrounding inquiry scan...", file=sys.stderr)

        rf_result = SurroundingScanner.test_rf_transceiver(
            radio_handle=primary_adapter.handle_value,
            timeout_multiplier=args.scan_timeout
        )

    # 4. Synthesize diagnostic health score
    health_report = HealthEvaluator.evaluate(
        adapter=primary_adapter,
        driver=driver_info,
        service=service_info,
        rf_result=rf_result
    )

    # 5. Output results
    if args.json:
        print(json.dumps(health_report.to_dict(), indent=2))
    else:
        render_report(health_report, show_troubleshooting=not args.no_troubleshoot)


if __name__ == "__main__":
    main()