import customtkinter as ctk
import threading
import time
import random
from datetime import datetime

# --- Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Priorities (Lower number = Higher Priority)
PRIORITY_EMERGENCY = 1
PRIORITY_LOW_FUEL = 2
PRIORITY_MISSION = 3
PRIORITY_ROUTINE = 4


class Aircraft:
    def __init__(self, callsign, fuel, status_type):
        self.callsign = callsign
        self.fuel = int(fuel)  # Percentage
        self.status_type = status_type  # "Routine", "Mission", "Emergency"
        self.entry_time = datetime.now()
        self.id = random.randint(1000, 9999)
        self.update_priority()

    def update_priority(self):
        """
        Calculates Priority Score based on rules.
        """
        # Rule 1: Emergency overrides everything
        if self.status_type == "Emergency":
            self.priority_code = PRIORITY_EMERGENCY
            self.status_display = "MAYDAY / EMERGENCY"
            self.color = "#FF3333"  # Red

        # Rule 2: Low Fuel (< 20%) is critical
        elif self.fuel < 20:
            self.priority_code = PRIORITY_LOW_FUEL
            self.status_display = "BINGO FUEL (<20%)"
            self.color = "#FF9933"  # Orange

        # Rule 3: Mission Critical
        elif self.status_type == "Mission Launch":
            self.priority_code = PRIORITY_MISSION
            self.status_display = "SCRAMBLE / MISSION"
            self.color = "#3399FF"  # Blue

        # Rule 4: Routine
        else:
            self.priority_code = PRIORITY_ROUTINE
            self.status_display = "Routine Landing"
            self.color = "#666666"  # Grey

    def tick_fuel(self):
        """Simulates fuel burn while holding."""
        if self.fuel > 0:
            self.fuel -= 1
        # Re-evaluate priority based on new fuel level
        self.update_priority()


class ATCInterface(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ATC TOWER - PRIORITY MANAGEMENT SYSTEM")
        self.geometry("900x700")

        self.queue = []  # List of Aircraft objects
        self.lock = threading.Lock()

        self.setup_ui()

        # Start Background Simulation (Fuel Burn)
        self.running = True
        self.sim_thread = threading.Thread(target=self.simulation_loop, daemon=True)
        self.sim_thread.start()

    def setup_ui(self):
        # Layout: Left (Input), Right (Queue Display)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL: INPUT ---
        left_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        left_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(left_frame, text="NEW CONTACT", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))

        self.entry_callsign = ctk.CTkEntry(left_frame, placeholder_text="Callsign (e.g. VIPER 1)")
        self.entry_callsign.pack(pady=10, padx=20, fill="x")

        self.entry_fuel = ctk.CTkEntry(left_frame, placeholder_text="Fuel % (0-100)")
        self.entry_fuel.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(left_frame, text="Request Type:").pack(anchor="w", padx=20)
        self.combo_status = ctk.CTkComboBox(left_frame, values=["Routine Landing", "Mission Launch", "Emergency"])
        self.combo_status.pack(pady=5, padx=20, fill="x")

        btn_add = ctk.CTkButton(left_frame, text="+ ADD TO QUEUE", command=self.add_aircraft, fg_color="green",
                                hover_color="darkgreen")
        btn_add.pack(pady=20, padx=20, fill="x")

        ctk.CTkLabel(left_frame, text="TOWER CONTROLS", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(40, 10))

        btn_land = ctk.CTkButton(left_frame, text="CLEAR TO LAND (POP 1)", command=self.process_next, height=50,
                                 fg_color="#333", border_width=2, border_color="white")
        btn_land.pack(pady=10, padx=20, fill="x")

        # --- RIGHT PANEL: THE QUEUE ---
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        ctk.CTkLabel(right_frame, text="APPROACH QUEUE (SORTED BY URGENCY)", font=ctk.CTkFont(size=18)).pack(anchor="w",
                                                                                                             pady=(0,
                                                                                                                   10))

        # Scrollable container for the list items
        self.scroll_list = ctk.CTkScrollableFrame(right_frame, label_text="Aircraft In Pattern")
        self.scroll_list.pack(fill="both", expand=True)

    def add_aircraft(self):
        callsign = self.entry_callsign.get()
        fuel_str = self.entry_fuel.get()
        status = self.combo_status.get()

        if not callsign or not fuel_str:
            return

        try:
            fuel = int(fuel_str)
            if fuel < 0 or fuel > 100: raise ValueError
        except ValueError:
            return  # Invalid input

        new_plane = Aircraft(callsign, fuel, status)

        with self.lock:
            self.queue.append(new_plane)
            self.sort_queue()

        self.refresh_list()

        # Clear inputs
        self.entry_callsign.delete(0, "end")
        self.entry_fuel.delete(0, "end")

    def process_next(self):
        """Clears the top priority plane."""
        with self.lock:
            if self.queue:
                cleared = self.queue.pop(0)  # Remove index 0
                print(f"Cleared {cleared.callsign} for landing.")
                self.refresh_list()

    def sort_queue(self):
        """The Logic Engine: Sorts list based on custom rules."""
        # Primary Sort: Priority Code (Ascending: 1 is best)
        # Secondary Sort: Fuel (Ascending: Less fuel is more urgent)
        self.queue.sort(key=lambda x: (x.priority_code, x.fuel))

    def refresh_list(self):
        # Clear UI
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        # Re-draw sorted list
        for i, plane in enumerate(self.queue):
            self.create_plane_card(plane, i + 1)

    def create_plane_card(self, plane, position):
        """Draws a single row in the list."""
        card = ctk.CTkFrame(self.scroll_list, fg_color=plane.color)
        card.pack(fill="x", pady=5, padx=5)

        # Grid layout inside the card
        card.grid_columnconfigure(2, weight=1)

        # Rank
        lbl_rank = ctk.CTkLabel(card, text=f"#{position}", font=ctk.CTkFont(size=20, weight="bold"), width=50)
        lbl_rank.grid(row=0, column=0, rowspan=2, padx=10)

        # Callsign
        lbl_call = ctk.CTkLabel(card, text=plane.callsign, font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
        lbl_call.grid(row=0, column=1, sticky="w", padx=10)

        # Status Text
        lbl_stat = ctk.CTkLabel(card, text=plane.status_display, text_color="white", anchor="w")
        lbl_stat.grid(row=1, column=1, sticky="w", padx=10)

        # Fuel Gauge text
        lbl_fuel = ctk.CTkLabel(card, text=f"FUEL: {plane.fuel}%", font=ctk.CTkFont(weight="bold"))
        lbl_fuel.grid(row=0, column=3, rowspan=2, padx=20)

    def simulation_loop(self):
        """Background thread: Burns fuel and updates priority."""
        while self.running:
            time.sleep(1.0)  # Tick every second

            needs_refresh = False
            with self.lock:
                for plane in self.queue:
                    old_code = plane.priority_code

                    # Logic: Burn Fuel
                    plane.tick_fuel()

                    # Check if priority changed (e.g. dropped below 20%)
                    if plane.priority_code != old_code:
                        needs_refresh = True

                if needs_refresh or self.queue:
                    # Always re-sort to handle fuel changes re-ordering same-priority items
                    self.sort_queue()

            # Update GUI from main thread context
            # In Tkinter, direct calls from threads can be risky, but refresh_list
            # effectively just queues redraws. Ideally, use .after, but this works for simple apps.
            self.after(0, self.refresh_list)

    def destroy(self):
        self.running = False
        super().destroy()


if __name__ == "__main__":
    app = ATCInterface()
    app.mainloop()