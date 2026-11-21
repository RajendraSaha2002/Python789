

import ctypes
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Generator

from Classic_Bluetooth_win_constants import (
    ERROR_SUCCESS,
    ERROR_NO_MORE_ITEMS,
    RADIO_MANUFACTURERS,
    DEFAULT_INQUIRY_TIMEOUT_MULTIPLIER,
)
from Classic_Bluetooth_win_types import (
    HANDLE,
    BLUETOOTH_FIND_RADIO_PARAMS,
    BLUETOOTH_RADIO_INFO,
    BLUETOOTH_DEVICE_SEARCH_PARAMS,
    BLUETOOTH_DEVICE_INFO,
)
from Classic_Bluetooth_api_wrapper import (
    BluetoothFindFirstRadio,
    BluetoothFindNextRadio,
    BluetoothFindRadioClose,
    BluetoothGetRadioInfo,
    BluetoothFindFirstDevice,
    BluetoothFindNextDevice,
    BluetoothFindDeviceClose,
    CloseHandle,
)
from Classic_Bluetooth_cod_decoder import ClassOfDeviceDecoder, DecodedClassOfDevice


@dataclass
class RadioDetails:
    """Represents a local physical or virtual Bluetooth Radio Adapter."""
    name: str
    address: str
    class_of_device: DecodedClassOfDevice
    manufacturer_name: str
    manufacturer_id: int
    lmp_subversion: int
    handle: Optional[int] = None


@dataclass
class DiscoveredBluetoothDevice:
    """Represents a discovered remote Classic Bluetooth device."""
    name: str
    mac_address: str
    class_of_device: DecodedClassOfDevice
    is_authenticated: bool   # Paired with PIN / passkey
    is_remembered: bool      # Stored in registry / bonded
    is_connected: bool       # Currently active link
    last_seen: Optional[datetime]
    last_used: Optional[datetime]

    @property
    def status_summary(self) -> str:
        flags = []
        if self.is_connected:
            flags.append("Connected")
        if self.is_authenticated:
            flags.append("Paired")
        elif self.is_remembered:
            flags.append("Remembered")
        else:
            flags.append("Discovered (New)")
        return ", ".join(flags)


class BluetoothDiscoveryEngine:
    """High-level interface to query Bluetooth hardware and scan for devices."""

    @staticmethod
    def enumerate_radios() -> List[RadioDetails]:
        """Discovers all local Bluetooth radio controllers installed on the system."""
        radios: List[RadioDetails] = []
        find_params = BLUETOOTH_FIND_RADIO_PARAMS()
        h_radio = HANDLE()

        h_find = BluetoothFindFirstRadio(ctypes.byref(find_params), ctypes.byref(h_radio))
        if not h_find:
            return radios

        try:
            more_radios = True
            while more_radios:
                radio_info = BLUETOOTH_RADIO_INFO()
                res = BluetoothGetRadioInfo(h_radio, ctypes.byref(radio_info))
                if res == ERROR_SUCCESS:
                    decoded_cod = ClassOfDeviceDecoder.decode(radio_info.ulClassofDevice)
                    manuf_id = radio_info.manufacturer
                    manuf_name = RADIO_MANUFACTURERS.get(manuf_id, f"Unknown ({manuf_id})")

                    radios.append(
                        RadioDetails(
                            name=radio_info.name or "Generic Bluetooth Adapter",
                            address=radio_info.address.to_string(),
                            class_of_device=decoded_cod,
                            manufacturer_name=manuf_name,
                            manufacturer_id=manuf_id,
                            lmp_subversion=radio_info.lmpSubversion,
                            handle=h_radio.value,
                        )
                    )
                else:
                    CloseHandle(h_radio)

                h_next_radio = HANDLE()
                more_radios = bool(BluetoothFindNextRadio(h_find, ctypes.byref(h_next_radio)))
                if more_radios:
                    h_radio = h_next_radio
        finally:
            BluetoothFindRadioClose(h_find)

        return radios

    @classmethod
    def discover_devices(
        cls,
        issue_inquiry: bool = True,
        return_authenticated: bool = True,
        return_remembered: bool = True,
        return_unknown: bool = True,
        return_connected: bool = True,
        timeout_multiplier: int = DEFAULT_INQUIRY_TIMEOUT_MULTIPLIER,
        radio_handle: Optional[int] = None,
    ) -> Generator[DiscoveredBluetoothDevice, None, None]:
        """
        Executes a Bluetooth Device Discovery search using BluetoothFindFirstDevice.

        Yields DiscoveredBluetoothDevice records dynamically as they are returned.
        """
        search_params = BLUETOOTH_DEVICE_SEARCH_PARAMS()
        search_params.fReturnAuthenticated = int(return_authenticated)
        search_params.fReturnRemembered = int(return_remembered)
        search_params.fReturnUnknown = int(return_unknown)
        search_params.fReturnConnected = int(return_connected)
        search_params.fIssueInquiry = int(issue_inquiry)
        search_params.cTimeoutMultiplier = max(1, min(timeout_multiplier, 48))
        search_params.hRadio = radio_handle

        device_info = BLUETOOTH_DEVICE_INFO()
        h_find = BluetoothFindFirstDevice(ctypes.byref(search_params), ctypes.byref(device_info))

        if not h_find:
            last_err = ctypes.GetLastError()
            if last_err == ERROR_NO_MORE_ITEMS:
                return  # No devices matching the query criteria
            raise ctypes.WinError(last_err)

        try:
            has_next = True
            while has_next:
                name_str = device_info.name
                if not name_str:
                    name_str = "[Unknown Device]"

                yield DiscoveredBluetoothDevice(
                    name=name_str,
                    mac_address=device_info.Address.to_string(),
                    class_of_device=ClassOfDeviceDecoder.decode(device_info.ulClassofDevice),
                    is_authenticated=bool(device_info.fAuthenticated),
                    is_remembered=bool(device_info.fRemembered),
                    is_connected=bool(device_info.fConnected),
                    last_seen=device_info.stLastSeen.to_datetime(),
                    last_used=device_info.stLastUsed.to_datetime(),
                )

                # Reset structure size and query next device
                device_info = BLUETOOTH_DEVICE_INFO()
                has_next = bool(BluetoothFindNextDevice(h_find, ctypes.byref(device_info)))
        finally:
            BluetoothFindDeviceClose(h_find)