import platform
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

EXPORT_DIR = Path("passwords")


def ensure_windows() -> None:
    if platform.system().lower() != "windows":
        raise SystemError("This script only works on Windows (requires 'netsh').")


def export_profiles(out_dir: Path) -> None:
    """
    Exports all WLAN profiles to XML with cleartext keys (where available).
    Netsh syntax: netsh wlan export profile key=clear folder="<path>"
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["netsh", "wlan", "export", "profile", "key=clear", f'folder={str(out_dir)}']
    # Suppress stdout noise, capture stderr for diagnostics
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"netsh export failed: {result.stderr.strip() or 'Unknown error'}")


def iter_children_by_local_name(elem: ET.Element, name: str):
    local = name
    for child in list(elem):
        # Handle namespaced tags: '{namespace}tag'
        if child.tag.split('}')[-1] == local:
            yield child


def find_path_text(root: ET.Element, path: list[str]) -> str | None:
    """
    Traverse XML by local-name only (ignores namespaces).
    Example paths:
      - ["SSIDConfig", "SSID", "name"]
      - ["MSM", "security", "sharedKey", "keyMaterial"]
    """
    nodes = [root]
    for part in path:
        next_nodes = []
        for n in nodes:
            next_nodes.extend(iter_children_by_local_name(n, part))
        if not next_nodes:
            return None
        nodes = next_nodes
    # Take the first match's text
    return nodes[0].text if nodes and nodes[0].text is not None else None


def load_profiles(out_dir: Path) -> list[dict]:
    """
    Returns a list of dicts: {ssid, password, file}
    Password may be None for open networks.
    """
    profiles: list[dict] = []
    for xml_file in sorted(out_dir.glob("*.xml")):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            ssid = find_path_text(root, ["SSIDConfig", "SSID", "name"])
            pwd = find_path_text(root, ["MSM", "security", "sharedKey", "keyMaterial"])
            if ssid is None:
                # Fallback: some profiles may have SSID at a slightly different path
                ssid = find_path_text(root, ["SSID", "name"]) or "(unknown-SSID)"
            profiles.append({"ssid": ssid, "password": pwd, "file": xml_file})
        except Exception as e:
            profiles.append({"ssid": f"(failed to parse {xml_file.name})", "password": None, "file": xml_file})
    return profiles


def print_menu(profiles: list[dict]) -> None:
    print("Here is the list of Wi‑Fi networks registered on this device:\n")
    for idx, p in enumerate(profiles, start=1):
        print(f"[{idx}] {p['ssid']}")
    print("\nType the number to view SSID and password, or 'all' to print all, or 'q' to quit.")


def prompt_choice(max_index: int) -> str:
    while True:
        choice = input("Please choose a number (or 'all'/'q'): ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            return "q"
        if choice == "all":
            return "all"
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= max_index:
                return choice
        print("Invalid choice. Try again.")


def show_selection(profiles: list[dict], choice: str) -> None:
    def show(idx: int):
        entry = profiles[idx]
        ssid = entry["ssid"]
        pwd = entry["password"]
        if pwd:
            print(f"\nSSID   : {ssid}\nPassword: {pwd}\n")
        else:
            print(f"\nSSID   : {ssid}\nPassword: (none or unavailable)\n")

    if choice == "all":
        for i in range(len(profiles)):
            show(i)
    else:
        show(int(choice) - 1)


def cleanup(out_dir: Path) -> None:
    # Remove exported XML files and directory
    try:
        for f in out_dir.glob("*.xml"):
            f.unlink(missing_ok=True)
        # Remove dir if empty
        out_dir.rmdir()
    except Exception:
        # Best-effort cleanup
        pass


def main():
    ensure_windows()
    try:
        export_profiles(EXPORT_DIR)
        profiles = load_profiles(EXPORT_DIR)
        if not profiles:
            print("No WLAN profiles were exported. You may need to run this in an elevated terminal.")
            return
        print_menu(profiles)
        choice = prompt_choice(len(profiles))
        if choice == "q":
            return
        show_selection(profiles, choice)
    finally:
        print("Thanks for using this tool :)")
        cleanup(EXPORT_DIR)


if __name__ == "__main__":
    main()