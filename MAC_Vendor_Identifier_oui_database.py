

from dataclasses import dataclass
from typing import Dict, Optional, List


@dataclass(frozen=True)
class VendorRecord:
    """Represents a vendor entry in the local OUI registry."""
    company_name: str
    country: str
    category: str
    notes: str = ""


# Master Local Lookup Table (Normalized 6-character uppercase hex strings)
OUI_REGISTRY: Dict[str, VendorRecord] = {
    # ------------------------------------------------------------------------
    # Apple, Inc.
    # ------------------------------------------------------------------------
    "0017F2": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "Mac / iPhone"),
    "001E52": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "MacBook / iMac"),
    "002500": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "iPhone / iPad"),
    "28CFDA": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "Apple Watch / iPhone"),
    "3C0754": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "iPad / AirPort"),
    "705681": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "Apple TV"),
    "ACDE48": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "iPhone / Mac"),
    "F01898": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "AirPods / Apple Watch"),
    "F4F15A": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "iPhone / iPad"),
    "BC9FEF": VendorRecord("Apple, Inc.", "United States", "Mobile / Compute", "Mac Studio / MacBook Pro"),

    # ------------------------------------------------------------------------
    # Samsung Electronics Co., Ltd.
    # ------------------------------------------------------------------------
    "0007AB": VendorRecord("Samsung Electronics", "South Korea", "Mobile / Consumer", "Galaxy Series"),
    "0012FB": VendorRecord("Samsung Electronics", "South Korea", "Consumer Electronics", "Smart TVs"),
    "00166C": VendorRecord("Samsung Electronics", "South Korea", "Mobile / Wearables", "Galaxy Watch"),
    "144D67": VendorRecord("Samsung Electronics", "South Korea", "Mobile / Compute", "Galaxy Tab"),
    "244BFE": VendorRecord("Samsung Electronics", "South Korea", "Mobile / Consumer", "Smart Appliances"),
    "342387": VendorRecord("Samsung Electronics", "South Korea", "Mobile / Compute", "Galaxy S Series"),
    "508569": VendorRecord("Samsung Electronics", "South Korea", "Consumer Electronics", "Soundbars / Monitors"),
    "842519": VendorRecord("Samsung Electronics", "South Korea", "Mobile / Compute", "Galaxy Z Fold / Flip"),
    "E47CF9": VendorRecord("Samsung Electronics", "South Korea", "Mobile / Consumer", "Galaxy A Series"),

    # ------------------------------------------------------------------------
    # Sony Corporation / Sony Interactive Entertainment
    # ------------------------------------------------------------------------
    "00014A": VendorRecord("Sony Corporation", "Japan", "Audio / Video", "Broadcast Equipment"),
    "00041F": VendorRecord("Sony Interactive Entertainment", "Japan", "Gaming Console", "PlayStation 2 / 3"),
    "001315": VendorRecord("Sony Mobile", "Japan", "Mobile", "Xperia Phones"),
    "0019C5": VendorRecord("Sony Interactive Entertainment", "Japan", "Gaming Console", "PlayStation 3 / Vita"),
    "709E29": VendorRecord("Sony Interactive Entertainment", "Japan", "Gaming Console", "PlayStation 4"),
    "F8461C": VendorRecord("Sony Interactive Entertainment", "Japan", "Gaming Console", "PlayStation 5"),
    "001D27": VendorRecord("Sony Corporation", "Japan", "Audio / Video", "Bravia Smart TV"),
    "045D4B": VendorRecord("Sony Corporation", "Japan", "Audio / Video", "WH-1000XM Series Headphones"),

    # ------------------------------------------------------------------------
    # Google LLC / Alphabet Inc.
    # ------------------------------------------------------------------------
    "001A11": VendorRecord("Google LLC", "United States", "Smart Home / Networking", "Google Nest / Wi-Fi"),
    "3C5AB4": VendorRecord("Google LLC", "United States", "Smart Home", "Google Home Mini"),
    "546009": VendorRecord("Google LLC", "United States", "Smart Home", "Chromecast / Google TV"),
    "94EB2C": VendorRecord("Google LLC", "United States", "Mobile", "Pixel Smartphone Series"),
    "D86C63": VendorRecord("Google LLC", "United States", "Wearables", "Pixel Watch / Fitbit"),

    # ------------------------------------------------------------------------
    # Microsoft Corporation
    # ------------------------------------------------------------------------
    "0003FF": VendorRecord("Microsoft Corporation", "United States", "Compute / Network", "Virtual Machines / Hyper-V"),
    "00155D": VendorRecord("Microsoft Corporation", "United States", "Virtualization", "Hyper-V Virtual Adapter"),
    "0050F2": VendorRecord("Microsoft Corporation", "United States", "Compute", "Surface Devices"),
    "281878": VendorRecord("Microsoft Corporation", "United States", "Gaming Console", "Xbox Series X / S"),
    "7CD95C": VendorRecord("Microsoft Corporation", "United States", "Gaming Console", "Xbox One"),
    "DC5360": VendorRecord("Microsoft Corporation", "United States", "Compute", "Surface Pro / Laptop"),

    # ------------------------------------------------------------------------
    # Intel Corporation
    # ------------------------------------------------------------------------
    "0002B3": VendorRecord("Intel Corporation", "United States", "Networking / Silicon", "Ethernet Adapters"),
    "001B21": VendorRecord("Intel Corporation", "United States", "Networking / Silicon", "Centrino Wi-Fi"),
    "3413E8": VendorRecord("Intel Corporation", "United States", "Networking / Silicon", "AX200 / AX210 Wi-Fi 6"),
    "6805CA": VendorRecord("Intel Corporation", "United States", "Networking / Silicon", "Gigabit Network Card"),
    "A0C589": VendorRecord("Intel Corporation", "United States", "Networking / Silicon", "Killer Wi-Fi Adapters"),
    "F8633F": VendorRecord("Intel Corporation", "United States", "Networking / Silicon", "BE200 Wi-Fi 7"),

    # ------------------------------------------------------------------------
    # Cisco Systems, Inc. / Meraki / Linksys
    # ------------------------------------------------------------------------
    "00000C": VendorRecord("Cisco Systems, Inc.", "United States", "Enterprise Networking", "Routers / Switches"),
    "000142": VendorRecord("Cisco Systems, Inc.", "United States", "Enterprise Networking", "Catalyst Series"),
    "00180A": VendorRecord("Cisco Meraki", "United States", "Cloud Networking", "MR Access Points"),
    "001839": VendorRecord("Cisco-Linksys", "United States", "Consumer Networking", "WRT Series Routers"),
    "002414": VendorRecord("Cisco Systems, Inc.", "United States", "Enterprise Networking", "IP Phones"),
    "E4AA5D": VendorRecord("Cisco Meraki", "United States", "Cloud Networking", "MS Switches / MX Gateways"),

    # ------------------------------------------------------------------------
    # Espressif Systems (IoT / Microcontrollers)
    # ------------------------------------------------------------------------
    "18FE34": VendorRecord("Espressif Systems", "China", "Microcontroller / IoT", "ESP8266 SoC"),
    "240AC4": VendorRecord("Espressif Systems", "China", "Microcontroller / IoT", "ESP32 SoC"),
    "30AEA4": VendorRecord("Espressif Systems", "China", "Microcontroller / IoT", "ESP32-WROOM"),
    "A4CF12": VendorRecord("Espressif Systems", "China", "Microcontroller / IoT", "ESP32-S2 / S3"),
    "EC94CB": VendorRecord("Espressif Systems", "China", "Microcontroller / IoT", "ESP32-C3 / C6"),

    # ------------------------------------------------------------------------
    # Raspberry Pi Trading / Foundation
    # ------------------------------------------------------------------------
    "B827EB": VendorRecord("Raspberry Pi Foundation", "United Kingdom", "Single-Board Computer", "Raspberry Pi 1/2/3/Zero"),
    "DCA632": VendorRecord("Raspberry Pi Trading Ltd", "United Kingdom", "Single-Board Computer", "Raspberry Pi 4 / 400"),
    "28CDC1": VendorRecord("Raspberry Pi Trading Ltd", "United Kingdom", "Single-Board Computer", "Raspberry Pi Pico W / Pi 5"),

    # ------------------------------------------------------------------------
    # Network Equipment (TP-Link, Netgear, Ubiquiti, Synology, MikroTik)
    # ------------------------------------------------------------------------
    "0014D1": VendorRecord("TP-Link Corporation", "China", "Consumer Networking", "Archer Series"),
    "50C7BF": VendorRecord("TP-Link Corporation", "China", "Smart Home", "Tapo / Kasa Smart Plugs"),
    "984827": VendorRecord("TP-Link Corporation", "China", "Consumer Networking", "Deco Mesh Wi-Fi"),
    "000FB5": VendorRecord("NETGEAR", "United States", "Consumer Networking", "Nighthawk Routers"),
    "20E52A": VendorRecord("NETGEAR", "United States", "Consumer Networking", "Orbi Mesh Systems"),
    "002722": VendorRecord("Ubiquiti Networks Inc.", "United States", "Enterprise Networking", "UniFi AP / Switch"),
    "245A4C": VendorRecord("Ubiquiti Networks Inc.", "United States", "Enterprise Networking", "Dream Machine / Cloud Key"),
    "001132": VendorRecord("Synology Inc.", "Taiwan", "Network Attached Storage", "DiskStation NAS"),
    "000C42": VendorRecord("MikroTik", "Latvia", "Network Equipment", "RouterBOARD / RouterOS"),

    # ------------------------------------------------------------------------
    # PC / Mobile Vendors (Dell, HP, Lenovo, ASUS, Xiaomi, Huawei, Amazon)
    # ------------------------------------------------------------------------
    "001422": VendorRecord("Dell Inc.", "United States", "Compute", "OptiPlex / Latitude"),
    "F8BC12": VendorRecord("Dell Inc.", "United States", "Compute", "XPS / Alienware"),
    "000802": VendorRecord("HP Inc.", "United States", "Compute / Print", "LaserJet / DeskJet"),
    "3CD92B": VendorRecord("HP Inc.", "United States", "Compute", "Spectre / Envy Laptops"),
    "001A6B": VendorRecord("Lenovo", "China", "Compute", "ThinkPad Series"),
    "54EE75": VendorRecord("Lenovo", "China", "Compute", "Legion Gaming Laptops"),
    "001E8C": VendorRecord("ASUSTeK Computer Inc.", "Taiwan", "Compute / Network", "ROG / ZenBook"),
    "107B44": VendorRecord("ASUSTeK Computer Inc.", "Taiwan", "Consumer Networking", "RT-AX Routers"),
    "000EC6": VendorRecord("Huawei Technologies Co., Ltd.", "China", "Telecommunications", "Enterprise Routers"),
    "E0247F": VendorRecord("Huawei Technologies Co., Ltd.", "China", "Mobile", "Mate / P Series"),
    "009EEA": VendorRecord("Xiaomi Communications Co Ltd", "China", "Mobile / Smart Home", "Redmi / Mi Series"),
    "584498": VendorRecord("Xiaomi Communications Co Ltd", "China", "Smart Home", "Mi Home Ecosystem"),
    "00FC8B": VendorRecord("Amazon Technologies Inc.", "United States", "Smart Home / Media", "Echo Dot / Show"),
    "44650D": VendorRecord("Amazon Technologies Inc.", "United States", "Media Streaming", "Fire TV Stick"),
    "FC65DE": VendorRecord("Amazon Technologies Inc.", "United States", "E-Reader", "Kindle Paperwhite"),

    # ------------------------------------------------------------------------
    # Audio, Wearables & Connected Home (Sonos, Bose, Roku, Philips, Tuya)
    # ------------------------------------------------------------------------
    "000E58": VendorRecord("Sonos, Inc.", "United States", "Audio", "Sonos One / Move / Arc"),
    "000C8A": VendorRecord("Bose Corporation", "United States", "Audio", "QuietComfort Headphones"),
    "000D4B": VendorRecord("Roku, Inc.", "United States", "Media Streaming", "Roku Ultra / Streaming Stick"),
    "001788": VendorRecord("Philips Lighting (Signify)", "Netherlands", "Smart Lighting", "Hue Bridge / Bulbs"),
    "10D561": VendorRecord("Tuya Smart Inc.", "China", "IoT Platform", "Smart Life Devices"),
}


class OuiDatabase:
    """Provides indexed query methods for resolving MAC addresses to vendors."""

    @staticmethod
    def normalize_oui(oui_hex: str) -> str:
        """Removes delimiters and returns a uniform 6-character uppercase string."""
        clean = oui_hex.replace(":", "").replace("-", "").replace(".", "").strip().upper()
        if len(clean) < 6:
            raise ValueError(f"OUI fragment too short: '{oui_hex}' (Requires at least 3 bytes / 6 hex chars)")
        return clean[:6]

    @classmethod
    def lookup(cls, oui_hex: str) -> Optional[VendorRecord]:
        """Resolves an OUI prefix (e.g. '00:17:F2' or '0017F2') to a VendorRecord."""
        norm = cls.normalize_oui(oui_hex)
        return OUI_REGISTRY.get(norm)

    @classmethod
    def search_by_vendor(cls, query: str) -> List[tuple]:
        """Returns all registered OUIs matching a vendor name query."""
        q = query.lower()
        results = []
        for oui, record in OUI_REGISTRY.items():
            if q in record.company_name.lower() or q in record.notes.lower():
                formatted_oui = f"{oui[0:2]}:{oui[2:4]}:{oui[4:6]}"
                results.append((formatted_oui, record))
        return results