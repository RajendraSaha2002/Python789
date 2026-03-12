# ============================================================
# network_service.py — Network Scanning (native Python sockets)
# No Nmap library — uses raw socket + subprocess
# ============================================================

import socket
import subprocess
import ipaddress
import threading

def scan_port(host, port, open_ports, timeout=1.0):
    """Check if a single port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        if result == 0:
            try:
                service = socket.getservbyport(port)
            except Exception:
                service = "unknown"
            open_ports.append({"port": port, "service": service})
        sock.close()
    except Exception:
        pass

def scan_host(host, port_range=(1, 1024)):
    """Scan a host for open ports using threading."""
    open_ports = []
    threads = []
    for port in range(port_range[0], port_range[1] + 1):
        t = threading.Thread(target=scan_port, args=(host, port, open_ports))
        threads.append(t)
        t.start()
        if len(threads) >= 100:        # Batch size
            for t in threads:
                t.join()
            threads = []
    for t in threads:
        t.join()
    return sorted(open_ports, key=lambda x: x["port"])

def ping_host(host):
    """Ping a host and return True if reachable."""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '1', host],
            capture_output=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False

def get_local_ip():
    """Get local machine IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def scan_network_range(cidr="192.168.1.0/24"):
    """Scan a network range for live hosts."""
    live_hosts = []
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        threads = []
        results = []
        lock = threading.Lock()

        def check_host(ip):
            ip_str = str(ip)
            if ping_host(ip_str):
                with lock:
                    results.append({"ip": ip_str, "status": "up"})

        for ip in list(network.hosts())[:50]:  # Limit to 50 hosts
            t = threading.Thread(target=check_host, args=(ip,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5)

        return results
    except Exception as e:
        return []