

import ctypes
from dataclasses import dataclass
from typing import List, Optional

from Bluetooth_Health_Checker_bt_constants import (
    get_bluetooth_spec_name,
    get_manufacturer_name,
    IOCTL_BTH_GET_LOCAL_INFO,
)
from Bluetooth_Health_Checker_bt_win32_types import (
    HANDLE,
    DWORD,
    BLUETOOTH_FIND_RADIO_PARAMS,
    BLUETOOTH_RADIO_INFO,
    BluetoothFindFirstRadio,
    BluetoothFindNextRadio,
    BluetoothFindRadioClose,
    BluetoothGetRadioInfo,
    BluetoothIsConnectable,
    BluetoothIsDiscoverable,
    DeviceIoControl,
    CloseHandle,
)


@dataclass
class AdapterHealthRecord:
    """Hardware configuration and radio state parameters."""
    adapter_index: int
    name: str
    mac_address: str
    manufacturer_id: int
    manufacturer_name: str
    lmp_subversion: int
    lmp_version_major: int
    bluetooth_specification: str
    is_connectable: bool
    is_discoverable: bool
    handle_value: Optional[int]


class AdapterInspector:
    """Interrogates physical and virtual Bluetooth radios on Windows."""

    @classmethod
    def query_all_adapters(cls) -> List[AdapterHealthRecord]:
        """Discovers all local Bluetooth radios and collects their operational health states."""
        adapters: List[AdapterHealthRecord] = []
        find_params = BLUETOOTH_FIND_RADIO_PARAMS()
        h_radio = HANDLE()

        h_find = BluetoothFindFirstRadio(ctypes.byref(find_params), ctypes.byref(h_radio))
        if not h_find:
            return adapters

        index = 0
        try:
            more_radios = True
            while more_radios:
                record = cls._inspect_single_radio(index, h_radio)
                if record:
                    adapters.append(record)
                    index += 1

                h_next_radio = HANDLE()
                more_radios = bool(BluetoothFindNextRadio(h_find, ctypes.byref(h_next_radio)))
                if more_radios:
                    h_radio = h_next_radio
        finally:
            BluetoothFindRadioClose(h_find)

        return adapters

    @classmethod
    def _inspect_single_radio(cls, index: int, h_radio: HANDLE) -> Optional[AdapterHealthRecord]:
        """Extracts radio details from a single open radio handle."""
        radio_info = BLUETOOTH_RADIO_INFO()
        res = BluetoothGetRadioInfo(h_radio, ctypes.byref(radio_info))
        if res != 0:
            CloseHandle(h_radio)
            return None

        # Determine Connectable and Discoverable states
        connectable = bool(BluetoothIsConnectable(h_radio))
        discoverable = bool(BluetoothIsDiscoverable(h_radio))

        mfg_id = radio_info.manufacturer
        mfg_name = get_manufacturer_name(mfg_id)
        lmp_sub = radio_info.lmpSubversion

        # Query LMP/HCI version via IOCTL or LMP subversion mapping
        lmp_major = cls._query_lmp_major_version(h_radio, mfg_id, lmp_sub)
        spec_name = get_bluetooth_spec_name(lmp_major)

        record = AdapterHealthRecord(
            adapter_index=index,
            name=radio_info.name or f"Bluetooth Adapter {index}",
            mac_address=radio_info.address.to_string(),
            manufacturer_id=mfg_id,
            manufacturer_name=mfg_name,
            lmp_subversion=lmp_sub,
            lmp_version_major=lmp_major,
            bluetooth_specification=spec_name,
            is_connectable=connectable,
            is_discoverable=discoverable,
            handle_value=h_radio.value,
        )

        return record

    @classmethod
    def _query_lmp_major_version(cls, h_radio: HANDLE, mfg_id: int, lmp_sub: int) -> int:
        """
        Attempts to read hardware LMP Major Version using IOCTL_BTH_GET_LOCAL_INFO.
        Falls back to subversion/manufacturer heuristic tables if DeviceIoControl is restricted.
        """
        # Buffer for BTH_LOCAL_RADIO_INFO: size is 276 bytes
        in_out_buf = (ctypes.c_ubyte * 512)()
        bytes_returned = DWORD(0)

        success = DeviceIoControl(
            h_radio,
            IOCTL_BTH_GET_LOCAL_INFO,
            None,
            0,
            ctypes.byref(in_out_buf),
            ctypes.sizeof(in_out_buf),
            ctypes.byref(bytes_returned),
            None,
        )

        if success and bytes_returned.value >= 270:
            # LMP Version byte is at offset 275 in standard BTH_LOCAL_RADIO_INFO
            lmp_major = in_out_buf[275]
            if 0 < lmp_major <= 14:
                return lmp_major

        # Heuristic fallback based on LMP Subversion and Vendor
        return cls._estimate_lmp_from_subversion(mfg_id, lmp_sub)

    @staticmethod
    def _estimate_lmp_from_subversion(mfg_id: int, lmp_sub: int) -> int:
        """
        Correlates LMP subversion with known vendor release baselines.
        Intel, Realtek, Broadcom, and Qualcomm maintain monotonic subversion thresholds.
        """
        # Intel (Mfg ID 2)
        if mfg_id == 2:
            if lmp_sub >= 0x3000:
                return 12  # BT 5.3 (Intel AX211, BE200)
            if lmp_sub >= 0x2500:
                return 11  # BT 5.2 (Intel AX200/AX201)
            if lmp_sub >= 0x2000:
                return 9   # BT 5.0 (Intel 9260/9560)
            if lmp_sub >= 0x1000:
                return 8   # BT 4.2 (Intel 8265)
            return 6       # BT 4.0

        # Realtek (Mfg ID 93)
        if mfg_id == 93:
            if lmp_sub >= 0x8852:
                return 12  # BT 5.3 (RTL8852CE)
            if lmp_sub >= 0x8822:
                return 11  # BT 5.2 (RTL8822CE)
            if lmp_sub >= 0x0C00:
                return 9   # BT 5.0
            return 8       # BT 4.2

        # Broadcom / Cypress (Mfg ID 15 / 414)
        if mfg_id in (15, 414):
            if lmp_sub >= 0x6000:
                return 11  # BT 5.2
            if lmp_sub >= 0x4000:
                return 9   # BT 5.0
            if lmp_sub >= 0x2000:
                return 8   # BT 4.2
            return 6       # BT 4.0

        # Generic Default for Modern Windows 11 Systems
        if lmp_sub > 0x1000:
            return 11  # Bluetooth 5.2
        return 8       # Bluetooth 4.2