

import ctypes
import subprocess
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any

from Bluetooth_Health_Checker_bt_constants import (
    SERVICE_STATES,
    SERVICE_RUNNING,
    get_pnp_problem_description,
)
from Bluetooth_Health_Checker_bt_win32_types import (
    SERVICE_STATUS_PROCESS,
    _advapi32,
)


@dataclass
class ServiceHealthReport:
    """Status of the Windows Bluetooth Support Service (bthserv)."""
    service_name: str
    display_name: str
    is_running: bool
    state_code: int
    state_string: str
    process_id: int
    diagnostic_message: str


@dataclass
class DriverHealthReport:
    """PnP Driver status and hardware health metadata."""
    device_name: str
    hardware_id: str
    driver_version: str
    driver_date: str
    driver_provider: str
    pnp_status: str
    problem_code: int
    problem_name: str
    problem_description: str
    is_healthy: bool


class DriverDiagnostics:
    """Inspects Windows PnP and Service subsystems for Bluetooth adapter health."""

    @classmethod
    def check_bthserv_service(cls) -> ServiceHealthReport:
        """
        Queries the Windows Service Control Manager for 'bthserv' (Bluetooth Support Service).
        Utilizes pure Win32 Advapi32 functions with graceful fallback.
        """
        SC_MANAGER_CONNECT = 0x0001
        SERVICE_QUERY_STATUS = 0x0004
        bthserv_name = "bthserv"

        sch_sc_manager = _advapi32.OpenSCManagerW(None, None, SC_MANAGER_CONNECT)
        if not sch_sc_manager:
            return cls._check_bthserv_fallback()

        try:
            sch_service = _advapi32.OpenServiceW(sch_sc_manager, bthserv_name, SERVICE_QUERY_STATUS)
            if not sch_service:
                return ServiceHealthReport(
                    service_name=bthserv_name,
                    display_name="Bluetooth Support Service",
                    is_running=False,
                    state_code=0,
                    state_string="Service Not Installed / Access Denied",
                    process_id=0,
                    diagnostic_message="Windows Bluetooth Support Service (bthserv) could not be queried.",
                )

            try:
                status_buffer = SERVICE_STATUS_PROCESS()
                bytes_needed = ctypes.c_ulong(0)
                SC_STATUS_PROCESS_INFO = 0

                res = _advapi32.QueryServiceStatusEx(
                    sch_service,
                    SC_STATUS_PROCESS_INFO,
                    ctypes.byref(status_buffer),
                    ctypes.sizeof(status_buffer),
                    ctypes.byref(bytes_needed),
                )

                if res:
                    state = status_buffer.dwCurrentState
                    is_run = (state == SERVICE_RUNNING)
                    state_str = SERVICE_STATES.get(state, f"State {state}")
                    diag = (
                        "Service is operating normally."
                        if is_run
                        else f"Service is {state_str}. Bluetooth radios cannot communicate until bthserv runs."
                    )

                    return ServiceHealthReport(
                        service_name=bthserv_name,
                        display_name="Bluetooth Support Service",
                        is_running=is_run,
                        state_code=state,
                        state_string=state_str,
                        process_id=status_buffer.dwProcessId,
                        diagnostic_message=diag,
                    )
            finally:
                _advapi32.CloseServiceHandle(sch_service)
        finally:
            _advapi32.CloseServiceHandle(sch_sc_manager)

        return cls._check_bthserv_fallback()

    @classmethod
    def _check_bthserv_fallback(cls) -> ServiceHealthReport:
        """Subprocess fallback for querying service status if SCManager API is restricted."""
        try:
            cmd = ["sc", "query", "bthserv"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            output = proc.stdout.upper()
            is_run = "RUNNING" in output
            return ServiceHealthReport(
                service_name="bthserv",
                display_name="Bluetooth Support Service",
                is_running=is_run,
                state_code=4 if is_run else 1,
                state_string="Running" if is_run else "Stopped/Unavailable",
                process_id=0,
                diagnostic_message="Checked via service control query fallback.",
            )
        except Exception:
            return ServiceHealthReport(
                service_name="bthserv",
                display_name="Bluetooth Support Service",
                is_running=False,
                state_code=0,
                state_string="Check Failed",
                process_id=0,
                diagnostic_message="Unable to verify Windows Bluetooth service status.",
            )

    @classmethod
    def get_pnp_driver_info(cls) -> DriverHealthReport:
        """
        Queries Windows CIM / PnP subsystem for Bluetooth Radios to extract driver
        version, driver date, provider, and Device Manager Problem Codes (e.g. Code 10, Code 43).
        """
        ps_script = (
            "$ErrorActionPreference = 'SilentlyContinue'; "
            "$dev = Get-CimInstance -ClassName Win32_PnPEntity | "
            "Where-Object { $_.PNPClass -eq 'Bluetooth' -and $_.Service -match 'BTHUSB|BTHMINI|IBTS|Rtk' } | "
            "Select-Object -First 1 Name, DeviceID, Status, ConfigManagerErrorCode; "
            "if (-not $dev) { "
            "  $dev = Get-CimInstance -ClassName Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Bluetooth' } | Select-Object -First 1 Name, DeviceID, Status, ConfigManagerErrorCode; "
            "} "
            "$drv = $null; "
            "if ($dev) { "
            "  $id = $dev.DeviceID; "
            "  $drv = Get-CimInstance -ClassName Win32_PnPSignedDriver | Where-Object { $_.DeviceID -eq $id } | Select-Object -First 1 DriverVersion, DriverDate, DriverProviderName; "
            "} "
            "[PSCustomObject]@{ Device = $dev; Driver = $drv } | ConvertTo-Json -Compress"
        )

        try:
            cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=12,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )

            raw = proc.stdout.strip()
            if not raw:
                return cls._create_default_driver_report("No PnP Bluetooth records returned.")

            data = json.loads(raw)
            dev_data = data.get("Device") or {}
            drv_data = data.get("Driver") or {}

            prob_code = dev_data.get("ConfigManagerErrorCode", 0) or 0
            prob_name, prob_desc = get_pnp_problem_description(prob_code)

            raw_date = drv_data.get("DriverDate") or "N/A"
            clean_date = raw_date
            if raw_date and len(raw_date) >= 8 and raw_date[:8].isdigit():
                clean_date = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

            return DriverHealthReport(
                device_name=dev_data.get("Name") or "Generic Bluetooth Adapter",
                hardware_id=dev_data.get("DeviceID") or "N/A",
                driver_version=drv_data.get("DriverVersion") or "Standard Windows Driver",
                driver_date=clean_date,
                driver_provider=drv_data.get("DriverProviderName") or "Microsoft / OEM",
                pnp_status=dev_data.get("Status") or "OK",
                problem_code=prob_code,
                problem_name=prob_name,
                problem_description=prob_desc,
                is_healthy=(prob_code == 0),
            )

        except Exception as ex:
            return cls._create_default_driver_report(f"PnP query error: {ex}")

    @staticmethod
    def _create_default_driver_report(err_msg: str) -> DriverHealthReport:
        return DriverHealthReport(
            device_name="Bluetooth Radio Adapter",
            hardware_id="N/A",
            driver_version="N/A",
            driver_date="N/A",
            driver_provider="N/A",
            pnp_status="Unknown",
            problem_code=0,
            problem_name="CM_PROB_NONE",
            problem_description=err_msg,
            is_healthy=True,
        )