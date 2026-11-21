

import ctypes
from typing import Optional

# Primitive Windows Types
BOOL = ctypes.c_long
BYTE = ctypes.c_ubyte
WORD = ctypes.c_ushort
DWORD = ctypes.c_ulong
ULONG = ctypes.c_ulong
USHORT = ctypes.c_ushort
ULONGLONG = ctypes.c_ulonglong
WCHAR = ctypes.c_wchar
HANDLE = ctypes.c_void_p
LPCWSTR = ctypes.c_wchar_p


class BLUETOOTH_ADDRESS(ctypes.Union):
    """
    Win32 BLUETOOTH_ADDRESS union matching BluetoothApis.h:
        union {
            BTH_ADDR ullLong;
            BYTE     rgBytes[6];
        };
    """
    _fields_ = [
        ("ullLong", ULONGLONG),
        ("rgBytes", BYTE * 6),
    ]

    def to_string(self) -> str:
        """Returns standard MAC string XX:XX:XX:XX:XX:XX (Little-endian to MSB)."""
        return ":".join(f"{self.rgBytes[i]:02X}" for i in range(5, -1, -1))

    def __str__(self) -> str:
        return self.to_string()


class BLUETOOTH_FIND_RADIO_PARAMS(ctypes.Structure):
    """Parameters for BluetoothFindFirstRadio."""
    _fields_ = [
        ("dwSize", DWORD),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dwSize = ctypes.sizeof(self)


class BLUETOOTH_RADIO_INFO(ctypes.Structure):
    """
    Win32 BLUETOOTH_RADIO_INFO structure:
        DWORD             dwSize;
        BLUETOOTH_ADDRESS address;
        WCHAR             szName[248];
        ULONG             ulClassofDevice;
        USHORT            lmpSubversion;
        USHORT            manufacturer;
    """
    _fields_ = [
        ("dwSize", DWORD),
        ("address", BLUETOOTH_ADDRESS),
        ("szName", WCHAR * 248),
        ("ulClassofDevice", ULONG),
        ("lmpSubversion", USHORT),
        ("manufacturer", USHORT),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dwSize = ctypes.sizeof(self)

    @property
    def name(self) -> str:
        return self.szName.strip("\x00")


class SYSTEMTIME(ctypes.Structure):
    """Win32 SYSTEMTIME representation for timestamps."""
    _fields_ = [
        ("wYear", WORD),
        ("wMonth", WORD),
        ("wDayOfWeek", WORD),
        ("wDay", WORD),
        ("wHour", WORD),
        ("wMinute", WORD),
        ("wSecond", WORD),
        ("wMilliseconds", WORD),
    ]


class BLUETOOTH_DEVICE_SEARCH_PARAMS(ctypes.Structure):
    """Search parameters for surrounding area RF inquiry."""
    _fields_ = [
        ("dwSize", DWORD),
        ("fReturnAuthenticated", BOOL),
        ("fReturnRemembered", BOOL),
        ("fReturnUnknown", BOOL),
        ("fReturnConnected", BOOL),
        ("fIssueInquiry", BOOL),
        ("cTimeoutMultiplier", BYTE),
        ("hRadio", HANDLE),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dwSize = ctypes.sizeof(self)


class BLUETOOTH_DEVICE_INFO(ctypes.Structure):
    """Discovered Bluetooth device representation."""
    _fields_ = [
        ("dwSize", DWORD),
        ("Address", BLUETOOTH_ADDRESS),
        ("ulClassofDevice", ULONG),
        ("fConnected", BOOL),
        ("fRemembered", BOOL),
        ("fAuthenticated", BOOL),
        ("stLastSeen", SYSTEMTIME),
        ("stLastUsed", SYSTEMTIME),
        ("szName", WCHAR * 248),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dwSize = ctypes.sizeof(self)

    @property
    def name(self) -> str:
        return self.szName.strip("\x00")


class SERVICE_STATUS_PROCESS(ctypes.Structure):
    """Win32 SERVICE_STATUS_PROCESS structure for checking Windows Service health."""
    _fields_ = [
        ("dwServiceType", DWORD),
        ("dwCurrentState", DWORD),
        ("dwControlsAccepted", DWORD),
        ("dwWin32ExitCode", DWORD),
        ("dwServiceSpecificExitCode", DWORD),
        ("dwCheckPoint", DWORD),
        ("dwWaitHint", DWORD),
        ("dwProcessId", DWORD),
        ("dwServiceFlags", DWORD),
    ]


# ============================================================================
# Safe Dynamic API Loader
# ============================================================================
try:
    _bt_api = ctypes.windll.BluetoothApis
except Exception:
    _bt_api = ctypes.windll.bthprops

_kernel32 = ctypes.windll.kernel32
_advapi32 = ctypes.windll.advapi32

# BluetoothFindFirstRadio
BluetoothFindFirstRadio = _bt_api.BluetoothFindFirstRadio
BluetoothFindFirstRadio.argtypes = [ctypes.POINTER(BLUETOOTH_FIND_RADIO_PARAMS), ctypes.POINTER(HANDLE)]
BluetoothFindFirstRadio.restype = HANDLE

# BluetoothFindNextRadio
BluetoothFindNextRadio = _bt_api.BluetoothFindNextRadio
BluetoothFindNextRadio.argtypes = [HANDLE, ctypes.POINTER(HANDLE)]
BluetoothFindNextRadio.restype = BOOL

# BluetoothFindRadioClose
BluetoothFindRadioClose = _bt_api.BluetoothFindRadioClose
BluetoothFindRadioClose.argtypes = [HANDLE]
BluetoothFindRadioClose.restype = BOOL

# BluetoothGetRadioInfo
BluetoothGetRadioInfo = _bt_api.BluetoothGetRadioInfo
BluetoothGetRadioInfo.argtypes = [HANDLE, ctypes.POINTER(BLUETOOTH_RADIO_INFO)]
BluetoothGetRadioInfo.restype = DWORD

# BluetoothIsConnectable
BluetoothIsConnectable = _bt_api.BluetoothIsConnectable
BluetoothIsConnectable.argtypes = [HANDLE]
BluetoothIsConnectable.restype = BOOL

# BluetoothIsDiscoverable
BluetoothIsDiscoverable = _bt_api.BluetoothIsDiscoverable
BluetoothIsDiscoverable.argtypes = [HANDLE]
BluetoothIsDiscoverable.restype = BOOL

# Device Discovery APIs
BluetoothFindFirstDevice = _bt_api.BluetoothFindFirstDevice
BluetoothFindFirstDevice.argtypes = [ctypes.POINTER(BLUETOOTH_DEVICE_SEARCH_PARAMS), ctypes.POINTER(BLUETOOTH_DEVICE_INFO)]
BluetoothFindFirstDevice.restype = HANDLE

BluetoothFindNextDevice = _bt_api.BluetoothFindNextDevice
BluetoothFindNextDevice.argtypes = [HANDLE, ctypes.POINTER(BLUETOOTH_DEVICE_INFO)]
BluetoothFindNextDevice.restype = BOOL

BluetoothFindDeviceClose = _bt_api.BluetoothFindDeviceClose
BluetoothFindDeviceClose.argtypes = [HANDLE]
BluetoothFindDeviceClose.restype = BOOL

# Kernel32
CloseHandle = _kernel32.CloseHandle
CloseHandle.argtypes = [HANDLE]
CloseHandle.restype = BOOL

DeviceIoControl = _kernel32.DeviceIoControl
DeviceIoControl.argtypes = [
    HANDLE, DWORD, ctypes.c_void_p, DWORD, ctypes.c_void_p, DWORD,
    ctypes.POINTER(DWORD), ctypes.c_void_p
]
DeviceIoControl.restype = BOOL