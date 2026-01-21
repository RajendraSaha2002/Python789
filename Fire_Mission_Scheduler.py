import tkinter as tk
from tkinter import ttk, messagebox
import heapq
import time
import threading


class FireMission:
    """Represents a single artillery request."""

    def __init__(self, priority, mission_type, target, requester):
        self.priority = priority  # Higher number = higher priority
        self.mission_type = mission_type
        self.target = target
        self.requester = requester
        self.timestamp = time.time()

    # PriorityQueue (heapq) is a min-heap.
    # To make it a max-heap (higher priority first), we use negative priority.
    def __lt__(self, other):
        if self.priority == other.priority:
            return self.timestamp < other.timestamp  # If same priority, older request first
        return self.priority > other.priority


class PrioritySchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Artillery Fire Mission Priority Scheduler")
        self.root.geometry("800x600")
        self.root.configure(bg="#1a1a1a")

        # The Priority Queue (Heap)
        self.mission_queue = []
        self.is_firing = False

        self.setup_ui()

    def setup_ui(self):
        # --- HEADER ---
        header = tk.Frame(self.root, bg="#2d2d2d", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="🔥 TACTICAL FIRE DIRECTION SYSTEM (FDS)",
                 font=("Courier", 18, "bold"), bg="#2d2d2d", fg="#ff4500").pack()

        # --- INPUT PANEL ---
        input_frame = tk.LabelFrame(self.root, text="NEW MISSION REQUEST (ROE)",
                                    bg="#1a1a1a", fg="#aaa", padx=10, pady=10)
        input_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(input_frame, text="Target (Grid):", bg="#1a1a1a", fg="white").grid(row=0, column=0)
        self.target_entry = tk.Entry(input_frame, width=15)
        self.target_entry.insert(0, "GR 123-456")
        self.target_entry.grid(row=0, column=1, padx=5)

        tk.Label(input_frame, text="Requester:", bg="#1a1a1a", fg="white").grid(row=0, column=2)
        self.req_entry = tk.Entry(input_frame, width=15)
        self.req_entry.insert(0, "Eagle-6")
        self.req_entry.grid(row=0, column=3, padx=5)

        tk.Label(input_frame, text="Mission Type:", bg="#1a1a1a", fg="white").grid(row=0, column=4)
        self.type_combo = ttk.Combobox(input_frame, values=[
            "Troops in Contact (P-100)",
            "Building Destruction (P-50)",
            "Harassment Fire (P-10)"
        ], state="readonly", width=25)
        self.type_combo.set("Troops in Contact (P-100)")
        self.type_combo.grid(row=0, column=5, padx=5)

        tk.Button(input_frame, text="QUEUE MISSION", command=self.add_mission,
                  bg="#ff4500", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=6, padx=10)

        # --- STATUS DASHBOARD ---
        status_frame = tk.Frame(self.root, bg="#1a1a1a")
        status_frame.pack(fill="both", expand=True, padx=20)

        # Left: Queue View
        queue_label_frame = tk.LabelFrame(status_frame, text="PENDING FIRE MISSIONS (Sorted by Priority)",
                                          bg="#1a1a1a", fg="#aaa")
        queue_label_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 10))

        cols = ("prio", "type", "target", "unit")
        self.tree = ttk.Treeview(queue_label_frame, columns=cols, show="headings", height=10)
        self.tree.heading("prio", text="Priority")
        self.tree.heading("type", text="Type")
        self.tree.heading("target", text="Target")
        self.tree.heading("unit", text="By")
        self.tree.column("prio", width=70)
        self.tree.pack(fill="both", expand=True)

        # Right: Active Firing
        active_frame = tk.LabelFrame(status_frame, text="BATTERY STATUS", bg="#1a1a1a", fg="#aaa", width=250)
        active_frame.pack(side=tk.RIGHT, fill="both")

        self.status_lbl = tk.Label(active_frame, text="IDLE", font=("Courier", 20, "bold"),
                                   bg="green", fg="white", width=15, pady=20)
        self.status_lbl.pack(pady=20)

        self.fire_btn = tk.Button(active_frame, text="ENGAGE TARGET", command=self.engage_mission,
                                  bg="#444", fg="white", font=("Arial", 12, "bold"), height=2)
        self.fire_btn.pack(fill="x", padx=20)

        self.log_text = tk.Text(active_frame, height=10, bg="black", fg="#0f0", font=("Courier", 8))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def add_mission(self):
        target = self.target_entry.get()
        requester = self.req_entry.get()
        selected_type = self.type_combo.get()

        # Map string to weight
        prio_map = {
            "Troops in Contact (P-100)": 100,
            "Building Destruction (P-50)": 50,
            "Harassment Fire (P-10)": 10
        }
        priority = prio_map[selected_type]

        mission = FireMission(priority, selected_type.split(" (")[0], target, requester)

        # PUSH TO HEAP (Priority Queue)
        heapq.heappush(self.mission_queue, mission)

        self.update_log(f"NEW CALL: {mission.mission_type} at {target}")
        self.refresh_queue_ui()

    def refresh_queue_ui(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # We need a sorted copy to show in UI (Heaps are only partially sorted)
        # Note: In production, we'd use heapq.nsmallest or sorted()
        sorted_list = sorted(self.mission_queue)

        for m in sorted_list:
            self.tree.insert("", tk.END, values=(m.priority, m.mission_type, m.target, m.requester))

    def engage_mission(self):
        if not self.mission_queue:
            messagebox.showinfo("No Targets", "Mission queue is empty.")
            return

        if self.is_firing:
            return

        # POP highest priority from heap
        current_mission = heapq.heappop(self.mission_queue)
        self.refresh_queue_ui()

        # Start threading to prevent UI freeze during firing
        threading.Thread(target=self.fire_sequence, args=(current_mission,), daemon=True).start()

    def fire_sequence(self, mission):
        self.is_firing = True
        self.fire_btn.config(state="disabled")

        self.status_lbl.config(text="FIRING!", bg="red")
        self.update_log(f">>> ENGAGING {mission.target} ({mission.priority} PRIO)")

        # Simulate delay for rounds landing
        for i in range(3, 0, -1):
            self.update_log(f"Splash in {i}...")
            time.sleep(1)

        self.update_log(f"!!! TARGET NEUTRALIZED: {mission.target}")
        self.status_lbl.config(text="IDLE", bg="green")

        self.is_firing = False
        self.fire_btn.config(state="normal")

    def update_log(self, msg):
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = PrioritySchedulerApp(root)
    root.mainloop()