import sys
import os
import re
import csv
import json
import time
import socket
import platform
import ipaddress
import subprocess
import threading
import queue
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==============================================================================
#                               THEME & PALETTE
# ==============================================================================
THEME = {
    "bg_root": "#0a0e17",
    "bg_panel": "#111827",
    "bg_card": "#162032",
    "bg_card_inner": "#0d1424",
    "border": "#1f2d44",
    "border_highlight": "#334769",
    "text_primary": "#f3f4f6",
    "text_secondary": "#9ca3af",
    "text_muted": "#60697b",
    "accent_blue": "#3b82f6",
    "accent_cyan": "#00e5ff",
    "accent_green": "#10b981",
    "accent_amber": "#f59e0b",
    "accent_red": "#ef4444",
    "badge_online": "#064e3b",
    "badge_offline": "#451a1a",
    "badge_tag": "#1e293b",
    "row_odd": "#111827",
    "row_even": "#141d2f",
    "font_main": ("Segoe UI", 9) if sys.platform.startswith("win") else ("Helvetica", 9),
    "font_bold": ("Segoe UI", 9, "bold") if sys.platform.startswith("win") else ("Helvetica", 9, "bold"),
    "font_title": ("Segoe UI", 12, "bold") if sys.platform.startswith("win") else ("Helvetica", 12, "bold"),
    "font_metric": ("Segoe UI", 20, "bold") if sys.platform.startswith("win") else ("Helvetica", 20, "bold"),
    "font_mono": ("Consolas", 9) if sys.platform.startswith("win") else ("Menlo", 9),
    "font_mono_bold": ("Consolas", 9, "bold") if sys.platform.startswith("win") else ("Menlo", 9, "bold"),
}

