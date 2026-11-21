

import sys
import argparse
import json
import time
from typing import List
from Classic_Bluetooth_win_constants import (
    DEFAULT_INQUIRY_TIMEOUT_MULTIPLIER,
    MIN_INQUIRY_TIMEOUT_MULTIPLIER,
    MAX_INQUIRY_TIMEOUT_MULTIPLIER,
)
from Classic_Bluetooth_device_discovery import BluetoothDiscoveryEngine, DiscoveredBluetoothDevice, RadioDetails


class ConsoleColor:
    """ANSI color codes for Windows 10/11 terminals."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    GRAY = "\033[90m"


def print_radios(radios: List[RadioDetails]) -> None:
    """Prints discovered local Bluetooth controllers."""
    print(f"{ConsoleColor.BOLD}{ConsoleColor.CYAN}--- Local Bluetooth Radios ---{ConsoleColor.RESET}")
    if not radios:
        print(f"{ConsoleColor.RED}No active Bluetooth radio controller detected on this system.{ConsoleColor.RESET}\n")
        return

    for idx, radio in enumerate(radios):
        print(f"[{idx}] {ConsoleColor.BOLD}{radio.name}{ConsoleColor.RESET}")
        print(f"    MAC Address   : {radio.address}")
        print(f"    Manufacturer  : {radio.manufacturer_name} (ID: {radio.manufacturer_id})")
        print(f"    Class of Dev  : {radio.class_of_device.summary_label} ({radio.class_of_device.hex_str})")
        print(f"    LMP Subversion: 0x{radio.lmp_subversion:04X}")
    print()


def render_table(devices: List[DiscoveredBluetoothDevice]) -> None:
    """Prints discovered devices in an aligned ASCII table."""
    if not devices:
        print(f"{ConsoleColor.YELLOW}No Bluetooth devices found matching the filter criteria.{ConsoleColor.RESET}")
        return

    headers = ["MAC Address", "Device Name", "Class / Category", "Status", "Last Seen"]
    col_widths = [19, 26, 32, 18, 20]

    header_line = " ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = " ".join("-" * w for w in col_widths)

    print(f"{ConsoleColor.BOLD}{header_line}{ConsoleColor.RESET}")
    print(separator)

    for dev in devices:
        # Determine status color
        if dev.is_connected:
            status_col = f"{ConsoleColor.GREEN}{dev.status_summary:<18}{ConsoleColor.RESET}"
        elif dev.is_authenticated:
            status_col = f"{ConsoleColor.CYAN}{dev.status_summary:<18}{ConsoleColor.RESET}"
        elif dev.is_remembered:
            status_col = f"{ConsoleColor.BLUE}{dev.status_summary:<18}{ConsoleColor.RESET}"
        else:
            status_col = f"{ConsoleColor.YELLOW}{dev.status_summary:<18}{ConsoleColor.RESET}"

        last_seen_str = dev.last_seen.strftime("%Y-%m-%d %H:%M:%S") if dev.last_seen else "Never"
        name_clean = (dev.name[:23] + "...") if len(dev.name) > 26 else dev.name
        cod_clean = (dev.class_of_device.summary_label[:29] + "...") if len(
            dev.class_of_device.summary_label) > 32 else dev.class_of_device.summary_label

        row_str = (
            f"{dev.mac_address:<19} "
            f"{name_clean:<26} "
            f"{cod_clean:<32} "
            f"{status_col} "
            f"{last_seen_str:<20}"
        )
        print(row_str)
    print()


def render_detailed(device: DiscoveredBluetoothDevice) -> None:
    """Prints an expanded, multi-line view of a single discovered device."""
    cc = ConsoleColor
    print(f"{cc.BOLD}{cc.MAGENTA}======================================================================{cc.RESET}")
    print(f"Device Name      : {cc.BOLD}{device.name}{cc.RESET}")
    print(f"MAC Address      : {cc.CYAN}{device.mac_address}{cc.RESET}")
    print(f"Primary Category : {device.class_of_device.summary_label}")
    print(f"Major Class      : {device.class_of_device.major_device_class_name}")
    print(f"Minor Class      : {device.class_of_device.minor_device_class_name}")
    print(f"Raw CoD Hex      : {device.class_of_device.hex_str}")

    services = ", ".join(device.class_of_device.services) if device.class_of_device.services else "None Reported"
    print(f"Services Offered : {services}")

    print(f"Authenticated    : {'Yes' if device.is_authenticated else 'No'}")
    print(f"Remembered       : {'Yes' if device.is_remembered else 'No'}")
    print(f"Connected        : {'Yes (Active Link)' if device.is_connected else 'No'}")
    print(f"Last Seen        : {device.last_seen if device.last_seen else 'Never'}")
    print(f"Last Used        : {device.last_used if device.last_used else 'Never'}")
    print(f"{cc.BOLD}{cc.MAGENTA}======================================================================{cc.RESET}\n")


def device_to_dict(dev: DiscoveredBluetoothDevice) -> dict:
    """Serializes a device dataclass to a JSON-ready dictionary."""
    return {
        "mac_address": dev.mac_address,
        "name": dev.name,
        "is_authenticated": dev.is_authenticated,
        "is_remembered": dev.is_remembered,
        "is_connected": dev.is_connected,
        "last_seen": dev.last_seen.isoformat() if dev.last_seen else None,
        "last_used": dev.last_used.isoformat() if dev.last_used else None,
        "class_of_device": dev.class_of_device.to_dict(),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Windows Classic Bluetooth Device Discovery Tool (Pure Ctypes)."
    )
    parser.add_argument(
        "--no-inquiry",
        action="store_true",
        help="Skip active RF inquiry (only display cached, paired, or remembered devices).",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=DEFAULT_INQUIRY_TIMEOUT_MULTIPLIER,
        help=f"Inquiry duration multiplier (1 to 48, each unit = 1.28s). Default: {DEFAULT_INQUIRY_TIMEOUT_MULTIPLIER} (~12.8s)",
    )
    parser.add_argument(
        "--connected-only",
        action="store_true",
        help="Filter results to currently connected devices.",
    )
    parser.add_argument(
        "--paired-only",
        action="store_true",
        help="Filter results to authenticated/paired devices.",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Display full technical breakdown for each device.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Export discovered devices in JSON format.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    if sys.platform != "win32":
        sys.stderr.write("[!] Error: This application requires Windows 7, 8, 10, or 11.\n")
        sys.exit(1)

    timeout = max(MIN_INQUIRY_TIMEOUT_MULTIPLIER, min(args.timeout, MAX_INQUIRY_TIMEOUT_MULTIPLIER))
    inquiry_duration_sec = timeout * 1.28

    if not args.json:
        # Enumerate radios
        radios = BluetoothDiscoveryEngine.enumerate_radios()
        print_radios(radios)

        if not args.no_inquiry:
            print(f"[*] Starting Classic Bluetooth RF Inquiry (Scan duration: ~{inquiry_duration_sec:.1f}s)...")
            print("[*] Discovering nearby discoverable devices...\n")
        else:
            print("[*] Querying Windows device cache (No RF inquiry requested)...\n")

    start_time = time.time()
    devices: List[DiscoveredBluetoothDevice] = []

    try:
        discovered_gen = BluetoothDiscoveryEngine.discover_devices(
            issue_inquiry=not args.no_inquiry,
            return_authenticated=True,
            return_remembered=True,
            return_unknown=True,
            return_connected=True,
            timeout_multiplier=timeout,
        )

        for dev in discovered_gen:
            # Apply user filters
            if args.connected_only and not dev.is_connected:
                continue
            if args.paired_only and not dev.is_authenticated:
                continue
            devices.append(dev)

    except PermissionError:
        sys.stderr.write("[!] Access denied querying Bluetooth devices.\n")
        sys.exit(1)
    except Exception as ex:
        sys.stderr.write(f"[!] Win32 Bluetooth Discovery failed: {ex}\n")
        sys.exit(1)

    elapsed = time.time() - start_time

    if args.json:
        out_list = [device_to_dict(d) for d in devices]
        print(json.dumps(out_list, indent=2))
        return

    if args.detailed:
        for dev in devices:
            render_detailed(dev)
    else:
        render_table(devices)

    print(f"[*] Discovery complete in {elapsed:.2f}s. Discovered: {len(devices)} device(s).")


if __name__ == "__main__":
    main()