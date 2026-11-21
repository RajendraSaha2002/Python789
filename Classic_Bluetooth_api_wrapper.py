

import ctypes
import sys
from typing import Optional
from Classic_Bluetooth_win_constants import ERROR_NO_MORE_ITEMS, ERROR_SUCCESS
from Classic_Bluetooth_win_types import (
    HANDLE,
    BOOL,
    DWORD,
    BLUETOOTH_FIND_RADIO_PARAMS,
    BLUETOOTH_RADIO_INFO,
    BLUETOOTH_DEVICE_SEARCH_PARAMS,
    BLUETOOTH_DEVICE_INFO,
)

if sys.platform != "win32":
    raise OSError("The Classic Bluetooth Windows Discovery Tool is only supported on Windows OS.")

# Load Bluetooth DLL: Try BluetoothApis.dll first (Vista+), fallback to bthprops.cpl
try:
    _bt_dll = ctypes.windll.BluetoothApis
except Exception:
    _bt_dll = ctypes.windll.bthprops

_kernel32 = ctypes.windll.kernel32

# ============================================================================
# API: BluetoothFindFirstRadio
# HBLUETOOTH_RADIO_FIND BluetoothFindFirstRadio(
#     const BLUETOOTH_FIND_RADIO_PARAMS *pbtfrp,
#     HANDLE                            *phRadio
# );
# ============================================================================
BluetoothFindFirstRadio = _bt_dll.BluetoothFindFirstRadio
BluetoothFindFirstRadio.argtypes = [
    ctypes.POINTER(BLUETOOTH_FIND_RADIO_PARAMS),
    ctypes.POINTER(HANDLE),
]
BluetoothFindFirstRadio.restype = HANDLE

# ============================================================================
# API: BluetoothFindNextRadio
# BOOL BluetoothFindNextRadio(
#     HBLUETOOTH_RADIO_FIND hFind,
#     HANDLE                *phRadio
# );
# ============================================================================
BluetoothFindNextRadio = _bt_dll.BluetoothFindNextRadio
BluetoothFindNextRadio.argtypes = [
    HANDLE,
    ctypes.POINTER(HANDLE),
]
BluetoothFindNextRadio.restype = BOOL

# ============================================================================
# API: BluetoothFindRadioClose
# BOOL BluetoothFindRadioClose(
#     HBLUETOOTH_RADIO_FIND hFind
# );
# ============================================================================
BluetoothFindRadioClose = _bt_dll.BluetoothFindRadioClose
BluetoothFindRadioClose.argtypes = [HANDLE]
BluetoothFindRadioClose.restype = BOOL

# ============================================================================
# API: BluetoothGetRadioInfo
# DWORD BluetoothGetRadioInfo(
#     HANDLE                hRadio,
#     PBLUETOOTH_RADIO_INFO pRadioInfo
# );
# ============================================================================
BluetoothGetRadioInfo = _bt_dll.BluetoothGetRadioInfo
BluetoothGetRadioInfo.argtypes = [
    HANDLE,
    ctypes.POINTER(BLUETOOTH_RADIO_INFO),
]
BluetoothGetRadioInfo.restype = DWORD

# ============================================================================
# API: BluetoothFindFirstDevice
# HBLUETOOTH_DEVICE_FIND BluetoothFindFirstDevice(
#     const BLUETOOTH_DEVICE_SEARCH_PARAMS *pbtsp,
#     BLUETOOTH_DEVICE_INFO                *pbtdi
# );
# ============================================================================
BluetoothFindFirstDevice = _bt_dll.BluetoothFindFirstDevice
BluetoothFindFirstDevice.argtypes = [
    ctypes.POINTER(BLUETOOTH_DEVICE_SEARCH_PARAMS),
    ctypes.POINTER(BLUETOOTH_DEVICE_INFO),
]
BluetoothFindFirstDevice.restype = HANDLE

# ============================================================================
# API: BluetoothFindNextDevice
# BOOL BluetoothFindNextDevice(
#     HBLUETOOTH_DEVICE_FIND hFind,
#     BLUETOOTH_DEVICE_INFO  *pbtdi
# );
# ============================================================================
BluetoothFindNextDevice = _bt_dll.BluetoothFindNextDevice
BluetoothFindNextDevice.argtypes = [
    HANDLE,
    ctypes.POINTER(BLUETOOTH_DEVICE_INFO),
]
BluetoothFindNextDevice.restype = BOOL

# ============================================================================
# API: BluetoothFindDeviceClose
# BOOL BluetoothFindDeviceClose(
#     HBLUETOOTH_DEVICE_FIND hFind
# );
# ============================================================================
BluetoothFindDeviceClose = _bt_dll.BluetoothFindDeviceClose
BluetoothFindDeviceClose.argtypes = [HANDLE]
BluetoothFindDeviceClose.restype = BOOL

# ============================================================================
# API: CloseHandle (kernel32)
# BOOL CloseHandle(HANDLE hObject);
# ============================================================================
CloseHandle = _kernel32.CloseHandle
CloseHandle.argtypes = [HANDLE]
CloseHandle.restype = BOOL


class SafeRadioHandle:
    """RAII wrapper ensuring Win32 Radio handles are reliably closed."""
    def __init__(self, handle: Optional[int]):
        self.handle = handle

    def close(self):
        if self.handle:
            CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self.handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()