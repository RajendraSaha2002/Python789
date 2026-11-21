

import re
from typing import Tuple, List
from MAC_Vendor_Identifier_mac_constants import (
    IEEE_IG_MASK,
    IEEE_UL_MASK,
    BLE_RANDOM_SUBTYPE_MASK,
    BLE_RANDOM_SUBTYPE_SHIFT,
    BLE_STATIC_RANDOM,
    BLE_RESOLVABLE_PRIVATE,
    BLE_NON_RESOLVABLE_PRIVATE,
    TransmissionScope,
    AdministrationScope,
    BleRandomType,
    BROADCAST_MAC_STR,
    ZERO_MAC_STR,
)


class InvalidMacAddressError(ValueError):
    """Raised when an input string cannot be parsed as a valid 48-bit MAC address."""
    pass


class MacAddress:
    """Represents a validated 48-bit (6-octet) MAC address with bitwise inspection."""

    __slots__ = ("_octets",)

    def __init__(self, raw_input: str):
        self._octets: Tuple[int, ...] = self._parse_input(raw_input)

    @staticmethod
    def _parse_input(raw: str) -> Tuple[int, ...]:
        """Validates and parses various MAC address string representations."""
        if not isinstance(raw, str):
            raise InvalidMacAddressError(f"Expected string input, got {type(raw).__name__}")

        cleaned = raw.strip()

        # Regular expression patterns for common MAC formats
        # Standard: 00:11:22:33:44:55 or 00-11-22-33-44-55
        hex_pair_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
        # Cisco style: 0011.2233.4455
        cisco_pattern = re.compile(r"^([0-9A-Fa-f]{4}\.){2}([0-9A-Fa-f]{4})$")
        # Raw hex: 001122334455
        raw_pattern = re.compile(r"^[0-9A-Fa-f]{12}$")
        # Space separated: 00 11 22 33 44 55
        space_pattern = re.compile(r"^([0-9A-Fa-f]{2}\s){5}([0-9A-Fa-f]{2})$")

        if hex_pair_pattern.match(cleaned):
            delimiter = ":" if ":" in cleaned else "-"
            parts = [int(p, 16) for p in cleaned.split(delimiter)]
        elif cisco_pattern.match(cleaned):
            parts = []
            for group in cleaned.split("."):
                parts.append(int(group[0:2], 16))
                parts.append(int(group[2:4], 16))
        elif space_pattern.match(cleaned):
            parts = [int(p, 16) for p in cleaned.split()]
        elif raw_pattern.match(cleaned):
            parts = [int(cleaned[i:i+2], 16) for i in range(0, 12, 2)]
        else:
            raise InvalidMacAddressError(
                f"Invalid MAC address format: '{raw}'. "
                "Accepted formats: '00:11:22:33:44:55', '00-11-22-33-44-55', "
                "'0011.2233.4455', or '001122334455'"
            )

        return tuple(parts)

    @property
    def octets(self) -> Tuple[int, ...]:
        """Returns the 6 octets as integers (0 to 255)."""
        return self._octets

    @property
    def bytes(self) -> bytes:
        """Returns raw 6 bytes representation."""
        return bytes(self._octets)

    # ------------------------------------------------------------------------
    # Formatting Representations
    # ------------------------------------------------------------------------
    def to_colon_format(self) -> str:
        """Standard canonical representation: 00:11:22:33:44:55."""
        return ":".join(f"{b:02X}" for b in self._octets)

    def to_hyphen_format(self) -> str:
        """Windows / IEEE standard format: 00-11-22-33-44-55."""
        return "-".join(f"{b:02X}" for b in self._octets)

    def to_cisco_format(self) -> str:
        """Cisco switch format: 0011.2233.4455."""
        h = [f"{b:02x}" for b in self._octets]
        return f"{h[0]}{h[1]}.{h[2]}{h[3]}.{h[4]}{h[5]}"

    def to_raw_hex(self) -> str:
        """Contiguous hex string: 001122334455."""
        return "".join(f"{b:02X}" for b in self._octets)

    # ------------------------------------------------------------------------
    # OUI and NIC Fields
    # ------------------------------------------------------------------------
    @property
    def oui_octets(self) -> Tuple[int, int, int]:
        """First 3 bytes (Organizationally Unique Identifier)."""
        return self._octets[0], self._octets[1], self._octets[2]

    @property
    def nic_octets(self) -> Tuple[int, int, int]:
        """Last 3 bytes (Network Interface Controller specific identifier)."""
        return self._octets[3], self._octets[4], self._octets[5]

    @property
    def oui_string(self) -> str:
        """Returns normalized 6-character OUI hex string: '0017F2'."""
        return "".join(f"{b:02X}" for b in self.oui_octets)

    @property
    def formatted_oui(self) -> str:
        """Returns colon-separated OUI string: '00:17:F2'."""
        return ":".join(f"{b:02X}" for b in self.oui_octets)

    # ------------------------------------------------------------------------
    # IEEE 802 Header Bit Inspections (Byte 0)
    # ------------------------------------------------------------------------
    @property
    def is_multicast(self) -> bool:
        """Checks if the Individual/Group (I/G) bit is set (Bit 0 of Byte 0)."""
        return (self._octets[0] & IEEE_IG_MASK) != 0

    @property
    def is_unicast(self) -> bool:
        """Checks if the address is a Unicast address."""
        return not self.is_multicast

    @property
    def is_broadcast(self) -> bool:
        """Checks if the address is the universal broadcast address (FF:FF:FF:FF:FF:FF)."""
        return self._octets == (0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)

    @property
    def is_all_zeros(self) -> bool:
        """Checks if the address is unassigned (00:00:00:00:00:00)."""
        return self._octets == (0x00, 0x00, 0x00, 0x00, 0x00, 0x00)

    @property
    def is_locally_administered(self) -> bool:
        """
        Checks if the Universally/Locally Administered (U/L) bit is set (Bit 1 of Byte 0).
        If True, the address is private, randomized, or locally assigned.
        """
        return (self._octets[0] & IEEE_UL_MASK) != 0

    @property
    def is_universally_administered(self) -> bool:
        """Checks if the address is a globally registered IEEE OUI address."""
        return not self.is_locally_administered

    @property
    def transmission_scope(self) -> TransmissionScope:
        """Returns the classified transmission type."""
        if self.is_broadcast:
            return TransmissionScope.BROADCAST
        if self.is_multicast:
            return TransmissionScope.MULTICAST
        return TransmissionScope.UNICAST

    @property
    def administration_scope(self) -> AdministrationScope:
        """Returns whether the address is globally or locally administered."""
        if self.is_locally_administered:
            return AdministrationScope.LOCAL
        return AdministrationScope.UNIVERSAL

    # ------------------------------------------------------------------------
    # Bluetooth Low Energy (BLE) Classification
    # ------------------------------------------------------------------------
    @property
    def ble_random_type(self) -> BleRandomType:
        """
        Classifies address under Bluetooth Low Energy (BLE) specifications.
        BLE Random Addresses require the U/L bit to be set (Locally Administered).
        """
        if not self.is_locally_administered:
            return BleRandomType.NOT_BLE_RANDOM

        # Extract bits 7 and 6 from the most significant byte (Byte 0)
        subtype = (self._octets[0] & BLE_RANDOM_SUBTYPE_MASK) >> BLE_RANDOM_SUBTYPE_SHIFT

        if subtype == BLE_STATIC_RANDOM:
            return BleRandomType.STATIC
        elif subtype == BLE_RESOLVABLE_PRIVATE:
            return BleRandomType.RESOLVABLE_PRIVATE
        elif subtype == BLE_NON_RESOLVABLE_PRIVATE:
            return BleRandomType.NON_RESOLVABLE_PRIVATE
        return BleRandomType.RESERVED

    def get_first_byte_binary_repr(self) -> str:
        """Returns binary representation of Byte 0 with bit labels."""
        b0 = self._octets[0]
        bin_str = f"{b0:08b}"
        return (
            f"{bin_str} (Bit7: {bin_str[0]}, Bit6: {bin_str[1]}, "
            f"U/L[Bit1]: {bin_str[6]}, I/G[Bit0]: {bin_str[7]})"
        )

    def __str__(self) -> str:
        return self.to_colon_format()

    def __repr__(self) -> str:
        return f"<MacAddress {self.to_colon_format()} ({self.administration_scope.name})>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MacAddress):
            return self._octets == other._octets
        return False

    def __hash__(self) -> int:
        return hash(self._octets)