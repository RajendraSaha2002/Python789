

# ============================================================================
# Bluetooth Core Specification Versions (LMP / HCI Version Mapping)
# ============================================================================
BLUETOOTH_SPEC_VERSIONS = {
    0:  "Bluetooth 1.0b (Historic)",
    1:  "Bluetooth 1.1",
    2:  "Bluetooth 1.2",
    3:  "Bluetooth 2.0 + EDR",
    4:  "Bluetooth 2.1 + EDR",
    5:  "Bluetooth 3.0 + HS",
    6:  "Bluetooth 4.0 (Bluetooth Low Energy / Smart)",
    7:  "Bluetooth 4.1",
    8:  "Bluetooth 4.2 (LE Data Packet Length Extension)",
    9:  "Bluetooth 5.0 (2x Speed, 4x Range, 8x Broadcast)",
    10: "Bluetooth 5.1 (Direction Finding: AoA / AoD)",
    11: "Bluetooth 5.2 (LE Audio, Isochronous Channels, EATT)",
    12: "Bluetooth 5.3 (Connection Subrating, Periodic Adv)",
    13: "Bluetooth 5.4 (Periodic Adv with Responses - PAwR)",
    14: "Bluetooth 6.0 (Channel Sounding, Frame Space Update)",
}

def get_bluetooth_spec_name(version_number: int) -> str:
    """Returns the commercial Bluetooth version name for a given LMP/HCI version integer."""
    return BLUETOOTH_SPEC_VERSIONS.get(
        version_number,
        f"Bluetooth Core Spec Unknown (LMP/HCI Version {version_number})"
    )


# ============================================================================
# Bluetooth SIG Company Identifiers (Hardware Manufacturers)
# ============================================================================
BLUETOOTH_MANUFACTURERS = {
    0: "Ericsson Technology Licensing",
    1: "Nokia Mobile Phones",
    2: "Intel Corporation",
    3: "IBM Corp.",
    4: "Toshiba Corp.",
    5: "3Com",
    6: "Microsoft Corporation",
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
    19: "Atmel Corporation",
    20: "Mitsubishi Electric Corp.",
    21: "RTX Telecom A/S",
    22: "KC Technology Inc.",
    29: "Qualcomm",
    47: "STMicroelectronics",
    48: "Synopsys, Inc.",
    76: "Apple, Inc.",
    89: "Nordic Semiconductor ASA",
    93: "Realtek Semiconductor Corp.",
    102: "MediaTek, Inc.",
    117: "Samsung Electronics Co. Ltd.",
    135: "Garmin International, Inc.",
    140: "Atheros Communications, Inc.",
    224: "Google Inc.",
    277: "Murata Manufacturing Co., Ltd.",
    388: "Marvell Technology Group Ltd.",
    414: "Cypress Semiconductor",
    741: "Espressif Systems (Shanghai) Co., Ltd.",
    822: "Telink Semiconductor Co. Ltd.",
}

def get_manufacturer_name(manufacturer_id: int) -> str:
    """Resolves a 16-bit Bluetooth SIG Company ID into a manufacturer name."""
    return BLUETOOTH_MANUFACTURERS.get(
        manufacturer_id,
        f"Unknown Manufacturer (ID: 0x{manufacturer_id:04X} / {manufacturer_id})"
    )


# ============================================================================
# Windows Device Manager PnP Problem Codes (CM_PROB_*)
# ============================================================================
PNP_PROBLEM_CODES = {
    0: ("CM_PROB_NONE", "Device is working properly."),
    1: ("CM_PROB_NOT_CONFIGURED", "Device is not configured."),
    10: ("CM_PROB_FAILED_START", "Device cannot start (Code 10). Firmware or driver initialization error."),
    12: ("CM_PROB_NORMAL_CONFLICT", "Device cannot find free resources (Code 12)."),
    14: ("CM_PROB_NEED_RESTART", "Device requires a system restart before it can function (Code 14)."),
    18: ("CM_PROB_REINSTALL", "Device drivers need to be reinstalled (Code 18)."),
    22: ("CM_PROB_DISABLED", "Device is disabled by user or system policy (Code 22)."),
    28: ("CM_PROB_FAILED_INSTALL", "Drivers for this device are not installed (Code 28)."),
    31: ("CM_PROB_FAILED_ADD", "Device is not working properly because Windows cannot load required drivers (Code 31)."),
    43: ("CM_PROB_FAILED_POST_START", "Windows has stopped this device because it reported problems (Code 43). Often indicates USB suspend/hardware state fault."),
    45: ("CM_PROB_DEVICE_NOT_THERE", "Device is not currently connected to the computer (Code 45)."),
    48: ("CM_PROB_DRIVER_BLOCKED", "Software/driver for this device has been blocked from starting (Code 48)."),
}

def get_pnp_problem_description(problem_code: int) -> tuple:
    """Returns a tuple of (ErrorName, Description) for a Windows PnP problem code."""
    return PNP_PROBLEM_CODES.get(
        problem_code,
        (f"CM_PROB_UNKNOWN_{problem_code}", f"Windows reported error code {problem_code}.")
    )


# ============================================================================
# Windows Service State Definitions
# ============================================================================
SERVICE_STOPPED          = 0x00000001
SERVICE_START_PENDING    = 0x00000002
SERVICE_STOP_PENDING     = 0x00000003
SERVICE_RUNNING          = 0x00000004
SERVICE_CONTINUE_PENDING = 0x00000005
SERVICE_PAUSE_PENDING    = 0x00000006
SERVICE_PAUSED           = 0x00000007

SERVICE_STATES = {
    SERVICE_STOPPED: "Stopped",
    SERVICE_START_PENDING: "Start Pending",
    SERVICE_STOP_PENDING: "Stop Pending",
    SERVICE_RUNNING: "Running (Healthy)",
    SERVICE_CONTINUE_PENDING: "Continue Pending",
    SERVICE_PAUSED: "Paused",
}

# Win32 Bluetooth IOCTL Constants
FILE_DEVICE_BLUETOOTH = 0x00000031
METHOD_BUFFERED = 0
FILE_ANY_ACCESS = 0

def CTL_CODE(device_type, function, method, access):
    return (device_type << 16) | (access << 14) | (function << 2) | method

IOCTL_BTH_GET_LOCAL_INFO = CTL_CODE(FILE_DEVICE_BLUETOOTH, 0x00, METHOD_BUFFERED, FILE_ANY_ACCESS)