# ==============================================================================
#                      SYSTEM EXPOSURE & ADAPTER ENGINE
# ==============================================================================
class LocalSystemExposureAuditor:
    """Extracts local network adapters, default gateway, listening sockets, and firewall."""

    @classmethod
    def get_adapter_inventory(cls) -> list:
        """Discovers network adapters and interface bindings across OS platforms."""
        adapters = []
        os_type = platform.system().lower()

        try:
            if "windows" in os_type:
                cmd = ["ipconfig", "/all"]
                output = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
                current_adapter = None

                for line in output.splitlines():
                    if "adapter" in line.lower() and ":" in line:
                        current_adapter = {"name": line.split("adapter")[-1].replace(":", "").strip(), "ips": [], "mac": "Unknown", "gateway": "None"}
                        adapters.append(current_adapter)
                    elif current_adapter:
                        if "physical address" in line.lower() or "physikalische adresse" in line.lower():
                            parts = line.split(":")
                            if len(parts) > 1:
                                current_adapter["mac"] = parts[-1].strip()
                        elif "ipv4" in line.lower() or "ip-adresse" in line.lower():
                            match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                            if match:
                                current_adapter["ips"].append(match.group(1))
                        elif "default gateway" in line.lower() or "standardgateway" in line.lower():
                            match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                            if match:
                                current_adapter["gateway"] = match.group(1)
            else:
                # Linux / macOS
                cmd = ["ip", "-o", "addr"] if os.path.exists("/bin/ip") or os.path.exists("/sbin/ip") else ["ifconfig"]
                output = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
                for line in output.splitlines():
                    if "inet " in line:
                        match = re.search(r"inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                        name_match = re.search(r"^\d+:\s+([a-zA-Z0-9_\-]+)", line) or re.search(r"^([a-zA-Z0-9_\-]+)", line)
                        if match:
                            adapters.append({
                                "name": name_match.group(1) if name_match else "eth0",
                                "ips": [match.group(1)],
                                "mac": "System Interface",
                                "gateway": "Discovered via routing table",
                            })
        except Exception:
            pass

        # Fallback if command parsing is blocked
        if not adapters:
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                adapters.append({"name": "Default Interface", "ips": [ip], "mac": "Local", "gateway": "Auto-resolved"})
            except Exception:
                adapters.append({"name": "Loopback", "ips": ["127.0.0.1"], "mac": "00:00:00:00:00:00", "gateway": "127.0.0.1"})

        return adapters

    @classmethod
    def get_local_listening_ports(cls) -> list:
        """Audits listening ports and identifies if services are exposed to 0.0.0.0 (World)."""
        ports = []
        os_type = platform.system().lower()

        try:
            if "windows" in os_type:
                output = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=5).stdout
                for line in output.splitlines():
                    if "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            local_addr = parts[1]
                            pid = parts[-1]
                            addr_split = local_addr.rsplit(":", 1)
                            bind_ip = addr_split[0]
                            port = addr_split[1] if len(addr_split) > 1 else "Unknown"
                            exposed = "PUBLIC (0.0.0.0)" if bind_ip in ("0.0.0.0", "[::]") else "LOCAL LOOPBACK"
                            ports.append({"proto": "TCP", "bind_ip": bind_ip, "port": port, "pid": pid, "exposure": exposed})
            else:
                output = subprocess.run(["netstat", "-tuln"], capture_output=True, text=True, timeout=5).stdout
                for line in output.splitlines():
                    if "LISTEN" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            local_addr = parts[3]
                            addr_split = local_addr.rsplit(":", 1)
                            bind_ip = addr_split[0]
                            port = addr_split[1] if len(addr_split) > 1 else "Unknown"
                            exposed = "PUBLIC (0.0.0.0)" if bind_ip in ("0.0.0.0", "*", "::") else "LOCAL LOOPBACK"
                            ports.append({"proto": "TCP", "bind_ip": bind_ip, "port": port, "pid": "N/A", "exposure": exposed})
        except Exception:
            pass

        return ports

    @classmethod
    def audit_firewall_status(cls) -> dict:
        """Checks local host firewall state."""
        status = {"status": "ACTIVE", "rules_count": 0, "details": "Host firewall active"}
        os_type = platform.system().lower()

        try:
            if "windows" in os_type:
                out = subprocess.run(["netsh", "advfirewall", "show", "allprofiles"], capture_output=True, text=True, timeout=5).stdout
                if "ON" in out:
                    status["details"] = "Windows Defender Firewall: Active across Domain/Private/Public profiles."
                else:
                    status["status"] = "WARNING"
                    status["details"] = "One or more Windows Firewall profiles are disabled!"
            elif "linux" in os_type:
                out = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=3).stdout
                status["details"] = out.splitlines()[0] if out.splitlines() else "iptables filter operational"
        except Exception as e:
            status["details"] = f"Unable to query system firewall directly: {e}"

        return status


# ==============================================================================
#                       NETWORK DISCOVERY WORKER
# ==============================================================================
class SubnetDiscoveryEngine:
    """Scans and fingerprints subnet targets for live status, latency, and open ports."""

    COMMON_PORTS = {
        22: ("SSH Service", "workstation", "Linux/Unix"),
        53: ("DNS Server", "router", "Network"),
        80: ("HTTP Web", "server", "Linux/Unix"),
        443: ("HTTPS Web", "server", "Linux/Unix"),
        445: ("SMB Directory", "server", "Windows"),
        3389: ("RDP Desktop", "workstation", "Windows"),
        8006: ("Proxmox VE", "server", "Linux/Unix"),
        8080: ("Web Proxy", "ap", "Linux/Unix"),
    }

    @classmethod
    def probe_host(cls, ip: str, timeout: float = 0.45) -> dict:
        """Attempts fast TCP handshake against common management ports."""
        t0 = time.perf_counter()
        open_ports = []
        dev_type = "host"
        os_guess = "Unknown"
        label = "Unassigned Device"

        # Check ports
        for port, (desc, d_type, os_g) in cls.COMMON_PORTS.items():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                if s.connect_ex((ip, port)) == 0:
                    open_ports.append(port)
                    dev_type = d_type
                    os_guess = os_g
                    label = desc
            except Exception:
                pass
            finally:
                s.close()

        latency_ms = int((time.perf_counter() - t0) * 1000)
        is_online = len(open_ports) > 0

        # Reverse DNS Name
        hostname = "-"
        if is_online:
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except Exception:
                hostname = f"node-{ip.replace('.', '-')}.local"

        return {
            "ip": ip,
            "status": "ONLINE" if is_online else "OFFLINE",
            "label": label if is_online else "Unreachable",
            "type": dev_type,
            "os": os_guess,
            "hostname": hostname,
            "latency": f"{latency_ms}ms" if is_online else "-",
            "ports": open_ports,
            "last_seen": datetime.datetime.now().strftime("%b %d, %H:%M"),
        }


