

import os
import re
import subprocess
from typing import List, Dict, Optional
from MAC_Vendor_Identifier_vendor_lookup import VendorLookupEngine, MacAnalysisReport


# Regular expression matching valid MAC addresses in arbitrary text
MAC_REGEX = re.compile(
    r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b|"
    r"\b(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}\b|"
    r"\b[0-9A-Fa-f]{12}\b"
)


class BatchMacProcessor:
    """Processes collections of MAC addresses from text sources or files."""

    @classmethod
    def analyze_list(cls, mac_list: List[str]) -> List[MacAnalysisReport]:
        """Analyzes an in-memory list of MAC address strings."""
        reports = []
        for raw in mac_list:
            clean = raw.strip()
            if not clean:
                continue
            try:
                report = VendorLookupEngine.analyze(clean)
                reports.append(report)
            except Exception:
                continue
        return reports

    @classmethod
    def extract_from_text(cls, text: str) -> List[str]:
        """Extracts all unique MAC addresses discovered in freeform text."""
        matches = MAC_REGEX.findall(text)
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for m in matches:
            norm = m.upper().replace("-", ":")
            if norm not in seen:
                seen.add(norm)
                deduped.append(m)
        return deduped

    @classmethod
    def analyze_file(cls, filepath: str) -> List[MacAnalysisReport]:
        """Reads a file, extracts all contained MAC addresses, and resolves them."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Source file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        macs = cls.extract_from_text(content)
        return cls.analyze_list(macs)


class WindowsNetworkInspector:
    """Native Windows 11 diagnostic utility for local network neighbor analysis."""

    @staticmethod
    def get_arp_table() -> List[Dict[str, str]]:
        """
        Runs Windows native 'arp -a' command and extracts IP-to-MAC mappings.
        Works out of the box on Windows 11 Home, Pro, and Enterprise.
        """
        try:
            output = subprocess.check_output(
                ["arp", "-a"],
                text=True,
                stderr=subprocess.DEVNULL,
                shell=False
            )
        except Exception as ex:
            return []

        entries = []
        # Match lines like:  192.168.1.1       00-11-22-33-44-55     dynamic
        line_regex = re.compile(
            r"^\s*([0-9]{1,3}(?:\.[0-9]{1,3}){3})\s+([0-9a-fA-F-]{17})\s+(\w+)",
            re.MULTILINE
        )

        for match in line_regex.finditer(output):
            ip_addr, mac_addr, entry_type = match.groups()
            # Normalize to colon delimiter
            colon_mac = mac_addr.replace("-", ":").upper()
            entries.append({
                "ip": ip_addr,
                "mac": colon_mac,
                "type": entry_type.capitalize(),
            })

        return entries

    @staticmethod
    def get_local_adapters() -> List[Dict[str, str]]:
        """
        Runs Windows native 'getmac /v /fo csv' to inspect physical adapters.
        """
        try:
            output = subprocess.check_output(
                ["getmac", "/v", "/fo", "csv"],
                text=True,
                stderr=subprocess.DEVNULL,
                shell=False
            )
        except Exception:
            return []

        adapters = []
        lines = [line.strip() for line in output.strip().splitlines() if line.strip()]
        if len(lines) <= 1:
            return adapters

        import csv
        reader = csv.reader(lines)
        header = next(reader)  # Connection Name, Network Adapter, Physical Address, Transport Name

        for row in reader:
            if len(row) >= 3:
                conn_name = row[0]
                adapter_name = row[1]
                phys_addr = row[2].replace("-", ":").upper()
                if phys_addr and phys_addr != "N/A":
                    adapters.append({
                        "connection": conn_name,
                        "adapter": adapter_name,
                        "mac": phys_addr,
                    })

        return adapters