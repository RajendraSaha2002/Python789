

from enum import IntEnum, unique

# ============================================================================
# Windows System Errors
# ============================================================================
ERROR_SUCCESS = 0x00000000
ERROR_INVALID_PARAMETER = 0x00000057
ERROR_NO_MORE_ITEMS = 0x00000103
ERROR_DEVICE_NOT_CONNECTED = 0x0000048F
ERROR_NOT_FOUND = 0x00000490

# ============================================================================
# Bluetooth API Limits & Defaults
# ============================================================================
BLUETOOTH_MAX_NAME_SIZE = 248

# Inquiry timeout multipliers: units of 1.28 seconds (Range: 1 to 48 -> 1.28s to 61.44s)
DEFAULT_INQUIRY_TIMEOUT_MULTIPLIER = 10  # 12.8 seconds
MIN_INQUIRY_TIMEOUT_MULTIPLIER = 1
MAX_INQUIRY_TIMEOUT_MULTIPLIER = 48

# ============================================================================
# Major Service Classes (Bits 13 to 23 of CoD - Bitfield)
# ============================================================================
class MajorServiceClass(IntEnum):
    LIMITED_DISCOVERABLE_MODE = 1 << 13
    LE_AUDIO                  = 1 << 14
    RESERVED_15               = 1 << 15
    POSITIONING               = 1 << 16  # Location identification
    NETWORKING                = 1 << 17  # LAN, Ad-hoc
    RENDERING                 = 1 << 18  # Printing, Speaker
    CAPTURING                 = 1 << 19  # Scanner, Microphone
    OBJECT_TRANSFER           = 1 << 20  # v-Card, v-Cal
    AUDIO                     = 1 << 21  # Audio Speaker, Headset service
    TELEPHONY                 = 1 << 22  # Cordless telephony, Modem, Headset
    INFORMATION               = 1 << 23  # Web server, WAP server


# ============================================================================
# Major Device Classes (Bits 8 to 12 of CoD - 5-bit integer)
# ============================================================================
@unique
class MajorDeviceClass(IntEnum):
    MISCELLANEOUS = 0x00
    COMPUTER      = 0x01
    PHONE         = 0x02
    LAN_NETWORK   = 0x03
    AUDIO_VIDEO   = 0x04
    PERIPHERAL    = 0x05
    IMAGING       = 0x06
    WEARABLE      = 0x07
    TOY           = 0x08
    HEALTH        = 0x09
    UNCATEGORIZED = 0x1F


# ============================================================================
# Minor Device Classes (Bits 2 to 7 of CoD)
# ============================================================================

# Computer Minor Classes (Bits 2 to 7 shifted right by 2)
COMPUTER_MINOR_CLASSES = {
    0: "Uncategorized Computer",
    1: "Desktop Workstation",
    2: "Server-class Computer",
    3: "Laptop / Notebook",
    4: "Handheld PC/PDA (Clamshell)",
    5: "Palm-sized PC/PDA",
    6: "Wearable Computer (Watch size)",
    7: "Tablet Computer",
}

# Phone Minor Classes (Bits 2 to 7 shifted right by 2)
PHONE_MINOR_CLASSES = {
    0: "Uncategorized Phone",
    1: "Cellular Phone",
    2: "Cordless Phone",
    3: "Smartphone",
    4: "Wired Modem / Voice Gateway",
    5: "Common ISDN Access",
}

# LAN/Network Access Point Load Factor (Bits 5 to 7)
LAN_LOAD_FACTORS = {
    0: "Fully Available (0% utilized)",
    1: "1% - 17% utilized",
    2: "17% - 33% utilized",
    3: "33% - 50% utilized",
    4: "50% - 67% utilized",
    5: "67% - 83% utilized",
    6: "83% - 99% utilized",
    7: "No Service Available (100% utilized)",
}

