import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class SyscallEvent:
    event_id: int
    timestamp_utc: str
    category: str
    syscall: str
    arguments: dict
    return_value: str
    risk_points: int
    description: str


@dataclass
class SandboxReport:
    report_time_utc: str
    sample_name: str
    simulation_only: bool
    event_count: int
    threat_score: int
    threat_level: str
    detected_behaviors: list = field(default_factory=list)
    syscall_trace: list = field(default_factory=list)


class SimulatedSandbox:
    def __init__(self, sample_name):
        self.sample_name = sample_name
        self.events = []
        self.behaviors = set()
        self.threat_score = 0
        self.event_counter = 0

    def log_event(
        self,
        category,
        syscall,
        arguments,
        return_value,
        risk_points,
        description,
        behavior=None,
    ):
        self.event_counter += 1

        event = SyscallEvent(
            event_id=self.event_counter,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            category=category,
            syscall=syscall,
            arguments=arguments,
            return_value=return_value,
            risk_points=risk_points,
            description=description,
        )

        self.events.append(event)
        self.threat_score += risk_points

        if behavior:
            self.behaviors.add(behavior)

        print(
            f"[{event.event_id:02d}] "
            f"{event.category:<10} "
            f"{event.syscall:<20} "
            f"Risk +{event.risk_points}"
        )

    def simulate_file_activity(self):
        self.log_event(
            category="File",
            syscall="NtCreateFile",
            arguments={
                "path": "C:\\Users\\Public\\Documents\\update.tmp",
                "access": "GENERIC_WRITE",
                "disposition": "CREATE_ALWAYS",
            },
            return_value="STATUS_SUCCESS",
            risk_points=3,
            description="Simulated creation of a file in a public directory.",
            behavior="File creation",
        )

        self.log_event(
            category="File",
            syscall="NtWriteFile",
            arguments={
                "path": "C:\\Users\\Public\\Documents\\update.tmp",
                "bytes_written": 4096,
            },
            return_value="STATUS_SUCCESS",
            risk_points=4,
            description="Simulated write of data to a newly created file.",
            behavior="File modification",
        )

        self.log_event(
            category="File",
            syscall="NtReadFile",
            arguments={
                "path": "C:\\Windows\\System32\\drivers\\etc\\hosts",
                "bytes_requested": 2048,
            },
            return_value="STATUS_SUCCESS",
            risk_points=2,
            description="Simulated read of a system configuration file.",
            behavior="System file discovery",
        )

    def simulate_registry_activity(self):
        self.log_event(
            category="Registry",
            syscall="NtOpenKey",
            arguments={
                "key": (
                    "HKCU\\Software\\Microsoft\\Windows\\"
                    "CurrentVersion\\Run"
                ),
                "access": "KEY_READ",
            },
            return_value="STATUS_SUCCESS",
            risk_points=3,
            description="Simulated read of a common persistence registry key.",
            behavior="Persistence location discovery",
        )

        self.log_event(
            category="Registry",
            syscall="NtQueryValueKey",
            arguments={
                "key": (
                    "HKCU\\Software\\Microsoft\\Windows\\"
                    "CurrentVersion\\Run"
                ),
                "value_name": "ExampleApplication",
            },
            return_value="STATUS_OBJECT_NAME_NOT_FOUND",
            risk_points=2,
            description="Simulated query for an autorun registry value.",
            behavior="Registry reconnaissance",
        )

    def simulate_network_activity(self):
        self.log_event(
            category="Network",
            syscall="socket",
            arguments={
                "address_family": "AF_INET",
                "socket_type": "SOCK_STREAM",
                "protocol": "TCP",
            },
            return_value="SIMULATED_SOCKET_HANDLE",
            risk_points=1,
            description="Simulated TCP socket creation.",
            behavior="Network capability",
        )

        self.log_event(
            category="Network",
            syscall="connect",
            arguments={
                "destination": "203.0.113.25",
                "port": 443,
                "protocol": "HTTPS",
            },
            return_value="SIMULATED_CONNECTION_SUCCESS",
            risk_points=6,
            description=(
                "Simulated outbound encrypted connection to a documentation-only "
                "test IP address."
            ),
            behavior="Outbound network connection",
        )

    def simulate_process_activity(self):
        self.log_event(
            category="Process",
            syscall="NtCreateUserProcess",
            arguments={
                "image": "cmd.exe",
                "command_line": "cmd.exe /c simulated_task",
                "parent_process": self.sample_name,
            },
            return_value="SIMULATED_PROCESS_HANDLE",
            risk_points=7,
            description="Simulated child-process creation.",
            behavior="Process spawning",
        )

    def simulate_memory_activity(self):
        self.log_event(
            category="Memory",
            syscall="NtAllocateVirtualMemory",
            arguments={
                "process": "SIMULATED_CURRENT_PROCESS",
                "size_bytes": 8192,
                "protection": "PAGE_READWRITE",
            },
            return_value="STATUS_SUCCESS",
            risk_points=3,
            description="Simulated writable memory allocation.",
            behavior="Memory allocation",
        )

        self.log_event(
            category="Memory",
            syscall="NtProtectVirtualMemory",
            arguments={
                "process": "SIMULATED_CURRENT_PROCESS",
                "old_protection": "PAGE_READWRITE",
                "new_protection": "PAGE_EXECUTE_READ",
            },
            return_value="STATUS_SUCCESS",
            risk_points=8,
            description=(
                "Simulated memory protection change from writable to executable."
            ),
            behavior="Executable memory transition",
        )

    def run_simulation(self):
        print("\nStarting safe simulated behavioral analysis...\n")

        self.simulate_file_activity()
        self.simulate_registry_activity()
        self.simulate_network_activity()
        self.simulate_process_activity()
        self.simulate_memory_activity()

        print("\nSimulation completed.\n")

    def get_threat_level(self):
        if self.threat_score >= 30:
            return "HIGH"

        if self.threat_score >= 15:
            return "MEDIUM"

        if self.threat_score >= 1:
            return "LOW"

        return "NONE"

    def create_report(self):
        return SandboxReport(
            report_time_utc=datetime.now(timezone.utc).isoformat(),
            sample_name=self.sample_name,
            simulation_only=True,
            event_count=len(self.events),
            threat_score=self.threat_score,
            threat_level=self.get_threat_level(),
            detected_behaviors=sorted(self.behaviors),
            syscall_trace=[asdict(event) for event in self.events],
        )


