

from enum import Enum, unique


# ============================================================================
# IEEE 802 MAC Address Bitmasks (Applied to the 1st Octet / Most Significant Byte)
# ============================================================================

# Bit 0 of Byte 0: Individual / Group (I/G) Bit
# 0 = Unicast (Individual address)
# 1 = Multicast / Broadcast (Group address)
IEEE_IG_MASK = 0x01

# Bit 1 of Byte 0: Universally / Locally Administered (U/L) Bit
# 0 = Universally Administered Address (UAA) - Enforced by IEEE OUI registration
# 1 = Locally Administered Address (LAA) - Private, randomized, or locally assigned
IEEE_UL_MASK = 0x02


# ============================================================================
# Bluetooth Low Energy (BLE) Address Type Masks (Top 2 bits of Byte 0)
# ============================================================================
# In BLE specifications, Random addresses are classified by bits [7:6] of MSB
BLE_RANDOM_SUBTYPE_MASK = 0xC0
BLE_RANDOM_SUBTYPE_SHIFT = 6

BLE_NON_RESOLVABLE_PRIVATE = 0b00  # 0x00: Non-Resolvable Private Address (NRPA)
BLE_RESOLVABLE_PRIVATE     = 0b01  # 0x40: Resolvable Private Address (RPA)
BLE_RESERVED_RANDOM        = 0b10  # 0x80: Reserved for future use
BLE_STATIC_RANDOM          = 0b11  # 0xC0: Static Device Address


# ============================================================================
# Standard Address Characteristics Enums
# ============================================================================

@unique
class TransmissionScope(Enum):
    """Specifies the destination delivery mode of the frame."""
    UNICAST = "Unicast (Individual Device)"
    MULTICAST = "Multicast (Group Address)"
    BROADCAST = "Broadcast (All Nodes)"


@unique
class AdministrationScope(Enum):
    """Specifies whether the address is globally unique (IEEE) or locally assigned."""
    UNIVERSAL = "Universally Administered (Global IEEE OUI Enforced)"
    LOCAL = "Locally Administered (Private / Randomized / Non-Standard)"


@unique
class BleRandomType(Enum):
    """Bluetooth Low Energy Random Address Category."""
    NOT_BLE_RANDOM = "Not a BLE Random Address (Standard IEEE UAA)"
    STATIC = "BLE Static Device Address (Fixed across power cycles)"
    RESOLVABLE_PRIVATE = "BLE Resolvable Private Address (RPA, Rotates periodically)"
    NON_RESOLVABLE_PRIVATE = "BLE Non-Resolvable Private Address (NRPA, Ephemeral)"
    RESERVED = "BLE Reserved Random Format"


# ============================================================================
# Special MAC Addresses
# ============================================================================
BROADCAST_MAC_STR = "FF:FF:FF:FF:FF:FF"
ZERO_MAC_STR = "00:00:00:00:00:00"

# Common Well-Known Multicast Address Prefixes
WELL_KNOWN_MULTICAST_PREFIXES = {
    "01:00:5E": "IPv4 Multicast (RFC 1112)",
    "33:33":    "IPv6 Multicast (RFC 2464)",
    "01:80:C2": "Spanning Tree Protocol (STP / IEEE 802.1D)",
    "01:0C:CD": "IEC 61850-8-1 (GOOSE / Sampled Values)",
    "01:1B:19": "Precision Time Protocol (PTP / IEEE 1588)",
}