# Audio/Video Minor Classes (Bits 2 to 7 shifted right by 2)
AUDIO_VIDEO_MINOR_CLASSES = {
    0: "Uncategorized Audio/Video",
    1: "Wearable Headset Device",
    2: "Hands-free Device",
    3: "Reserved (0x03)",
    4: "Microphone",
    5: "Loudspeaker",
    6: "Headphones",
    7: "Portable Audio Device",
    8: "Car Audio",
    9: "Set-top Box",
    10: "HiFi Audio Device",
    11: "VCR",
    12: "Video Camera",
    13: "Camcorder",
    14: "Video Monitor",
    15: "Video Display and Loudspeaker",
    16: "Video Conferencing",
    17: "Reserved (0x11)",
    18: "Gaming / Toy Audio Device",
}

# Peripheral Minor Classes: Bits 6 & 7 indicate primary type
PERIPHERAL_TYPE_KEYBOARD = 0x10  # Bit 6
PERIPHERAL_TYPE_POINTING = 0x20  # Bit 7
PERIPHERAL_TYPE_COMBO    = 0x30  # Bits 6 & 7

PERIPHERAL_SUBTYPES = {
    0: "Uncategorized",
    1: "Joystick",
    2: "Gamepad",
    3: "Remote Control",
    4: "Sensing Device",
    5: "Digitizer Tablet",
    6: "Card Reader",
    7: "Digital Pen",
    8: "Handheld Barcode Scanner",
    9: "Handheld Gestural Input Device",
}

# Imaging Minor Classes: Bitfield in bits 4 to 7
IMAGING_BIT_DISPLAY = 1 << 4
IMAGING_BIT_CAMERA  = 1 << 5
IMAGING_BIT_SCANNER = 1 << 6
IMAGING_BIT_PRINTER = 1 << 7

# Wearable Minor Classes (Bits 2 to 7 shifted right by 2)
WEARABLE_MINOR_CLASSES = {
    1: "Wristwatch",
    2: "Pager",
    3: "Jacket",
    4: "Helmet",
    5: "Glasses",
}

# Toy Minor Classes (Bits 2 to 7 shifted right by 2)
TOY_MINOR_CLASSES = {
    1: "Robot",
    2: "Vehicle",
    3: "Doll / Action Figure",
    4: "Controller",
    5: "Game",
}

# Health Minor Classes (Bits 2 to 7 shifted right by 2)
HEALTH_MINOR_CLASSES = {
    0: "Undefined Health Device",
    1: "Blood Pressure Monitor",
    2: "Thermometer",
    3: "Weighing Scale",
    4: "Glucose Meter",
    5: "Pulse Oximeter",
    6: "Heart Rate Monitor",
    7: "Health Data Display",
    8: "Step Counter",
    9: "Body Composition Analyzer",
    10: "Peak Flow Monitor",
    11: "Medication Monitor",
    12: "Knee Prosthesis",
    13: "Ankle Prosthesis",
    14: "Generic Health Manager",
    15: "Personal Mobility Device",
}

# ============================================================================
# Bluetooth SIG Recognized Radio Manufacturers
# ============================================================================
RADIO_MANUFACTURERS = {
    0: "Ericsson Technology Licensing",
    1: "Nokia Mobile Phones",
    2: "Intel Corp.",
    3: "IBM Corp.",
    4: "Toshiba Corp.",
    5: "3Com",
    6: "Microsoft",
    7: "Lucent",
    8: "Motorola",
    9: "Infineon Technologies AG",
    10: "Qualcomm Technologies International, Ltd. (CSR)",
    11: "Silicon Wave",
    12: "Digianswer A/S",
    13: "Texas Instruments Inc.",
    14: "Parthus Technologies Inc.",
    15: "Broadcom Corporation",
    18: "Zeevo, Inc.",
    29: "Qualcomm",
    47: "STMicroelectronics",
    76: "Apple, Inc.",
    89: "Nordic Semiconductor ASA",
    117: "Samsung Electronics Co. Ltd.",
    135: "Garmin International, Inc.",
    224: "Google Inc.",
    741: "Espressif Systems (Shanghai) Co., Ltd.",
}