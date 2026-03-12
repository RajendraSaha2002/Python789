# ============================================================
# system_service.py — Real-time System Monitoring
# Uses only Python built-in + psutil (no external APIs)
# ============================================================

import subprocess
import platform
import os

def get_cpu_info():
    """Get CPU usage using /proc/stat (Linux native)."""
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
        vals = [float(x) for x in line.split()[1:]]
        idle = vals[3]
        total = sum(vals)
        cpu_percent = round((1.0 - idle / total) * 100, 2) if total > 0 else 0
        return cpu_percent
    except Exception:
        return 0.0

def get_ram_info():
    """Get RAM usage from /proc/meminfo."""
    try:
        mem = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mem[parts[0].rstrip(':')] = int(parts[1])
        total = mem.get('MemTotal', 1)
        available = mem.get('MemAvailable', 0)
        used_percent = round(((total - available) / total) * 100, 2)
        return {
            "total_mb": round(total / 1024, 2),
            "used_mb": round((total - available) / 1024, 2),
            "percent": used_percent
        }
    except Exception:
        return {"total_mb": 0, "used_mb": 0, "percent": 0}

def get_disk_info():
    """Get disk usage using os.statvfs."""
    try:
        st = os.statvfs('/')
        total = st.f_blocks * st.f_frsize
        free = st.f_bfree * st.f_frsize
        used = total - free
        percent = round((used / total) * 100, 2) if total > 0 else 0
        return {
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "percent": percent
        }
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "percent": 0}

def get_network_info():
    """Get network stats from /proc/net/dev."""
    try:
        stats = {}
        with open('/proc/net/dev', 'r') as f:
            lines = f.readlines()[2:]
        for line in lines:
            parts = line.split()
            if len(parts) > 9:
                iface = parts[0].rstrip(':')
                stats[iface] = {
                    "recv_mb": round(int(parts[1]) / (1024 * 1024), 2),
                    "sent_mb": round(int(parts[9]) / (1024 * 1024), 2)
                }
        return stats
    except Exception:
        return {}

def get_running_processes():
    """Get top 10 processes by CPU usage."""
    try:
        result = subprocess.run(
            ['ps', 'aux', '--sort=-%cpu'],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')[1:11]  # Top 10
        processes = []
        for line in lines:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                processes.append({
                    "user": parts[0],
                    "pid": parts[1],
                    "cpu": parts[2],
                    "mem": parts[3],
                    "command": parts[10][:50]
                })
        return processes
    except Exception:
        return []

def get_system_summary():
    """Full system summary."""
    return {
        "os": platform.system(),
        "hostname": platform.node(),
        "kernel": platform.release(),
        "arch": platform.machine(),
        "cpu_percent": get_cpu_info(),
        "ram": get_ram_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "processes": get_running_processes()
    }