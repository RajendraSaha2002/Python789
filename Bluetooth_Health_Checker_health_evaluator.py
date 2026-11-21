

from dataclasses import dataclass, field
from typing import List, Dict, Any

from Bluetooth_Health_Checker_adapter_inspector import AdapterHealthRecord
from Bluetooth_Health_Checker_driver_diagnostics import DriverHealthReport, ServiceHealthReport
from Bluetooth_Health_Checker_surrounding_scanner import RfTransceiverTestResult


@dataclass
class HealthCheckItem:
    """Represents an individual diagnostic check rule."""
    category: str
    item_name: str
    passed: bool
    severity: str  # "CRITICAL", "WARNING", "INFO"
    detail: str
    recommendation: str = ""


@dataclass
class OverallHealthReport:
    """Unified health report for the system's Bluetooth subsystem."""
    score_percentage: int
    health_grade: str  # "EXCELLENT", "GOOD", "DEGRADED", "CRITICAL"
    summary_message: str
    adapter_info: AdapterHealthRecord
    driver_info: DriverHealthReport
    service_info: ServiceHealthReport
    rf_test_info: RfTransceiverTestResult
    checklist: List[HealthCheckItem] = field(default_factory=list)
    actionable_recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes health report into a dictionary for JSON output."""
        return {
            "health_score": {
                "score_percentage": self.score_percentage,
                "grade": self.health_grade,
                "summary": self.summary_message,
            },
            "adapter": {
                "name": self.adapter_info.name,
                "mac_address": self.adapter_info.mac_address,
                "manufacturer": self.adapter_info.manufacturer_name,
                "lmp_version": self.adapter_info.lmp_version_major,
                "bluetooth_spec": self.adapter_info.bluetooth_specification,
                "connectable": self.adapter_info.is_connectable,
                "discoverable": self.adapter_info.is_discoverable,
            },
            "driver": {
                "device_name": self.driver_info.device_name,
                "version": self.driver_info.driver_version,
                "date": self.driver_info.driver_date,
                "provider": self.driver_info.driver_provider,
                "pnp_status": self.driver_info.pnp_status,
                "problem_code": self.driver_info.problem_code,
                "problem_description": self.driver_info.problem_description,
            },
            "service": {
                "service_name": self.service_info.service_name,
                "is_running": self.service_info.is_running,
                "state": self.service_info.state_string,
            },
            "rf_transceiver_test": {
                "scan_duration_sec": self.rf_test_info.scan_duration_sec,
                "devices_found": self.rf_test_info.devices_found_count,
                "summary": self.rf_test_info.diagnostic_summary,
                "surrounding_devices": [
                    {
                        "name": d.name,
                        "mac": d.mac_address,
                        "connected": d.is_connected,
                        "paired": d.is_authenticated,
                    }
                    for d in self.rf_test_info.devices
                ],
            },
            "checklist": [
                {
                    "category": item.category,
                    "item": item.item_name,
                    "passed": item.passed,
                    "severity": item.severity,
                    "detail": item.detail,
                    "recommendation": item.recommendation,
                }
                for item in self.checklist
            ],
            "recommendations": self.actionable_recommendations,
        }


class HealthEvaluator:
    """Evaluates rules and builds the final diagnostic report."""

    @classmethod
    def evaluate(
        cls,
        adapter: AdapterHealthRecord,
        driver: DriverHealthReport,
        service: ServiceHealthReport,
        rf_result: RfTransceiverTestResult
    ) -> OverallHealthReport:
        checklist: List[HealthCheckItem] = []
        recommendations: List[str] = []
        score = 100

        # --------------------------------------------------------------------
        # 1. Hardware Presence & MAC
        # --------------------------------------------------------------------
        has_valid_mac = (
            adapter.mac_address
            and adapter.mac_address != "00:00:00:00:00:00"
            and len(adapter.mac_address) == 17
        )
        if has_valid_mac:
            checklist.append(HealthCheckItem(
                category="Hardware",
                item_name="Valid BD_ADDR Hardware Address",
                passed=True,
                severity="INFO",
                detail=f"Adapter MAC is {adapter.mac_address}",
            ))
        else:
            score -= 30
            checklist.append(HealthCheckItem(
                category="Hardware",
                item_name="Valid BD_ADDR Hardware Address",
                passed=False,
                severity="CRITICAL",
                detail="Adapter reports an invalid or uninitialized MAC address.",
                recommendation="Reset the Bluetooth controller via Device Manager or perform a cold reboot.",
            ))
            recommendations.append("Reinitialize the Bluetooth radio: MAC address appears invalid.")

        # --------------------------------------------------------------------
        # 2. Modern Bluetooth Core Spec (BT 4.2+ vs Legacy)
        # --------------------------------------------------------------------
        if adapter.lmp_version_major >= 9:
            # Bluetooth 5.0 or higher
            checklist.append(HealthCheckItem(
                category="Specification",
                item_name="Bluetooth 5.x Modern Core Support",
                passed=True,
                severity="INFO",
                detail=f"{adapter.bluetooth_specification} supported (LMP {adapter.lmp_version_major}).",
            ))
        elif adapter.lmp_version_major >= 6:
            # Bluetooth 4.0 - 4.2
            score -= 10
            checklist.append(HealthCheckItem(
                category="Specification",
                item_name="Bluetooth 5.x Modern Core Support",
                passed=False,
                severity="WARNING",
                detail=f"Adapter is running legacy {adapter.bluetooth_specification}. Bluetooth 5.x features (2M PHY, LE Audio) are unsupported.",
                recommendation="Consider upgrading to a Bluetooth 5.2 or 5.3 USB adapter for faster transfers and LE Audio support.",
            ))
        else:
            # Pre-BLE Bluetooth 2.x/3.x
            score -= 35
            checklist.append(HealthCheckItem(
                category="Specification",
                item_name="Bluetooth Low Energy (BLE) Capability",
                passed=False,
                severity="CRITICAL",
                detail=f"Adapter operates on obsolete {adapter.bluetooth_specification} without BLE.",
                recommendation="Replace legacy Bluetooth adapter. Modern wearables and peripherals require Bluetooth 4.2 or 5.x.",
            ))
            recommendations.append("Hardware is obsolete: Adapter does not support Bluetooth Low Energy (BLE).")

        # --------------------------------------------------------------------
        # 3. PnP Driver Status & Problem Codes
        # --------------------------------------------------------------------
        if driver.is_healthy and driver.problem_code == 0:
            checklist.append(HealthCheckItem(
                category="Driver",
                item_name="Device Manager PnP Driver Status",
                passed=True,
                severity="INFO",
                detail=f"Driver version {driver.driver_version} ({driver.driver_date}) reported healthy.",
            ))
        else:
            score -= 40
            checklist.append(HealthCheckItem(
                category="Driver",
                item_name="Device Manager PnP Driver Status",
                passed=False,
                severity="CRITICAL",
                detail=f"PnP Problem {driver.problem_name}: {driver.problem_description}",
                recommendation=f"Update or reinstall driver from {driver.driver_provider} for '{driver.device_name}'.",
            ))
            recommendations.append(f"Resolve Device Manager Problem: {driver.problem_description}")

        # --------------------------------------------------------------------
        # 4. Windows Bluetooth Support Service (bthserv)
        # --------------------------------------------------------------------
        if service.is_running:
            checklist.append(HealthCheckItem(
                category="OS Service",
                item_name="Bluetooth Support Service (bthserv)",
                passed=True,
                severity="INFO",
                detail="bthserv is running normally.",
            ))
        else:
            score -= 35
            checklist.append(HealthCheckItem(
                category="OS Service",
                item_name="Bluetooth Support Service (bthserv)",
                passed=False,
                severity="CRITICAL",
                detail=f"bthserv status is {service.state_string}. {service.diagnostic_message}",
                recommendation="Start the service: Open cmd as Administrator and execute 'net start bthserv'.",
            ))
            recommendations.append("Windows 'bthserv' service is not running. Execute 'net start bthserv'.")

        # --------------------------------------------------------------------
        # 5. Connectable State
        # --------------------------------------------------------------------
        if adapter.is_connectable:
            checklist.append(HealthCheckItem(
                category="Connectivity",
                item_name="Radio Connectable Mode",
                passed=True,
                severity="INFO",
                detail="Radio is connectable. Paired remote devices can re-establish connections.",
            ))
        else:
            score -= 15
            checklist.append(HealthCheckItem(
                category="Connectivity",
                item_name="Radio Connectable Mode",
                passed=False,
                severity="WARNING",
                detail="Radio is currently NOT connectable. Incoming connection attempts will be rejected.",
                recommendation="Enable Bluetooth in Windows Settings (Win+I -> Bluetooth & devices).",
            ))
            recommendations.append("Adapter is not in connectable mode. Verify Bluetooth toggle is ON in Windows Settings.")

        # --------------------------------------------------------------------
        # 6. Discoverable State
        # --------------------------------------------------------------------
        if adapter.is_discoverable:
            checklist.append(HealthCheckItem(
                category="Connectivity",
                item_name="Radio Discoverability Mode",
                passed=True,
                severity="INFO",
                detail="Radio is discoverable by new surrounding devices.",
            ))
        else:
            # Informational only: discoverable is usually off by default for security
            checklist.append(HealthCheckItem(
                category="Connectivity",
                item_name="Radio Discoverability Mode",
                passed=True,
                severity="INFO",
                detail="Radio is hidden (Non-discoverable). Standard security posture.",
                recommendation="If pairing new devices from the other device's menu, open 'Bluetooth & devices' to broadcast visibility.",
            ))

        # --------------------------------------------------------------------
        # 7. RF Transceiver Verification
        # --------------------------------------------------------------------
        if rf_result.transceiver_functional:
            checklist.append(HealthCheckItem(
                category="RF Hardware",
                item_name="RF Transceiver Active Inquiry",
                passed=True,
                severity="INFO",
                detail=f"RF scan succeeded. {rf_result.devices_found_count} device(s) observed in the RF vicinity.",
            ))
        else:
            score -= 25
            checklist.append(HealthCheckItem(
                category="RF Hardware",
                item_name="RF Transceiver Active Inquiry",
                passed=False,
                severity="CRITICAL",
                detail="RF transceiver failed to complete search query.",
                recommendation="Inspect antenna connection or test USB adapter on another port.",
            ))
            recommendations.append("RF Inquiry failed. Check physical antenna and USB port power.")

        # Normalize score
        final_score = max(0, min(score, 100))

        if final_score >= 90:
            grade = "EXCELLENT"
            summary = "Bluetooth adapter, driver, and system services are completely healthy."
        elif final_score >= 75:
            grade = "GOOD"
            summary = "Bluetooth adapter is operational with minor configuration notices."
        elif final_score >= 50:
            grade = "DEGRADED"
            summary = "Bluetooth adapter is degraded. Connectivity issues are likely."
        else:
            grade = "CRITICAL"
            summary = "Bluetooth subsystem has critical failures preventing normal operation."

        return OverallHealthReport(
            score_percentage=final_score,
            health_grade=grade,
            summary_message=summary,
            adapter_info=adapter,
            driver_info=driver,
            service_info=service,
            rf_test_info=rf_result,
            checklist=checklist,
            actionable_recommendations=recommendations,
        )