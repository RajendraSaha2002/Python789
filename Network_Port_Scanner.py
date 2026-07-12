import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class LocalPortScanner:
    def __init__(self, target, start_port, end_port, workers, timeout):
        if target != "127.0.0.1":
            raise ValueError("For safety, this scanner only accepts 127.0.0.1.")

        if not 1 <= start_port <= 65535:
            raise ValueError("Start port must be between 1 and 65535.")

        if not 1 <= end_port <= 65535:
            raise ValueError("End port must be between 1 and 65535.")

        if start_port > end_port:
            raise ValueError("Start port cannot be greater than end port.")

        if not 1 <= workers <= 200:
            raise ValueError("Worker count must be between 1 and 200.")

        if not 0.1 <= timeout <= 10:
            raise ValueError("Timeout must be between 0.1 and 10 seconds.")

        self.target = target
        self.start_port = start_port
        self.end_port = end_port
        self.workers = workers
        self.timeout = timeout
        self.results = []
        self.lock = threading.Lock()

    @staticmethod
    def guess_service(port):
        known_services = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            111: "RPC",
            135: "MSRPC",
            139: "NetBIOS",
            143: "IMAP",
            443: "HTTPS",
            445: "SMB",
            465: "SMTPS",
            587: "SMTP Submission",
            993: "IMAPS",
            995: "POP3S",
            1433: "MSSQL",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            6379: "Redis",
            8000: "HTTP Alternate",
            8080: "HTTP Proxy/Alternate",
            8443: "HTTPS Alternate",
        }

        return known_services.get(port, "Unknown")

    @staticmethod
    def clean_banner(data):
        if not data:
            return ""

        return data.decode(
            "utf-8",
            errors="replace",
        ).replace(
            "\r",
            " "
        ).replace(
            "\n",
            " "
        ).strip()[:500]

    def get_probe(self, port):
        if port in (80, 8000, 8080, 8081, 8888):
            return (
                b"GET / HTTP/1.0\r\n"
                b"Host: 127.0.0.1\r\n"
                b"User-Agent: Local-Port-Scanner\r\n"
                b"Connection: close\r\n\r\n"
            )

        if port in (21,):
            return b""

        if port in (25, 465, 587):
            return b"EHLO localhost\r\n"

        if port in (110,):
            return b"CAPA\r\n"

        if port in (143, 993):
            return b"A001 CAPABILITY\r\n"

        if port in (6379,):
            return b"PING\r\n"

        return b""

    def identify_service(self, port, banner):
        banner_lower = banner.lower()

        if "ssh-" in banner_lower:
            return "SSH"

        if banner_lower.startswith("220") and "ftp" in banner_lower:
            return "FTP"

        if banner_lower.startswith("220") and (
            "smtp" in banner_lower
            or "esmtp" in banner_lower
        ):
            return "SMTP"

        if "http/" in banner_lower:
            return "HTTP"

        if banner_lower.startswith("+ok"):
            return "POP3"

        if "* ok" in banner_lower:
            return "IMAP"

        if "+pong" in banner_lower:
            return "Redis"

        if "mysql" in banner_lower:
            return "MySQL"

        return self.guess_service(port)

    def scan_port(self, port):
        result = {
            "target": self.target,
            "port": port,
            "state": "closed",
            "service": "Unknown",
            "banner": "",
            "error": "",
        }

        try:
            with socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            ) as client:

                client.settimeout(self.timeout)
                connection_status = client.connect_ex(
                    (self.target, port)
                )

                if connection_status != 0:
                    return result

                result["state"] = "open"
                probe = self.get_probe(port)

                try:
                    initial_data = client.recv(1024)
                except socket.timeout:
                    initial_data = b""

                if probe:
                    try:
                        client.sendall(probe)
                    except OSError:
                        pass

                try:
                    response_data = client.recv(2048)
                except socket.timeout:
                    response_data = b""

                all_data = initial_data + response_data
                banner = self.clean_banner(all_data)

                result["banner"] = banner
                result["service"] = self.identify_service(
                    port,
                    banner,
                )

        except socket.gaierror:
            result["error"] = "Address resolution error."

        except ConnectionRefusedError:
            result["state"] = "closed"

        except socket.timeout:
            result["state"] = "filtered_or_timeout"
            result["error"] = "Connection timed out."

        except OSError as error:
            result["error"] = str(error)

        return result

    def run(self):
        ports = range(
            self.start_port,
            self.end_port + 1,
        )

        with ThreadPoolExecutor(
            max_workers=self.workers
        ) as executor:

            futures = {
                executor.submit(self.scan_port, port): port
                for port in ports
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as error:
                    result = {
                        "target": self.target,
                        "port": futures[future],
                        "state": "error",
                        "service": "Unknown",
                        "banner": "",
                        "error": str(error),
                    }

                if result["state"] == "open":
                    with self.lock:
                        self.results.append(result)

        self.results.sort(key=lambda item: item["port"])

        return {
            "target": self.target,
            "port_range": f"{self.start_port}-{self.end_port}",
            "threads": self.workers,
            "timeout_seconds": self.timeout,
            "open_ports": self.results,
            "open_port_count": len(self.results),
        }


def get_integer_input(message, default_value, minimum, maximum):
    value = input(f"{message} [{default_value}]: ").strip()

    if not value:
        return default_value

    try:
        number = int(value)
    except ValueError:
        print(f"Invalid input. Using default value: {default_value}")
        return default_value

    if number < minimum or number > maximum:
        print(
            f"Value must be between {minimum} and {maximum}. "
            f"Using default value: {default_value}"
        )
        return default_value

    return number


def print_report(report):
    print("\n" + "=" * 72)
    print("LOOPBACK TCP PORT SCAN REPORT")
    print("=" * 72)
    print(f"Target:       {report['target']}")
    print(f"Port range:   {report['port_range']}")
    print(f"Threads:      {report['threads']}")
    print(f"Timeout:      {report['timeout_seconds']} seconds")
    print(f"Open ports:   {report['open_port_count']}")

    if not report["open_ports"]:
        print("\nNo open TCP ports found in the selected range.")
        return

    print("\nOpen ports:")
    print("-" * 72)

    for item in report["open_ports"]:
        print(
            f"Port: {item['port']:<5} "
            f"State: {item['state']:<6} "
            f"Service: {item['service']}"
        )

        if item["banner"]:
            print(f"  Banner: {item['banner']}")

        if item["error"]:
            print(f"  Note: {item['error']}")


def main():
    print("=" * 72)
    print("TCP Connect Port Scanner with Service Fingerprinter")
    print("=" * 72)
    print("Safety restriction: only 127.0.0.1 can be scanned.\n")

    target = input("Target IP [127.0.0.1]: ").strip()

    if not target:
        target = "127.0.0.1"

    if target != "127.0.0.1":
        print("Error: This scanner only permits 127.0.0.1.")
        return

    start_port = get_integer_input(
        "Start port",
        1,
        1,
        65535,
    )

    end_port = get_integer_input(
        "End port",
        1024,
        1,
        65535,
    )

    worker_count = get_integer_input(
        "Thread count",
        50,
        1,
        200,
    )

    timeout_milliseconds = get_integer_input(
        "Timeout in milliseconds",
        500,
        100,
        10000,
    )

    try:
        scanner = LocalPortScanner(
            target=target,
            start_port=start_port,
            end_port=end_port,
            workers=worker_count,
            timeout=timeout_milliseconds / 1000,
        )

        print("\nScanning localhost. Please wait...")
        report = scanner.run()
        print_report(report)

    except ValueError as error:
        print(f"Input error: {error}")

    except KeyboardInterrupt:
        print("\nScan cancelled by user.")

    except Exception as error:
        print(f"Unexpected error: {error}")


if __name__ == "__main__":
    main()