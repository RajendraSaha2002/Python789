

from dataclasses import dataclass, field
from typing import List, Dict, Any
from Classic_Bluetooth_win_constants import (
    MajorServiceClass,
    MajorDeviceClass,
    COMPUTER_MINOR_CLASSES,
    PHONE_MINOR_CLASSES,
    LAN_LOAD_FACTORS,
    AUDIO_VIDEO_MINOR_CLASSES,
    PERIPHERAL_TYPE_KEYBOARD,
    PERIPHERAL_TYPE_POINTING,
    PERIPHERAL_TYPE_COMBO,
    PERIPHERAL_SUBTYPES,
    IMAGING_BIT_DISPLAY,
    IMAGING_BIT_CAMERA,
    IMAGING_BIT_SCANNER,
    IMAGING_BIT_PRINTER,
    WEARABLE_MINOR_CLASSES,
    TOY_MINOR_CLASSES,
    HEALTH_MINOR_CLASSES,
)


@dataclass
class DecodedClassOfDevice:
    """Detailed structural breakdown of a 24-bit Bluetooth Class of Device."""
    raw_value: int
    hex_str: str
    major_device_class_name: str
    minor_device_class_name: str
    summary_label: str
    services: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_value": self.raw_value,
            "hex": self.hex_str,
            "summary": self.summary_label,
            "major_device_class": self.major_device_class_name,
            "minor_device_class": self.minor_device_class_name,
            "services": self.services,
        }


class ClassOfDeviceDecoder:
    """Parser for Bluetooth SIG CoD values."""

    @classmethod
    def decode_services(cls, cod: int) -> List[str]:
        """Extracts all active Major Service Class flags (bits 13 to 23)."""
        services = []
        for service in MajorServiceClass:
            if cod & service.value:
                # Humanize enum member name
                clean_name = service.name.replace("_", " ").title()
                services.append(clean_name)
        return services

    @classmethod
    def decode_minor(cls, major_class: MajorDeviceClass, cod: int) -> str:
        """Decodes the 6-bit minor device field based on the major class."""
        minor_bits = (cod >> 2) & 0x3F  # Bits 2..7

        if major_class == MajorDeviceClass.COMPUTER:
            return COMPUTER_MINOR_CLASSES.get(minor_bits, f"Unknown Computer ({minor_bits})")

        elif major_class == MajorDeviceClass.PHONE:
            return PHONE_MINOR_CLASSES.get(minor_bits, f"Unknown Phone ({minor_bits})")

        elif major_class == MajorDeviceClass.LAN_NETWORK:
            load_factor = (minor_bits >> 3) & 0x07
            return f"LAN/Access Point - {LAN_LOAD_FACTORS.get(load_factor, 'Unknown')}"

        elif major_class == MajorDeviceClass.AUDIO_VIDEO:
            return AUDIO_VIDEO_MINOR_CLASSES.get(minor_bits, f"Unknown Audio/Video ({minor_bits})")

        elif major_class == MajorDeviceClass.PERIPHERAL:
            peripheral_type = minor_bits & 0x30  # Bits 6..7
            subtype = minor_bits & 0x0F  # Bits 2..5

            type_label = "Peripheral"
            if peripheral_type == PERIPHERAL_TYPE_KEYBOARD:
                type_label = "Keyboard"
            elif peripheral_type == PERIPHERAL_TYPE_POINTING:
                type_label = "Pointing Device (Mouse)"
            elif peripheral_type == PERIPHERAL_TYPE_COMBO:
                type_label = "Combo Keyboard/Mouse"

            subtype_label = PERIPHERAL_SUBTYPES.get(subtype, f"Subtype {subtype}")
            return f"{type_label} [{subtype_label}]"

        elif major_class == MajorDeviceClass.IMAGING:
            capabilities = []
            if cod & IMAGING_BIT_DISPLAY:
                capabilities.append("Display")
            if cod & IMAGING_BIT_CAMERA:
                capabilities.append("Camera")
            if cod & IMAGING_BIT_SCANNER:
                capabilities.append("Scanner")
            if cod & IMAGING_BIT_PRINTER:
                capabilities.append("Printer")
            return f"Imaging Device ({', '.join(capabilities)})" if capabilities else "Unspecified Imaging"

        elif major_class == MajorDeviceClass.WEARABLE:
            return WEARABLE_MINOR_CLASSES.get(minor_bits, f"Unknown Wearable ({minor_bits})")

        elif major_class == MajorDeviceClass.TOY:
            return TOY_MINOR_CLASSES.get(minor_bits, f"Unknown Toy ({minor_bits})")

        elif major_class == MajorDeviceClass.HEALTH:
            return HEALTH_MINOR_CLASSES.get(minor_bits, f"Unknown Health Device ({minor_bits})")

        elif major_class == MajorDeviceClass.MISCELLANEOUS:
            return "Miscellaneous / Generic"

        return f"Uncategorized (0x{minor_bits:02X})"

    @classmethod
    def decode(cls, cod: int) -> DecodedClassOfDevice:
        """Parses a full 24-bit CoD into structured, human-readable records."""
        major_class_num = (cod >> 8) & 0x1F  # Bits 8..12
        hex_str = f"0x{cod:06X}"

        try:
            major_enum = MajorDeviceClass(major_class_num)
            major_name = major_enum.name.replace("_", " ").title()
        except ValueError:
            major_enum = MajorDeviceClass.UNCATEGORIZED
            major_name = f"Unknown (0x{major_class_num:02X})"

        minor_name = cls.decode_minor(major_enum, cod)
        services = cls.decode_services(cod)

        # Build clean primary summary label
        if major_enum in (MajorDeviceClass.COMPUTER, MajorDeviceClass.PHONE, MajorDeviceClass.AUDIO_VIDEO):
            summary = minor_name
        else:
            summary = f"{major_name} ({minor_name})"

        return DecodedClassOfDevice(
            raw_value=cod,
            hex_str=hex_str,
            major_device_class_name=major_name,
            minor_device_class_name=minor_name,
            summary_label=summary,
            services=services,
        )