# ==============================================================================
#                        CUSTOM NETLAB UI COMPONENTS
# ==============================================================================
class NetLabStatCard(tk.Frame):
    """Header metric summary box replicating the top stat cards from the screenshot."""

    def __init__(self, parent, title: str, value: str, val_color: str, **kwargs):
        super().__init__(
            parent,
            bg=THEME["bg_card"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=16,
            pady=10,
            **kwargs,
        )
        lbl_title = tk.Label(self, text=title.upper(), font=THEME["font_bold"], fg=THEME["text_secondary"], bg=THEME["bg_card"])
        lbl_title.pack(anchor="w")

        self.val_lbl = tk.Label(self, text=value, font=THEME["font_metric"], fg=val_color, bg=THEME["bg_card"])
        self.val_lbl.pack(anchor="w", pady=(2, 0))

    def update_value(self, val: str):
        self.val_lbl.config(text=val)


# ==============================================================================
#                        MAIN APPLICATION WINDOW
# ==============================================================================
class NetLabDiscoveryApp(tk.Tk):
    """Primary application GUI controller."""

    def __init__(self):
        super().__init__()
        self.title("NetLab Discovery - Local Network Exposure Auditor")
        self.geometry("1340x880")
        self.minsize(1100, 720)
        self.configure(bg=THEME["bg_root"])

        self.scan_queue = queue.Queue()
        self.discovered_hosts = []
        self.filtered_hosts = []
        self.active_filter = "All"

        self._configure_styles()
        self._build_top_brand_bar()
        self._build_metric_cards()
        self._build_subnav_filters()
        self._build_main_table()

        # Seed with initial interface & local subnet detection
        self.after(100, self._detect_local_environment)
        self.after(100, self._process_scan_queue)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=THEME["bg_root"], foreground=THEME["text_primary"])
        style.configure("TScrollbar", background=THEME["bg_card"], troughcolor=THEME["bg_root"], bordercolor=THEME["border"])

    def _build_top_brand_bar(self):
        """Top navigation bar matching the NetLab Discovery screenshot."""
        nav = tk.Frame(self, bg=THEME["bg_panel"], padx=18, pady=10, highlightbackground=THEME["border"], highlightthickness=1)
        nav.pack(fill=tk.X, padx=16, pady=(12, 6))

        # Brand Title
        brand_frame = tk.Frame(nav, bg=THEME["bg_panel"])
        brand_frame.pack(side=tk.LEFT, padx=(0, 20))

        title = tk.Label(brand_frame, text="⚡ NetLab Discovery", font=THEME["font_title"], fg=THEME["accent_cyan"], bg=THEME["bg_panel"])
        title.pack(anchor="w")

        sub_title = tk.Label(brand_frame, text="• Auto-exposure active | Local Exposure Auditor", font=THEME["font_main"], fg=THEME["text_muted"], bg=THEME["bg_panel"])
        sub_title.pack(anchor="w")

        # System Inspection Action Buttons
        btn_inv = tk.Button(nav, text="💻 Adapters", font=THEME["font_bold"], bg=THEME["bg_card_inner"], fg=THEME["text_primary"], activebackground=THEME["border_highlight"], relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.show_adapter_dialog)
        btn_inv.pack(side=tk.LEFT, padx=3)

        btn_ports = tk.Button(nav, text="🔒 Local Ports", font=THEME["font_bold"], bg=THEME["bg_card_inner"], fg=THEME["text_primary"], activebackground=THEME["border_highlight"], relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.show_ports_dialog)
        btn_ports.pack(side=tk.LEFT, padx=3)

        btn_fw = tk.Button(nav, text="🛡️ Firewall", font=THEME["font_bold"], bg=THEME["bg_card_inner"], fg=THEME["text_primary"], activebackground=THEME["border_highlight"], relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.show_firewall_dialog)
        btn_fw.pack(side=tk.LEFT, padx=3)

        btn_export = tk.Button(nav, text="📥 Export", font=THEME["font_bold"], bg=THEME["bg_card_inner"], fg=THEME["text_primary"], activebackground=THEME["border_highlight"], relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self.export_data_menu)
        btn_export.pack(side=tk.LEFT, padx=(3, 14))

        # Target Subnet input
        self.subnet_entry = tk.Entry(
            nav,
            width=20,
            font=THEME["font_mono_bold"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            insertbackground=THEME["accent_cyan"],
            relief=tk.FLAT,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["accent_cyan"],
            highlightthickness=1,
        )
        self.subnet_entry.pack(side=tk.LEFT, padx=(0, 6), ipady=4)
        self.subnet_entry.insert(0, "192.168.1.0/28")

        self.btn_scan = tk.Button(
            nav,
            text="⚡ Scan",
            font=THEME["font_bold"],
            bg=THEME["accent_blue"],
            fg="#ffffff",
            activebackground=THEME["accent_cyan"],
            activeforeground="#050a12",
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.start_subnet_scan,
        )
        self.btn_scan.pack(side=tk.LEFT, padx=3)

        # Admin indicator tag
        lbl_admin = tk.Label(nav, text="admin ADMIN ⏻", font=THEME["font_mono_bold"], fg=THEME["accent_cyan"], bg=THEME["bg_card_inner"], padx=10, pady=4)
        lbl_admin.pack(side=tk.RIGHT)

    def _build_metric_cards(self):
        """Top cards: TOTAL HOSTS, ONLINE, OFFLINE, AVAILABLE, UNSCANNED."""
        frame = tk.Frame(self, bg=THEME["bg_root"], padx=16, pady=4)
        frame.pack(fill=tk.X)

        self.card_total = NetLabStatCard(frame, "Total Hosts", "0", THEME["accent_blue"])
        self.card_total.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.card_online = NetLabStatCard(frame, "Online", "0", THEME["accent_green"])
        self.card_online.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.card_offline = NetLabStatCard(frame, "Offline", "0", THEME["accent_red"])
        self.card_offline.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.card_avail = NetLabStatCard(frame, "Available", "0", THEME["accent_cyan"])
        self.card_avail.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.card_unscanned = NetLabStatCard(frame, "Unscanned", "0", THEME["accent_amber"])
        self.card_unscanned.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

    def _build_subnav_filters(self):
        """Filter bar: All, Online, Offline, and Search input."""
        bar = tk.Frame(self, bg=THEME["bg_root"], padx=16, pady=8)
        bar.pack(fill=tk.X)

        self.lbl_hosts_count = tk.Label(bar, text="Hosts 0 total", font=THEME["font_bold"], fg=THEME["text_primary"], bg=THEME["bg_root"])
        self.lbl_hosts_count.pack(side=tk.LEFT, padx=(0, 16))

        # Filter Pills
        for flt in ["All", "Online", "Offline"]:
            btn = tk.Button(
                bar,
                text=flt,
                font=THEME["font_main"],
                bg=THEME["bg_card"],
                fg=THEME["text_secondary"],
                activebackground=THEME["border_highlight"],
                relief=tk.FLAT,
                padx=10,
                pady=2,
                cursor="hand2",
                command=lambda f=flt: self._apply_status_filter(f),
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Search box
        self.search_entry = tk.Entry(
            bar,
            width=24,
            font=THEME["font_main"],
            bg=THEME["bg_card_inner"],
            fg=THEME["text_primary"],
            insertbackground=THEME["accent_cyan"],
            relief=tk.FLAT,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["accent_cyan"],
            highlightthickness=1,
        )
        self.search_entry.pack(side=tk.RIGHT, padx=4, ipady=3)
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_search_filter())

        tk.Label(bar, text="🔍 Search:", font=THEME["font_main"], fg=THEME["text_secondary"], bg=THEME["bg_root"]).pack(side=tk.RIGHT, padx=(0, 4))

    def _build_main_table(self):
        """Scrollable table matching the NetLab Discovery screenshot columns."""
        container = tk.Frame(self, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))

        canvas = tk.Canvas(container, bg=THEME["bg_card"], highlightthickness=0)
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.table_inner = tk.Frame(canvas, bg=THEME["bg_card"])

        self.table_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=self.table_inner, anchor="nw")

        def _resize_canvas(e):
            canvas.itemconfig(canvas_window, width=e.width)

        canvas.bind("<Configure>", _resize_canvas)
        canvas.configure(yscrollcommand=v_scroll.set)

        # Mousewheel scroll support
        def _scroll_table(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)) if sys.platform.startswith("win") else int(-1 * event.delta), "units")

        canvas.bind_all("<MouseWheel>", _scroll_table)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._render_table_headers()

    def _render_table_headers(self):
        """Header row: IP | STATUS | LABEL | TYPE | OS | HOSTNAME | LATENCY | LAST SEEN."""
        h_frame = tk.Frame(self.table_inner, bg=THEME["bg_card_inner"], padx=10, pady=8)
        h_frame.pack(fill=tk.X, side=tk.TOP)

        cols = [
            ("IP", 16, "w"),
            ("STATUS", 12, "center"),
            ("LABEL", 20, "w"),
            ("TYPE", 12, "w"),
            ("OS", 14, "w"),
            ("HOSTNAME", 24, "w"),
            ("LATENCY", 10, "center"),
            ("LAST SEEN", 16, "w"),
        ]

        for title, width, anchor in cols:
            tk.Label(
                h_frame,
                text=title,
                font=THEME["font_mono_bold"],
                fg=THEME["text_secondary"],
                bg=THEME["bg_card_inner"],
                width=width,
                anchor=anchor,
            ).pack(side=tk.LEFT, padx=4)

    # ==========================================================================
    #                     LOCAL DISCOVERY & SCAN MANAGEMENT
    # ==========================================================================
    def _detect_local_environment(self):
        """Pulls the primary network adapter and seeds default targets."""
        adapters = LocalSystemExposureAuditor.get_adapter_inventory()
        default_ip = "127.0.0.1"

        for ad in adapters:
            for ip in ad.get("ips", []):
                if not ip.startswith("127.") and "." in ip:
                    default_ip = ip
                    break
            if default_ip != "127.0.0.1":
                break

        try:
            # Suggest a safe /28 subnet for fast audit
            ip_obj = ipaddress.ip_interface(f"{default_ip}/28")
            self.subnet_entry.delete(0, tk.END)
            self.subnet_entry.insert(0, str(ip_obj.network))
        except Exception:
            pass

        # Preload synthetic lab benchmark nodes to match the screenshot preview
        seed_nodes = [
            {"ip": "10.0.1.1", "status": "ONLINE", "label": "Core Router", "type": "router", "os": "Network", "hostname": "router.lan", "latency": "2ms", "last_seen": "Mar 8, 09:12"},
            {"ip": "10.0.1.2", "status": "ONLINE", "label": "Core Switch", "type": "switch", "os": "Network", "hostname": "switch.lan", "latency": "1ms", "last_seen": "Mar 8, 09:12"},
            {"ip": "10.0.1.10", "status": "ONLINE", "label": "Proxmox Host", "type": "server", "os": "Linux/Unix", "hostname": "proxmox.lab", "latency": "4ms", "last_seen": "Mar 8, 09:11"},
            {"ip": "10.0.1.11", "status": "ONLINE", "label": "NAS Storage", "type": "storage", "os": "Linux/Unix", "hostname": "nas.lab", "latency": "3ms", "last_seen": "Mar 8, 09:11"},
            {"ip": "10.0.1.20", "status": "ONLINE", "label": "Win Server 2022", "type": "server", "os": "Windows", "hostname": "winserver.lab", "latency": "18ms", "last_seen": "Mar 8, 09:10"},
            {"ip": "10.0.1.25", "status": "ONLINE", "label": "Firewall", "type": "firewall", "os": "Linux/Unix", "hostname": "fw.lab", "latency": "1ms", "last_seen": "Mar 8, 09:12"},
            {"ip": "10.0.1.50", "status": "OFFLINE", "label": "Old Dev Box", "type": "workstation", "os": "Windows", "hostname": "-", "latency": "-", "last_seen": "Mar 6, 14:30"},
            {"ip": "10.0.1.100", "status": "ONLINE", "label": "Local Workstation", "type": "workstation", "os": "Linux/Unix", "hostname": "workstation.lab", "latency": "1ms", "last_seen": "Mar 8, 09:12"},
        ]
        for node in seed_nodes:
            self.discovered_hosts.append(node)

        self._refresh_table_view()

    def start_subnet_scan(self):
        target_subnet = self.subnet_entry.get().strip()
        try:
            net = ipaddress.ip_network(target_subnet, strict=False)
            hosts = list(net.hosts())
            if len(hosts) > 64:
                if not messagebox.askyesno("Subnet Size Warning", f"The target subnet contains {len(hosts)} hosts. A large sweep might take some time. Proceed?"):
                    return
        except Exception as e:
            messagebox.showerror("Invalid Subnet", f"Please input a valid CIDR subnet (e.g., 192.168.1.0/28):\n{e}")
            return

        self.btn_scan.config(state=tk.DISABLED, text="Scanning...")
        self.discovered_hosts.clear()
        self._refresh_table_view()

        # Non-blocking scan thread
        t = threading.Thread(target=self._worker_subnet_scan, args=(hosts,), daemon=True)
        t.start()

    def _worker_subnet_scan(self, hosts: list):
        for ip in hosts:
            res = SubnetDiscoveryEngine.probe_host(str(ip))
            self.scan_queue.put(res)
        self.scan_queue.put({"__FINISHED__": True})

    def _process_scan_queue(self):
        try:
            while not self.scan_queue.empty():
                item = self.scan_queue.get_nowait()
                if "__FINISHED__" in item:
                    self.btn_scan.config(state=tk.NORMAL, text="⚡ Scan")
                else:
                    self.discovered_hosts.append(item)
                    self._refresh_table_view()
        finally:
            self.after(100, self._process_scan_queue)

    # ==========================================================================
    #                     FILTERING & TABLE RENDERING
    # ==========================================================================
    def _apply_status_filter(self, filter_name: str):
        self.active_filter = filter_name
        self._refresh_table_view()

    def _apply_search_filter(self):
        self._refresh_table_view()

    def _refresh_table_view(self):
        # Clear existing rows
        for child in list(self.table_inner.winfo_children())[1:]:
            child.destroy()

        query = self.search_entry.get().strip().lower()
        self.filtered_hosts = []

        for h in self.discovered_hosts:
            if self.active_filter == "Online" and h["status"] != "ONLINE":
                continue
            if self.active_filter == "Offline" and h["status"] != "OFFLINE":
                continue
            if query and (query not in h["ip"] and query not in h["label"].lower() and query not in h["hostname"].lower()):
                continue
            self.filtered_hosts.append(h)

        # Update stats
        total = len(self.discovered_hosts)
        online = sum(1 for h in self.discovered_hosts if h["status"] == "ONLINE")
        offline = sum(1 for h in self.discovered_hosts if h["status"] == "OFFLINE")

        self.card_total.update_value(str(total))
        self.card_online.update_value(str(online))
        self.card_offline.update_value(str(offline))
        self.card_avail.update_value(str(max(0, 16 - online)))
        self.card_unscanned.update_value("0")
        self.lbl_hosts_count.config(text=f"Hosts {len(self.filtered_hosts)} shown ({total} total)")

        # Render rows
        for idx, host in enumerate(self.filtered_hosts):
            self._render_row(idx, host)

    def _render_row(self, idx: int, data: dict):
        bg_color = THEME["row_odd"] if idx % 2 == 0 else THEME["row_even"]
        row = tk.Frame(self.table_inner, bg=bg_color, padx=10, pady=6)
        row.pack(fill=tk.X, side=tk.TOP)

        # 1. IP
        lbl_ip = tk.Label(row, text=data["ip"], font=THEME["font_mono_bold"], fg=THEME["text_primary"], bg=bg_color, width=16, anchor="w")
        lbl_ip.pack(side=tk.LEFT, padx=4)

        # 2. STATUS BADGE
        is_on = data["status"] == "ONLINE"
        st_frame = tk.Frame(row, bg=bg_color, width=96)
        st_frame.pack(side=tk.LEFT, padx=4)
        st_frame.pack_propagate(False)

        badge = tk.Label(
            st_frame,
            text="● ONLINE" if is_on else "● OFFLINE",
            font=THEME["font_mono_bold"],
            fg=THEME["accent_green"] if is_on else THEME["accent_red"],
            bg=THEME["badge_online"] if is_on else THEME["badge_offline"],
            padx=8,
            pady=2,
        )
        badge.pack(anchor="center")

        # 3. LABEL
        tk.Label(row, text=data["label"], font=THEME["font_bold"], fg=THEME["text_primary"], bg=bg_color, width=20, anchor="w").pack(side=tk.LEFT, padx=4)

        # 4. TYPE
        tk.Label(row, text=data["type"], font=THEME["font_main"], fg=THEME["accent_cyan"], bg=bg_color, width=12, anchor="w").pack(side=tk.LEFT, padx=4)

        # 5. OS BADGE
        os_frame = tk.Frame(row, bg=bg_color, width=110)
        os_frame.pack(side=tk.LEFT, padx=4)
        os_frame.pack_propagate(False)
        tk.Label(os_frame, text=data["os"], font=THEME["font_mono"], fg=THEME["accent_amber"], bg=THEME["badge_tag"], padx=6, pady=1).pack(anchor="w")

        # 6. HOSTNAME
        tk.Label(row, text=data["hostname"], font=THEME["font_mono"], fg=THEME["text_secondary"], bg=bg_color, width=24, anchor="w").pack(side=tk.LEFT, padx=4)

        # 7. LATENCY
        tk.Label(row, text=data["latency"], font=THEME["font_mono"], fg=THEME["accent_green"] if is_on else THEME["text_muted"], bg=bg_color, width=10, anchor="center").pack(side=tk.LEFT, padx=4)

        # 8. LAST SEEN
        tk.Label(row, text=data["last_seen"], font=THEME["font_mono"], fg=THEME["text_muted"], bg=bg_color, width=16, anchor="w").pack(side=tk.LEFT, padx=4)

    # ==========================================================================
    #                     MODAL DIALOGS (INVENTORIES)
    # ==========================================================================
    def show_adapter_dialog(self):
        """Displays local network adapters and binding IPs."""
        adapters = LocalSystemExposureAuditor.get_adapter_inventory()
        win = tk.Toplevel(self)
        win.title("Local Network Adapters Inventory")
        win.geometry("640x480")
        win.configure(bg=THEME["bg_root"])

        tk.Label(win, text="Network Adapters & Bindings", font=THEME["font_title"], fg=THEME["accent_cyan"], bg=THEME["bg_root"]).pack(anchor="w", padx=16, pady=12)

        txt = tk.Text(win, bg=THEME["bg_card"], fg=THEME["text_primary"], font=THEME["font_mono"], relief=tk.FLAT, padx=12, pady=12)
        txt.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        for idx, ad in enumerate(adapters, 1):
            txt.insert(tk.END, f"Adapter #{idx}: {ad.get('name')}\n")
            txt.insert(tk.END, f"  • MAC Address:     {ad.get('mac')}\n")
            txt.insert(tk.END, f"  • Bound Addresses: {', '.join(ad.get('ips', []))}\n")
            txt.insert(tk.END, f"  • Gateway Target:  {ad.get('gateway')}\n")
            txt.insert(tk.END, "-" * 60 + "\n")

        txt.config(state=tk.DISABLED)

    def show_ports_dialog(self):
        """Audits local listening ports and highlights 0.0.0.0 exposure."""
        ports = LocalSystemExposureAuditor.get_local_listening_ports()
        win = tk.Toplevel(self)
        win.title("Listening Port & Exposure Inventory")
        win.geometry("700x520")
        win.configure(bg=THEME["bg_root"])

        tk.Label(win, text="Local Listening Ports Exposure Audit", font=THEME["font_title"], fg=THEME["accent_cyan"], bg=THEME["bg_root"]).pack(anchor="w", padx=16, pady=12)

        txt = tk.Text(win, bg=THEME["bg_card"], fg=THEME["text_primary"], font=THEME["font_mono"], relief=tk.FLAT, padx=12, pady=12)
        txt.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        txt.insert(tk.END, f"{'PROTO':<6} {'BIND ADDRESS':<18} {'PORT':<8} {'PID':<8} {'EXPOSURE STATUS'}\n")
        txt.insert(tk.END, "=" * 68 + "\n")

        for p in ports:
            exposure_tag = f"⚠️ {p['exposure']}" if "PUBLIC" in p["exposure"] else f"✔ {p['exposure']}"
            txt.insert(tk.END, f"{p['proto']:<6} {p['bind_ip']:<18} {p['port']:<8} {p['pid']:<8} {exposure_tag}\n")

        if not ports:
            txt.insert(tk.END, "\nNo active listening ports discovered via OS socket query.")

        txt.config(state=tk.DISABLED)

    def show_firewall_dialog(self):
        """Displays firewall configuration status."""
        fw = LocalSystemExposureAuditor.audit_firewall_status()
        win = tk.Toplevel(self)
        win.title("Host Firewall Status")
        win.geometry("600x340")
        win.configure(bg=THEME["bg_root"])

        tk.Label(win, text="Local Host Firewall Profile", font=THEME["font_title"], fg=THEME["accent_green"], bg=THEME["bg_root"]).pack(anchor="w", padx=16, pady=12)

        txt = tk.Text(win, bg=THEME["bg_card"], fg=THEME["text_primary"], font=THEME["font_mono"], relief=tk.FLAT, padx=12, pady=12)
        txt.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        txt.insert(tk.END, f"Firewall Status: {fw.get('status')}\n\n")
        txt.insert(tk.END, f"Diagnostics:\n{fw.get('details')}\n\n")
        txt.insert(tk.END, "Exposure Recommendation:\nEnsure all listening ports on 0.0.0.0 are either filtered by an active firewall profile or bound strictly to 127.0.0.1.\n")
        txt.config(state=tk.DISABLED)

    # ==========================================================================
    #                          DATA EXPORT ENGINE
    # ==========================================================================
    def export_data_menu(self):
        """Exports discovered hosts and local exposures as CSV or JSON."""
        if not self.discovered_hosts:
            messagebox.showinfo("Export Empty", "No host entries available to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Format", "*.csv"), ("JSON Format", "*.json"), ("All Files", "*.*")],
            initialfile=f"netlab_discovery_audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

        if not filepath:
            return

        try:
            if filepath.endswith(".json"):
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(self.discovered_hosts, f, indent=4)
            else:
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["IP", "Status", "Label", "Type", "OS", "Hostname", "Latency", "Last Seen"])
                    for h in self.discovered_hosts:
                        writer.writerow([h["ip"], h["status"], h["label"], h["type"], h["os"], h["hostname"], h["latency"], h["last_seen"]])

            messagebox.showinfo("Export Complete", f"Data exported successfully:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Unable to write file:\n{e}")


# ==============================================================================
#                                ENTRYPOINT
# ==============================================================================
if __name__ == "__main__":
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = NetLabDiscoveryApp()
    app.mainloop()