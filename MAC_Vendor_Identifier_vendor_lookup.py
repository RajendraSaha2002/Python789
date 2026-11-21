

from dataclasses import dataclass
from typing import Optional, Dict, Any
from MAC_Vendor_Identifier_mac_constants import TransmissionScope, AdministrationScope, BleRandomType
from MAC_Vendor_Identifier_mac_parser import MacAddress, InvalidMacAddressError
from MAC_Vendor_Identifier_oui_database import OuiDatabase, VendorRecord


@dataclass
class MacAnalysisReport:
    """Complete diagnostic and vendor identification report for a MAC address."""
    input_str: str
    canonical_mac: str
    cisco_mac: str
    raw_hex: str
    oui_string: str
    first_byte_binary: str

    transmission_scope: str
    administration_scope: str
    is_randomized_private: bool
    randomization_reason: str

    vendor_name: str
    vendor_country: str
    vendor_category: str
    vendor_notes: str

    ble_classification: str

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the report into a JSON-compliant dictionary."""
        return {
            "mac_address": {
                "canonical": self.canonical_mac,
                "cisco": self.cisco_mac,
                "raw_hex": self.raw_hex,
                "oui": self.oui_string,
                "byte0_binary": self.first_byte_binary,
            },
            "scopes": {
                "transmission": self.transmission_scope,
                "administration": self.administration_scope,
            },
            "privacy_and_randomization": {
                "is_randomized_private": self.is_randomized_private,
                "reason": self.randomization_reason,
                "ble_subtype": self.ble_classification,
            },
            "vendor": {
                "company_name": self.vendor_name,
                "country": self.vendor_country,
                "category": self.vendor_category,
                "notes": self.vendor_notes,
            },
        }


class VendorLookupEngine:
    """Diagnostic coordinator for MAC addresses."""

    @classmethod
    def analyze(cls, raw_mac: str) -> MacAnalysisReport:
        """
        Parses a MAC address string, performs bitwise validation, checks the
        Locally Administered Address (LAA) flag, and resolves the vendor.
        """
        mac = MacAddress(raw_mac)

        is_random = mac.is_locally_administered
        random_reason = ""
        ble_desc = mac.ble_random_type.value

        # --------------------------------------------------------------------
        # Evaluation of Privacy & Randomization
        # --------------------------------------------------------------------
        if is_random:
            # Check the second hex character of byte 0
            # If U/L bit is 1, the second hex character is always 2, 6, A, or E
            second_nibble = f"{mac.octets[0]:02X}"[1]
            random_reason = (
                f"Locally Administered Address (LAA) bit is active (Byte 0 ends with '{second_nibble}'). "
                "This address is generated dynamically for user privacy by operating systems "
                "(Windows 11 Random Hardware Addresses, iOS Private Wi-Fi Address, or Android MAC Randomization). "
                "It does not correspond to an IEEE-registered hardware vendor."
            )
            vendor_name = "Randomized / Private MAC Address"
            vendor_country = "N/A (Generated Locally)"
            vendor_category = "Privacy / Ephemeral Interface"
            vendor_notes = "Hardware manufacturer is obfuscated by device OS."
        elif mac.is_broadcast:
            vendor_name = "Broadcast Address"
            vendor_country = "Global Standard"
            vendor_category = "Networking Protocol"
            vendor_notes = "Sent to all nodes within the broadcast domain."
            random_reason = "Universal Broadcast address (FF:FF:FF:FF:FF:FF)."
        elif mac.is_all_zeros:
            vendor_name = "Null / Unspecified Address"
            vendor_country = "Global Standard"
            vendor_category = "Networking Protocol"
            vendor_notes = "Empty or uninitialized MAC address."
            random_reason = "Unassigned address (00:00:00:00:00:00)."
        else:
            # Standard Universally Administered Address (UAA)
            record: Optional[VendorRecord] = OuiDatabase.lookup(mac.oui_string)
            if record:
                vendor_name = record.company_name
                vendor_country = record.country
                vendor_category = record.category
                vendor_notes = record.notes
                random_reason = "Standard hardware MAC registered with IEEE."
            else:
                vendor_name = f"Unknown Vendor (OUI {mac.formatted_oui})"
                vendor_country = "Unknown"
                vendor_category = "Unindexed OUI"
                vendor_notes = (
                    "OUI is universally administered, but not yet cataloged in the local database."
                )
                random_reason = "Standard IEEE hardware address (Unindexed manufacturer)."

        return MacAnalysisReport(
            input_str=raw_mac,
            canonical_mac=mac.to_colon_format(),
            cisco_mac=mac.to_cisco_format(),
            raw_hex=mac.to_raw_hex(),
            oui_string=mac.formatted_oui,
            first_byte_binary=mac.get_first_byte_binary_repr(),
            transmission_scope=mac.transmission_scope.value,
            administration_scope=mac.administration_scope.value,
            is_randomized_private=is_random,
            randomization_reason=random_reason,
            vendor_name=vendor_name,
            vendor_country=vendor_country,
            vendor_category=vendor_category,
            vendor_notes=vendor_notes,
            ble_classification=ble_desc,
        )