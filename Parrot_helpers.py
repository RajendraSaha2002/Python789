# ============================================================
# helpers.py — Full Utility Functions Library
# Parrot Security OS Dashboard — Pro Edition
# Used by: routes/, services/, app.py
# ============================================================

import os
import re
import json
import hashlib
import secrets
import ipaddress
import subprocess
import platform
import socket
import datetime
import functools
from typing import Any, Optional, Union


# ════════════════════════════════════════════════════════════
# SECTION 1 — RESPONSE HELPERS
# ════════════════════════════════════════════════════════════

def success_response(
    data: Any = None,
    message: str = "Success",
    status: int = 200
) -> dict:
    """
    Standard JSON success response wrapper.
    Usage: return jsonify(success_response(data=my_data))
    """
    return {
        "success": True,
        "message": message,
        "data":    data,
        "status":  status,
    }


def error_response(
    message: str = "An error occurred",
    status:  int = 400,
    details: Any = None
) -> dict:
    """
    Standard JSON error response wrapper.
    Usage: return jsonify(error_response("Not found")), 404
    """
    return {
        "success": False,
        "message": message,
        "details": details,
        "status":  status,
    }


def paginate_list(
    items:    list,
    page:     int = 1,
    per_page: int = 20
) -> dict:
    """
    Paginate a Python list.
    Returns dict with items, total, page, per_page, pages.
    """
    page     = max(1, int(page))
    per_page = max(1, min(int(per_page), 100))
    total    = len(items)
    pages    = max(1, (total + per_page - 1) // per_page)
    start    = (page - 1) * per_page
    end      = start + per_page

    return {
        "items":    items[start:end],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


# ════════════════════════════════════════════════════════════
# SECTION 2 — SECURITY & HASHING HELPERS
# ════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256.
    Returns: hex digest string
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain password against a stored SHA-256 hash.
    Returns: True if match
    """
    return hash_password(plain) == hashed


def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    Usage: token = generate_token(32)
    """
    return secrets.token_hex(length)


def generate_api_key() -> str:
    """
    Generate a formatted API key like: PARROT-XXXX-XXXX-XXXX-XXXX
    """
    parts = [secrets.token_hex(4).upper() for _ in range(4)]
    return "PARROT-" + "-".join(parts)


def sanitize_input(value: str, max_length: int = 255) -> str:
    """
    Remove dangerous characters from user input.
    Strips HTML tags, trims whitespace, limits length.
    """
    if not isinstance(value, str):
        value = str(value)
    # Remove HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    # Remove null bytes
    value = value.replace('\x00', '')
    # Strip and limit
    return value.strip()[:max_length]


def mask_ip(ip: str) -> str:
    """
    Mask last octet of IPv4 for privacy display.
    Example: '192.168.1.100' → '192.168.1.xxx'
    """
    try:
        parts = ip.strip().split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
        return ip
    except Exception:
        return ip


def mask_sensitive(text: str, show: int = 4) -> str:
    """
    Mask sensitive strings like passwords, tokens.
    Example: 'mysecretpass' → 'myse********'
    """
    if not text or len(text) <= show:
        return '*' * len(str(text))
    return str(text)[:show] + '*' * (len(str(text)) - show)


# ════════════════════════════════════════════════════════════
# SECTION 3 — VALIDATION HELPERS
# ════════════════════════════════════════════════════════════

def is_valid_ip(ip: str) -> bool:
    """
    Validate IPv4 or IPv6 address.
    Returns: True if valid IP
    """
    try:
        ipaddress.ip_address(str(ip).strip())
        return True
    except ValueError:
        return False


def is_valid_ipv4(ip: str) -> bool:
    """
    Validate IPv4 address only.
    Returns: True if valid IPv4
    """
    try:
        addr = ipaddress.ip_address(str(ip).strip())
        return addr.version == 4
    except ValueError:
        return False


def is_valid_cidr(cidr: str) -> bool:
    """
    Validate CIDR notation (e.g. 192.168.1.0/24).
    Returns: True if valid CIDR
    """
    try:
        ipaddress.ip_network(str(cidr).strip(), strict=False)
        return True
    except ValueError:
        return False


def is_valid_port(port: Any) -> bool:
    """
    Validate port number (1–65535).
    Returns: True if valid port
    """
    try:
        p = int(port)
        return 1 <= p <= 65535
    except (ValueError, TypeError):
        return False


def is_valid_port_range(start: Any, end: Any) -> bool:
    """
    Validate a port range (start must be <= end).
    Returns: True if both ports are valid and start <= end
    """
    try:
        s = int(start)
        e = int(end)
        return is_valid_port(s) and is_valid_port(e) and s <= e
    except (ValueError, TypeError):
        return False


def is_valid_hostname(hostname: str) -> bool:
    """
    Validate a hostname string.
    Returns: True if valid hostname
    """
    if not hostname or len(hostname) > 253:
        return False
    pattern = re.compile(
        r'^(?!-)[A-Z\d\-]{1,63}(?<!-)$',
        re.IGNORECASE
    )
    return all(pattern.match(part) for part in hostname.split('.'))


def is_valid_username(username: str) -> bool:
    """
    Validate username: 3-50 chars, alphanumeric + underscore.
    Returns: True if valid
    """
    if not isinstance(username, str):
        return False
    return bool(re.match(r'^[a-zA-Z0-9_]{3,50}$', username))


def is_valid_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    Returns: (is_valid: bool, message: str)
    """
    if not isinstance(password, str):
        return False, "Password must be a string."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit."
    return True, "Password is valid."


def is_valid_severity(severity: str) -> bool:
    """
    Validate log/alert severity level.
    Returns: True if valid severity
    """
    valid = {'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
    return str(severity).upper() in valid


def is_valid_role(role: str) -> bool:
    """
    Validate user role.
    Returns: True if valid role
    """
    valid = {'admin', 'analyst', 'viewer'}
    return str(role).lower() in valid


# ════════════════════════════════════════════════════════════
# SECTION 4 — SYSTEM INFO HELPERS
# ════════════════════════════════════════════════════════════

def get_os_info() -> dict:
    """
    Get detailed OS information.
    Returns: dict with os, version, hostname, arch, kernel
    """
    return {
        "os":           platform.system(),
        "os_version":   platform.version(),
        "os_release":   platform.release(),
        "hostname":     platform.node(),
        "arch":         platform.machine(),
        "processor":    platform.processor(),
        "python":       platform.python_version(),
        "platform":     platform.platform(),
    }


def get_local_ip() -> str:
    """
    Get the local machine's primary IP address.
    Returns: IP string or '127.0.0.1' on failure
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def get_hostname() -> str:
    """
    Get the local machine hostname.
    Returns: hostname string
    """
    try:
        return socket.gethostname()
    except Exception:
        return 'unknown'


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Resolve a hostname to an IP address.
    Returns: IP string or None on failure
    """
    try:
        return socket.gethostbyname(hostname.strip())
    except Exception:
        return None


def get_cpu_count() -> int:
    """
    Get the number of CPU cores.
    Returns: int count
    """
    try:
        result = subprocess.run(
            ['nproc'],
            capture_output=True,
            text=True,
            timeout=3
        )
        return int(result.stdout.strip())
    except Exception:
        return os.cpu_count() or 1


def get_uptime() -> dict:
    """
    Get system uptime.
    Returns: dict with uptime_seconds, uptime_str
    """
    try:
        with open('/proc/uptime', 'r') as f:
            seconds = float(f.read().split()[0])

        days    = int(seconds // 86400)
        hours   = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs    = int(seconds % 60)

        parts = []
        if days:    parts.append(f"{days}d")
        if hours:   parts.append(f"{hours}h")
        if minutes: parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return {
            "uptime_seconds": seconds,
            "uptime_str":     " ".join(parts),
            "days":           days,
            "hours":          hours,
            "minutes":        minutes,
        }
    except Exception:
        return {
            "uptime_seconds": 0,
            "uptime_str":     "unknown",
            "days":           0,
            "hours":          0,
            "minutes":        0,
        }


def is_parrot_os() -> bool:
    """
    Check if running on Parrot OS.
    Returns: True if Parrot OS detected
    """
    try:
        with open('/etc/os-release', 'r') as f:
            content = f.read().lower()
        return 'parrot' in content
    except Exception:
        return False


def get_os_release_info() -> dict:
    """
    Parse /etc/os-release for OS details.
    Returns: dict of OS release key-value pairs
    """
    info = {}
    try:
        with open('/etc/os-release', 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, _, val = line.partition('=')
                    info[key.lower()] = val.strip('"').strip("'")
    except Exception:
        info = {"name": platform.system(), "version": platform.release()}
    return info


# ════════════════════════════════════════════════════════════
# SECTION 5 — FILE & LOG HELPERS
# ════════════════════════════════════════════════════════════

def read_file_tail(filepath: str, lines: int = 50) -> list:
    """
    Read the last N lines of a file safely.
    Returns: list of line strings
    """
    try:
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r', errors='ignore') as f:
            all_lines = f.readlines()
        return [line.strip() for line in all_lines[-lines:] if line.strip()]
    except PermissionError:
        return [f"[Permission Denied] Cannot read {filepath}"]
    except Exception as e:
        return [f"[Error] {str(e)}"]


def read_log_file(filepath: str, max_lines: int = 100) -> list:
    """
    Read a log file and return structured log entries.
    Returns: list of dicts with file and line keys
    """
    lines = read_file_tail(filepath, max_lines)
    return [{"file": filepath, "line": line} for line in lines]


def get_system_log_files() -> list:
    """
    Get list of readable system log files on Linux.
    Returns: list of existing log file paths
    """
    candidates = [
        '/var/log/auth.log',
        '/var/log/syslog',
        '/var/log/kern.log',
        '/var/log/dmesg',
        '/var/log/messages',
        '/var/log/secure',
        '/var/log/boot.log',
        '/var/log/dpkg.log',
        '/var/log/apt/history.log',
    ]
    return [f for f in candidates if os.path.exists(f)]


def file_exists_and_readable(filepath: str) -> bool:
    """
    Check if a file exists and is readable.
    Returns: True if file is accessible
    """
    return os.path.isfile(filepath) and os.access(filepath, os.R_OK)


def get_file_size_str(filepath: str) -> str:
    """
    Get human-readable file size string.
    Returns: e.g. '1.23 MB'
    """
    try:
        size = os.path.getsize(filepath)
        return format_bytes(size)
    except Exception:
        return 'unknown'


def format_bytes(byte_count: int) -> str:
    """
    Convert byte count to human-readable string.
    Returns: e.g. '1.23 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if byte_count < 1024.0:
            return f"{byte_count:.2f} {unit}"
        byte_count /= 1024.0
    return f"{byte_count:.2f} PB"


# ════════════════════════════════════════════════════════════
# SECTION 6 — DATE & TIME HELPERS
# ════════════════════════════════════════════════════════════

def now_utc() -> datetime.datetime:
    """Return current UTC datetime."""
    return datetime.datetime.utcnow()


def now_local() -> datetime.datetime:
    """Return current local datetime."""
    return datetime.datetime.now()


def format_datetime(dt: Optional[datetime.datetime] = None) -> str:
    """
    Format datetime to ISO 8601 string.
    Returns: '2026-03-12T14:30:00'
    """
    if dt is None:
        dt = now_utc()
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def format_date(dt: Optional[datetime.datetime] = None) -> str:
    """
    Format datetime to date string.
    Returns: '2026-03-12'
    """
    if dt is None:
        dt = now_utc()
    return dt.strftime('%Y-%m-%d')


def format_time_ago(dt_str: str) -> str:
    """
    Convert a datetime string to 'time ago' format.
    Returns: e.g. '5 minutes ago', '2 hours ago'
    """
    try:
        dt  = datetime.datetime.fromisoformat(str(dt_str))
        now = datetime.datetime.utcnow()
        diff = now - dt

        seconds = int(diff.total_seconds())
        if seconds < 0:
            return "just now"
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"
    except Exception:
        return str(dt_str)


def timestamp_now() -> str:
    """
    Get current timestamp as string.
    Returns: '2026-03-12 14:30:00'
    """
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def is_within_last_hours(dt_str: str, hours: int = 24) -> bool:
    """
    Check if a datetime string is within the last N hours.
    Returns: True if within range
    """
    try:
        dt   = datetime.datetime.fromisoformat(str(dt_str))
        now  = datetime.datetime.utcnow()
        diff = now - dt
        return diff.total_seconds() <= hours * 3600
    except Exception:
        return False


# ════════════════════════════════════════════════════════════
# SECTION 7 — NETWORK HELPERS
# ════════════════════════════════════════════════════════════

def cidr_to_host_list(cidr: str, limit: int = 50) -> list:
    """
    Expand a CIDR notation to a list of host IP strings.
    Returns: list of IP strings (limited to 'limit' hosts)
    """
    try:
        network = ipaddress.ip_network(cidr.strip(), strict=False)
        return [str(ip) for ip in list(network.hosts())[:limit]]
    except Exception:
        return []


def get_network_range(cidr: str) -> dict:
    """
    Get network range info from a CIDR string.
    Returns: dict with network, broadcast, hosts, prefix
    """
    try:
        net = ipaddress.ip_network(cidr.strip(), strict=False)
        return {
            "network":       str(net.network_address),
            "broadcast":     str(net.broadcast_address),
            "netmask":       str(net.netmask),
            "prefix":        net.prefixlen,
            "num_hosts":     net.num_addresses - 2,
            "is_private":    net.is_private,
        }
    except Exception:
        return {}


def is_private_ip(ip: str) -> bool:
    """
    Check if an IP address is in a private range.
    Returns: True if private
    """
    try:
        return ipaddress.ip_address(ip.strip()).is_private
    except Exception:
        return False


def is_loopback_ip(ip: str) -> bool:
    """
    Check if an IP is a loopback address.
    Returns: True if loopback
    """
    try:
        return ipaddress.ip_address(ip.strip()).is_loopback
    except Exception:
        return False


def get_port_service(port: int) -> str:
    """
    Get the common service name for a port number.
    Returns: service name string or 'unknown'
    """
    well_known = {
        20:   'ftp-data',
        21:   'ftp',
        22:   'ssh',
        23:   'telnet',
        25:   'smtp',
        53:   'dns',
        67:   'dhcp',
        68:   'dhcp',
        80:   'http',
        110:  'pop3',
        119:  'nntp',
        123:  'ntp',
        135:  'msrpc',
        139:  'netbios',
        143:  'imap',
        161:  'snmp',
        194:  'irc',
        389:  'ldap',
        443:  'https',
        445:  'smb',
        465:  'smtps',
        514:  'syslog',
        587:  'smtp-alt',
        636:  'ldaps',
        993:  'imaps',
        995:  'pop3s',
        1433: 'mssql',
        1521: 'oracle',
        3306: 'mysql',
        3389: 'rdp',
        4444: 'metasploit',
        5432: 'postgresql',
        5900: 'vnc',
        6379: 'redis',
        6667: 'irc',
        8080: 'http-alt',
        8443: 'https-alt',
        9200: 'elasticsearch',
        27017:'mongodb',
        27018:'mongodb-alt',
    }
    if port in well_known:
        return well_known[port]
    try:
        return socket.getservbyport(port)
    except Exception:
        return 'unknown'


def get_port_risk(port: int) -> str:
    """
    Categorize a port's risk level.
    Returns: 'HIGH', 'MEDIUM', or 'LOW'
    """
    high_risk   = {21, 22, 23, 445, 139, 3389, 4444, 5900}
    medium_risk = {80, 443, 8080, 8443, 3306, 5432, 6379, 1433, 27017, 9200}
    if port in high_risk:
        return 'HIGH'
    if port in medium_risk:
        return 'MEDIUM'
    return 'LOW'


def format_mac_address(mac: str) -> str:
    """
    Format and normalize a MAC address to XX:XX:XX:XX:XX:XX.
    Returns: formatted MAC or original on failure
    """
    try:
        clean = re.sub(r'[^0-9a-fA-F]', '', mac)
        if len(clean) != 12:
            return mac
        return ':'.join(clean[i:i+2] for i in range(0, 12, 2)).upper()
    except Exception:
        return mac


# ════════════════════════════════════════════════════════════
# SECTION 8 — SUBPROCESS / COMMAND HELPERS
# ════════════════════════════════════════════════════════════

def run_command(
    cmd: list,
    timeout: int = 10,
    capture: bool = True
) -> dict:
    """
    Run a system command safely using subprocess.
    Returns: dict with stdout, stderr, returncode, success
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout
        )
        return {
            "success":     result.returncode == 0,
            "returncode":  result.returncode,
            "stdout":      result.stdout.strip() if result.stdout else '',
            "stderr":      result.stderr.strip() if result.stderr else '',
        }
    except subprocess.TimeoutExpired:
        return {
            "success":    False,
            "returncode": -1,
            "stdout":     '',
            "stderr":     f"Command timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "success":    False,
            "returncode": -1,
            "stdout":     '',
            "stderr":     f"Command not found: {cmd[0]}",
        }
    except Exception as e:
        return {
            "success":    False,
            "returncode": -1,
            "stdout":     '',
            "stderr":     str(e),
        }


def command_exists(cmd: str) -> bool:
    """
    Check if a system command exists/is executable.
    Returns: True if command is found
    """
    result = run_command(['which', cmd], timeout=3)
    return result['success']


def ping_host(host: str, count: int = 1) -> bool:
    """
    Ping a host and return True if reachable.
    Returns: True if host responds to ping
    """
    result = run_command(
        ['ping', '-c', str(count), '-W', '1', host],
        timeout=5
    )
    return result['success']


def get_arp_table() -> list:
    """
    Get the system ARP table entries.
    Returns: list of dicts with ip, mac, interface
    """
    result = run_command(['arp', '-n'], timeout=5)
    entries = []
    if result['success']:
        lines = result['stdout'].split('\n')[1:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                entries.append({
                    "ip":        parts[0],
                    "mac":       parts[2],
                    "interface": parts[-1] if len(parts) >= 5 else 'unknown',
                })
    return entries


def get_active_connections() -> list:
    """
    Get active TCP connections using ss or netstat.
    Returns: list of connection strings
    """
    result = run_command(['ss', '-tn'], timeout=5)
    if not result['success']:
        result = run_command(['netstat', '-tn'], timeout=5)
    lines = result['stdout'].split('\n')[1:] if result['success'] else []
    return [line.strip() for line in lines if line.strip()]


def get_listening_ports() -> list:
    """
    Get all listening ports on the system.
    Returns: list of dicts with port, service, protocol
    """
    result = run_command(['ss', '-tlnp'], timeout=5)
    ports  = []
    if result['success']:
        for line in result['stdout'].split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 5:
                local = parts[3]
                try:
                    port_num = int(local.split(':')[-1])
                    ports.append({
                        "port":     port_num,
                        "service":  get_port_service(port_num),
                        "protocol": parts[0],
                        "risk":     get_port_risk(port_num),
                    })
                except (ValueError, IndexError):
                    continue
    return ports


# ════════════════════════════════════════════════════════════
# SECTION 9 — DATA FORMATTING HELPERS
# ════════════════════════════════════════════════════════════

def flatten_dict(
    d:      dict,
    parent: str = '',
    sep:    str = '_'
) -> dict:
    """
    Flatten a nested dictionary to single-level.
    Example: {'a': {'b': 1}} → {'a_b': 1}
    """
    items = {}
    for key, val in d.items():
        new_key = f"{parent}{sep}{key}" if parent else key
        if isinstance(val, dict):
            items.update(flatten_dict(val, new_key, sep))
        else:
            items[new_key] = val
    return items


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int.
    Returns: int or default on failure
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float.
    Returns: float or default on failure
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = '') -> str:
    """
    Safely convert a value to string.
    Returns: string or default on failure
    """
    try:
        return str(value) if value is not None else default
    except Exception:
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a numeric value between min and max.
    Returns: clamped float
    """
    return min(max(float(value), float(min_val)), float(max_val))


def round_percent(value: float, decimals: int = 2) -> float:
    """
    Round a percentage value safely.
    Returns: rounded float between 0.0 and 100.0
    """
    return round(clamp(value, 0.0, 100.0), decimals)


def truncate_string(text: str, max_len: int = 100, suffix: str = '...') -> str:
    """
    Truncate a string to max_len characters.
    Returns: truncated string with suffix if truncated
    """
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix


def to_json_safe(obj: Any) -> Any:
    """
    Convert an object to JSON-serializable format.
    Handles datetime, sets, bytes, custom objects.
    Returns: JSON-safe value
    """
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return str(obj)


def dict_to_json(data: dict, pretty: bool = False) -> str:
    """
    Convert dict to JSON string safely.
    Returns: JSON string
    """
    indent = 2 if pretty else None
    return json.dumps(data, default=to_json_safe, indent=indent)


def parse_json_safe(json_str: str, default: Any = None) -> Any:
    """
    Safely parse a JSON string.
    Returns: parsed object or default on failure
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


# ════════════════════════════════════════════════════════════
# SECTION 10 — DECORATOR HELPERS
# ════════════════════════════════════════════════════════════

def require_session(func):
    """
    Flask route decorator: Require user to be logged in via session.
    Usage: @require_session above any route function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from flask import session, jsonify
        if 'user' not in session:
            return jsonify(error_response(
                "Authentication required", 401
            )), 401
        return func(*args, **kwargs)
    return wrapper


def require_role(*roles):
    """
    Flask route decorator: Require specific user role(s).
    Usage: @require_role('admin') or @require_role('admin', 'analyst')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask import session, jsonify
            user = session.get('user', {})
            if not user:
                return jsonify(error_response(
                    "Authentication required", 401
                )), 401
            if user.get('role') not in roles:
                return jsonify(error_response(
                    f"Role required: {', '.join(roles)}", 403
                )), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator


def handle_errors(func):
    """
    Flask route decorator: Catch all exceptions and return JSON error.
    Usage: @handle_errors above any route function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from flask import jsonify
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[ERROR] {func.__name__}: {e}")
            return jsonify(error_response(
                "Internal server error",
                500,
                str(e)
            )), 500
    return wrapper


def log_request(func):
    """
    Flask route decorator: Log every incoming request.
    Usage: @log_request above any route function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request
        print(
            f"[REQUEST] {request.method} {request.path} "
            f"| IP: {request.remote_addr} "
            f"| {timestamp_now()}"
        )
        return func(*args, **kwargs)
    return wrapper


# ════════════════════════════════════════════════════════════
# SECTION 11 — ALERT & LOG SEVERITY HELPERS
# ════════════════════════════════════════════════════════════

def normalize_severity(severity: str) -> str:
    """
    Normalize severity string to standard uppercase value.
    Returns: 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'
    """
    mapping = {
        'info':     'INFO',
        'warn':     'WARNING',
        'warning':  'WARNING',
        'error':    'ERROR',
        'err':      'ERROR',
        'critical': 'CRITICAL',
        'crit':     'CRITICAL',
        'fatal':    'CRITICAL',
    }
    return mapping.get(str(severity).lower(), 'INFO')


def severity_to_color(severity: str) -> str:
    """
    Map severity to a display color hex code.
    Returns: hex color string
    """
    colors = {
        'INFO':     '#00b4ff',
        'WARNING':  '#ffcc00',
        'ERROR':    '#ff6b6b',
        'CRITICAL': '#ff3366',
        'SUCCESS':  '#00ff88',
    }
    return colors.get(str(severity).upper(), '#7a8ba0')


def severity_to_priority(severity: str) -> int:
    """
    Map severity to numeric priority (higher = more severe).
    Returns: int 1–4
    """
    priority = {
        'INFO':     1,
        'WARNING':  2,
        'ERROR':    3,
        'CRITICAL': 4,
    }
    return priority.get(str(severity).upper(), 1)


def sort_by_severity(items: list, key: str = 'severity') -> list:
    """
    Sort a list of dicts by severity (CRITICAL first).
    Returns: sorted list
    """
    return sorted(
        items,
        key=lambda x: severity_to_priority(x.get(key, 'INFO')),
        reverse=True
    )


# ════════════════════════════════════════════════════════════
# SECTION 12 — ENVIRONMENT & CONFIG HELPERS
# ════════════════════════════════════════════════════════════

def get_env(key: str, default: str = '') -> str:
    """
    Get an environment variable safely.
    Returns: value string or default
    """
    return os.environ.get(key, default)


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get an environment variable as integer.
    Returns: int value or default
    """
    return safe_int(os.environ.get(key, default), default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get an environment variable as boolean.
    Returns: True if value is 'true', '1', or 'yes'
    """
    val = os.environ.get(key, str(default)).lower()
    return val in ('true', '1', 'yes', 'on')


def is_debug_mode() -> bool:
    """
    Check if app is running in debug mode.
    Returns: True if DEBUG env var is set
    """
    return get_env_bool('DEBUG', True)


def is_production() -> bool:
    """
    Check if app is running in production mode.
    Returns: True if FLASK_ENV is 'production'
    """
    return get_env('FLASK_ENV', 'development').lower() == 'production'


# ════════════════════════════════════════════════════════════
# SECTION 13 — QUICK SELF-TEST (run directly to verify)
# python backend/utils/helpers.py
# ════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 60)
    print("  🦜 Parrot OS Dashboard — helpers.py Self-Test")
    print("=" * 60)

    # Security tests
    pw_hash = hash_password("admin123")
    assert verify_password("admin123", pw_hash), "❌ Password verify failed"
    print("✅ hash_password / verify_password")

    token = generate_token(16)
    assert len(token) == 32, "❌ Token length wrong"
    print("✅ generate_token")

    api_key = generate_api_key()
    assert api_key.startswith("PARROT-"), "❌ API key prefix wrong"
    print("✅ generate_api_key")

    # Validation tests
    assert is_valid_ip("192.168.1.1"),       "❌ Valid IP failed"
    assert not is_valid_ip("999.999.1.1"),   "❌ Invalid IP passed"
    assert is_valid_cidr("192.168.1.0/24"),  "❌ Valid CIDR failed"
    assert not is_valid_cidr("not-a-cidr"),  "❌ Invalid CIDR passed"
    assert is_valid_port(80),                "❌ Valid port failed"
    assert not is_valid_port(99999),         "❌ Invalid port passed"
    assert is_valid_username("admin_01"),    "❌ Valid username failed"
    assert not is_valid_username("a"),       "❌ Short username passed"
    print("✅ All validators")

    # Network helpers
    hosts = cidr_to_host_list("192.168.1.0/30")
    assert len(hosts) == 2, f"❌ CIDR expand wrong: {hosts}"
    print("✅ cidr_to_host_list")

    service = get_port_service(22)
    assert service == 'ssh', f"❌ Port service wrong: {service}"
    print("✅ get_port_service")

    risk = get_port_risk(22)
    assert risk == 'HIGH', f"❌ Port risk wrong: {risk}"
    print("✅ get_port_risk")

    # Formatting tests
    fb = format_bytes(1536)
    assert 'KB' in fb, f"❌ format_bytes wrong: {fb}"
    print("✅ format_bytes")

    ts = timestamp_now()
    assert len(ts) > 10, "❌ timestamp_now wrong"
    print("✅ timestamp_now")

    tr = truncate_string("Hello World", max_len=8)
    assert tr == "Hello...", f"❌ truncate_string wrong: {tr}"
    print("✅ truncate_string")

    # Data helpers
    flat = flatten_dict({"a": {"b": {"c": 1}}})
    assert flat == {"a_b_c": 1}, f"❌ flatten_dict wrong: {flat}"
    print("✅ flatten_dict")

    sev = normalize_severity("crit")
    assert sev == "CRITICAL", f"❌ normalize_severity wrong: {sev}"
    print("✅ normalize_severity")

    sorted_items = sort_by_severity([
        {"severity": "INFO"},
        {"severity": "CRITICAL"},
        {"severity": "WARNING"},
    ])
    assert sorted_items[0]["severity"] == "CRITICAL", "❌ sort_by_severity wrong"
    print("✅ sort_by_severity")

    # System info
    ip = get_local_ip()
    assert ip, f"❌ get_local_ip returned empty"
    print(f"✅ get_local_ip → {ip}")

    os_info = get_os_info()
    assert "os" in os_info, "❌ get_os_info missing key"
    print(f"✅ get_os_info → {os_info['os']}")

    print()
    print("=" * 60)
    print("  ✅ ALL TESTS PASSED — helpers.py is working correctly!")
    print("=" * 60)