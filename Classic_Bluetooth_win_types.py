

import ctypes
from datetime import datetime
from typing import Optional
from Classic_Bluetooth_win_constants import BLUETOOTH_MAX_NAME_SIZE

# Primitive Win32 Type Aliases
BOOL = ctypes.c_long
BYTE = ctypes.c_ubyte
WORD = ctypes.c_ushort
DWORD = ctypes.c_ulong
ULONG = ctypes.c_ulong
USHORT = ctypes.c_ushort
ULONGLONG = ctypes.c_ulonglong
WCHAR = ctypes.c_wchar
HANDLE = ctypes.c_void_p


class BLUETOOTH_ADDRESS(ctypes.Union):
    """
    Win32 BLUETOOTH_ADDRESS:
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
        """
        Converts the 48-bit address to canonical MAC string: XX:XX:XX:XX:XX:XX.
        Windows stores bytes in little-endian order (rgBytes[0] is LSB).
        """
        return ":".join(f"{self.rgBytes[i]:02X}" for i in range(5, -1, -1))

    @classmethod
    def from_string(cls, mac_str: str) -> "BLUETOOTH_ADDRESS":
        """Constructs a BLUETOOTH_ADDRESS instance from a colon-separated MAC string."""
        octets = [int(x, 16) for x in mac_str.strip().split(":")]
        if len(octets) != 6:
            raise ValueError(f"Invalid Bluetooth MAC format: {mac_str}")
        instance = cls()
        for idx, val in enumerate(reversed(octets)):
            instance.rgBytes[idx] = val
        return instance

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        return f"<BLUETOOTH_ADDRESS {self.to_string()}>"


class SYSTEMTIME(ctypes.Structure):
    """
    Win32 SYSTEMTIME:
        WORD wYear;
        WORD wMonth;
        WORD wDayOfWeek;
        WORD wDay;
        WORD wHour;
        WORD wMinute;
        WORD wSecond;
        WORD wMilliseconds;
    """
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

    def to_datetime(self) -> Optional[datetime]:
        """Converts to a Python datetime object, returning None if uninitialized."""
        if self.wYear == 0 or self.wMonth == 0 or self.wDay == 0:
            return None
        try:
            return datetime(
                year=self.wYear,
                month=self.wMonth,
                day=self.wDay,
                hour=self.wHour,
                minute=self.wMinute,
                second=self.wSecond,
                microsecond=self.wMilliseconds * 1000,
            )
        except ValueError:
            return None

    def to_string(self) -> str:
        """Returns ISO formatted string or 'Never'."""
        dt = self.to_datetime()
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "Never"


class BLUETOOTH_FIND_RADIO_PARAMS(ctypes.Structure):
    """
    Win32 BLUETOOTH_FIND_RADIO_PARAMS:
        DWORD dwSize;
    """
    _fields_ = [
        ("dwSize", DWORD),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dwSize = ctypes.sizeof(self)


class BLUETOOTH_RADIO_INFO(ctypes.Structure):
    """
    Win32 BLUETOOTH_RADIO_INFO:
        DWORD dwSize;
        BLUETOOTH_ADDRESS address;
        WCHAR szName[BLUETOOTH_MAX_NAME_SIZE];
        ULONG ulClassofDevice;
        USHORT lmpSubversion;
        USHORT manufacturer;
    """
    _fields_ = [
        ("dwSize", DWORD),
        ("address", BLUETOOTH_ADDRESS),
        ("szName", WCHAR * BLUETOOTH_MAX_NAME_SIZE),
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


class BLUETOOTH_DEVICE_SEARCH_PARAMS(ctypes.Structure):
    """
    Win32 BLUETOOTH_DEVICE_SEARCH_PARAMS:
        DWORD  dwSize;
        BOOL   fReturnAuthenticated;
        BOOL   fReturnRemembered;
        BOOL   fReturnUnknown;
        BOOL   fReturnConnected;
        BOOL   fIssueInquiry;
        UCHAR  cTimeoutMultiplier;
        HANDLE hRadio;
    """
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
    """
    Win32 BLUETOOTH_DEVICE_INFO:
        DWORD             dwSize;
        BLUETOOTH_ADDRESS Address;
        ULONG             ulClassofDevice;
        BOOL              fConnected;
        BOOL              fRemembered;
        BOOL              fAuthenticated;
        SYSTEMTIME        stLastSeen;
        SYSTEMTIME        stLastUsed;
        WCHAR             szName[BLUETOOTH_MAX_NAME_SIZE];
    """
    _fields_ = [
        ("dwSize", DWORD),
        ("Address", BLUETOOTH_ADDRESS),
        ("ulClassofDevice", ULONG),
        ("fConnected", BOOL),
        ("fRemembered", BOOL),
        ("fAuthenticated", BOOL),
        ("stLastSeen", SYSTEMTIME),
        ("stLastUsed", SYSTEMTIME),
        ("szName", WCHAR * BLUETOOTH_MAX_NAME_SIZE),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dwSize = ctypes.sizeof(self)

    @property
    def name(self) -> str:
        return self.szName.strip("\x00")