def print_report(report):
    print("=" * 72)
    print("SIMULATED SANDBOX BEHAVIORAL REPORT")
    print("=" * 72)
    print(f"Sample name: {report.sample_name}")
    print(f"Simulation only: {report.simulation_only}")
    print(f"Events logged: {report.event_count}")
    print(f"Threat score: {report.threat_score}")
    print(f"Threat level: {report.threat_level}")

    print("\nDetected behaviors:")

    for behavior in report.detected_behaviors:
        print(f"  - {behavior}")

    print("\nThreat scoring note:")
    print(
        "Higher scores result from combined indicators such as process "
        "creation, outbound connections, persistence-key access, and "
        "executable-memory transitions."
    )


def main():
    print("Sandbox Behavioural Logger (Safe Syscall Simulation)")
    print("-" * 72)

    sample_name = input(
        "Enter simulated sample name [sample.exe]: "
    ).strip()

    if not sample_name:
        sample_name = "sample.exe"

    sandbox = SimulatedSandbox(sample_name)
    sandbox.run_simulation()

    report = sandbox.create_report()
    print_report(report)

    save_report = input("\nSave JSON behavioral report? (y/n): ").strip().lower()

    if save_report == "y":
        filename = "sandbox_behavior_report.json"

        try:
            with open(filename, "w", encoding="utf-8") as file_handle:
                json.dump(
                    asdict(report),
                    file_handle,
                    indent=2,
                )

            print(f"\nReport saved successfully: {filename}")

        except OSError as error:
            print(f"\nCould not save JSON report: {error}")


if __name__ == "__main__":
    main()