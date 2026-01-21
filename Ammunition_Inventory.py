import sqlite3
import random
import datetime
from tkinter import ttk, messagebox
import customtkinter as ctk

# --- Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

DB_FILE = "ammo_depot.db"
TRUCK_MAX_WEIGHT = 5000.0  # kg (e.g., LMTV Truck limit)

# Compatibility Groups (Simplified Military Logic)
# A: Primary Explosive (Detonators) - VERY SENSITIVE
# B: Detonators/Primers - DO NOT MIX WITH D
# C: Propellants - OK with D sometimes
# D: High Explosive (Shells) - DO NOT MIX WITH B
# S: Safety Ammo (Small arms) - Mix with almost anything
COMPATIBILITY_RULES = {
    "A": [],
    "B": ["S"],  # Detonators can only go with safe stuff
    "C": ["D", "S"],  # Propellant can go with Shells
    "D": ["C", "S"],  # Shells can go with Propellant
    "S": ["B", "C", "D"]
}


# --- Database Backend ---

class AmmoDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS inventory
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           item_name
                           TEXT,
                           lot_number
                           TEXT,
                           compat_group
                           TEXT,
                           weight_kg
                           REAL,
                           quantity
                           INTEGER,
                           pallet_id
                           TEXT,
                           timestamp
                           TEXT
                       )
                       ''')
        self.conn.commit()

    def add_item(self, name, lot, group, weight, qty, pallet):
        cursor = self.conn.cursor()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
                       INSERT INTO inventory (item_name, lot_number, compat_group, weight_kg, quantity, pallet_id,
                                              timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ''', (name, lot, group, weight, qty, pallet, ts))
        self.conn.commit()
        return cursor.lastrowid

    def get_all_inventory(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory")
        return cursor.fetchall()

    def search_by_lot(self, lot_fragment):
        cursor = self.conn.cursor()
        query = f"SELECT * FROM inventory WHERE lot_number LIKE '%{lot_fragment}%'"
        cursor.execute(query)
        return cursor.fetchall()

    def delete_item(self, item_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        self.conn.commit()


# --- Application GUI ---

class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SMART AMMO: LOGISTICS TERMINAL")
        self.geometry("1100x700")

        self.db = AmmoDatabase()
        self.truck_manifest = []  # List of items currently on the truck
        self.truck_weight = 0.0
        self.truck_groups = set()  # Set of compatibility groups currently on truck

        self.setup_ui()

    def setup_ui(self):
        # Layout: Sidebar + Main Area
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.lbl_logo = ctk.CTkLabel(self.sidebar, text="ASP-4\nLOGISTICS", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_logo.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_tab_inv = ctk.CTkButton(self.sidebar, text="Depot Inventory",
                                         command=lambda: self.select_tab("Inventory"))
        self.btn_tab_inv.grid(row=1, column=0, padx=20, pady=10)

        self.btn_tab_truck = ctk.CTkButton(self.sidebar, text="Truck Loading", fg_color="#D35400",
                                           hover_color="#A04000", command=lambda: self.select_tab("Truck"))
        self.btn_tab_truck.grid(row=2, column=0, padx=20, pady=10)

        self.btn_tab_recall = ctk.CTkButton(self.sidebar, text="Lot Recall Search", fg_color="#C0392B",
                                            hover_color="#922B21", command=lambda: self.select_tab("Recall"))
        self.btn_tab_recall.grid(row=3, column=0, padx=20, pady=10)

        # --- Main View Container ---
        self.main_view = ctk.CTkTabview(self)
        self.main_view.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_inv = self.main_view.add("Inventory")
        self.tab_truck = self.main_view.add("Truck")
        self.tab_recall = self.main_view.add("Recall")

        # Hide the actual tab buttons (we use sidebar)
        self.main_view._segmented_button.grid_remove()

        self.build_inventory_tab()
        self.build_truck_tab()
        self.build_recall_tab()

    def select_tab(self, name):
        self.main_view.set(name)

    # --- TAB 1: INVENTORY MANAGEMENT ---

    def build_inventory_tab(self):
        # Scan Input Area
        frame_input = ctk.CTkFrame(self.tab_inv)
        frame_input.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_input, text="SCANNER INPUT (RFID/BARCODE)").pack(anchor="w", padx=10, pady=5)

        input_grid = ctk.CTkFrame(frame_input, fg_color="transparent")
        input_grid.pack(fill="x", padx=5, pady=5)

        # Fields
        self.entry_type = ctk.CTkComboBox(input_grid, values=["155mm HE M795", "155mm Smoke M825", "105mm Illum",
                                                              "M67 Charges (Propellant)", "M1156 Fuze (Precision)",
                                                              "Blasting Caps"])
        self.entry_type.pack(side="left", padx=5)

        self.entry_lot = ctk.CTkEntry(input_grid, placeholder_text="Lot Number (e.g. IOP-92K-001)")
        self.entry_lot.pack(side="left", padx=5, fill="x", expand=True)

        self.entry_group = ctk.CTkComboBox(input_grid, values=["D", "C", "B", "S"], width=70)
        self.entry_group.pack(side="left", padx=5)
        self.entry_group.set("D")  # Default HE

        self.entry_weight = ctk.CTkEntry(input_grid, placeholder_text="Wt (kg)", width=70)
        self.entry_weight.pack(side="left", padx=5)

        btn_add = ctk.CTkButton(input_grid, text="+ SCAN IN", command=self.add_inventory)
        btn_add.pack(side="left", padx=5)

        btn_sim = ctk.CTkButton(input_grid, text="🎲 Sim Scan", fg_color="#555", width=80, command=self.sim_scan)
        btn_sim.pack(side="left", padx=5)

        # Inventory Table (Using Treeview for columnar data)
        # CustomTkinter doesn't have a native table, so we embed standard Tkinter Treeview styled appropriately
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])

        self.tree_inv = ttk.Treeview(self.tab_inv, columns=("ID", "Type", "Lot", "Grp", "Weight", "Pallet"),
                                     show="headings")
        self.tree_inv.heading("ID", text="ID")
        self.tree_inv.heading("Type", text="Nomenclature")
        self.tree_inv.heading("Lot", text="Lot Number")
        self.tree_inv.heading("Grp", text="HazMat")
        self.tree_inv.heading("Weight", text="Weight (kg)")
        self.tree_inv.heading("Pallet", text="Pallet ID")

        self.tree_inv.column("ID", width=30)
        self.tree_inv.column("Grp", width=50)
        self.tree_inv.column("Weight", width=80)

        self.tree_inv.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh_inventory()

    def sim_scan(self):
        # Simulate scanning a crate
        items = [
            ("155mm HE M795", "D", 800),
            ("155mm Smoke M825", "D", 750),
            ("M67 Charges", "C", 400),
            ("Blasting Caps", "B", 50)
        ]
        choice = random.choice(items)
        lot = f"SIM-{random.randint(10, 99)}-{random.randint(100, 999)}"

        self.entry_type.set(choice[0])
        self.entry_lot.delete(0, "end");
        self.entry_lot.insert(0, lot)
        self.entry_group.set(choice[1])
        self.entry_weight.delete(0, "end");
        self.entry_weight.insert(0, str(choice[2]))

    def add_inventory(self):
        name = self.entry_type.get()
        lot = self.entry_lot.get()
        grp = self.entry_group.get()
        weight_str = self.entry_weight.get()

        if not lot or not weight_str:
            return

        try:
            weight = float(weight_str)
            pallet = f"P-{random.randint(1000, 9999)}"  # Assign random pallet location
            self.db.add_item(name, lot, grp, weight, 1, pallet)
            self.refresh_inventory()
            # Clear critical fields
            self.entry_lot.delete(0, "end")
        except ValueError:
            messagebox.showerror("Error", "Weight must be a number")

    def refresh_inventory(self):
        # Clear tree
        for i in self.tree_inv.get_children():
            self.tree_inv.delete(i)

        rows = self.db.get_all_inventory()
        for row in rows:
            # row: id, name, lot, group, weight, qty, pallet, ts
            self.tree_inv.insert("", "end", values=(row[0], row[1], row[2], row[3], row[4], row[6]))

    # --- TAB 2: TRUCK LOADING (LOGIC HEAVY) ---

    def build_truck_tab(self):
        # Split view: Available Stock vs Truck Manifest
        split = ctk.CTkFrame(self.tab_truck, fg_color="transparent")
        split.pack(fill="both", expand=True)

        # Left: Warehouse
        left = ctk.CTkFrame(split)
        left.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        ctk.CTkLabel(left, text="WAREHOUSE STOCK").pack()

        self.list_warehouse = ttk.Treeview(left, columns=("ID", "Type", "Grp", "Weight"), show="headings")
        self.list_warehouse.heading("ID", text="ID");
        self.list_warehouse.column("ID", width=30)
        self.list_warehouse.heading("Type", text="Item")
        self.list_warehouse.heading("Grp", text="Haz");
        self.list_warehouse.column("Grp", width=40)
        self.list_warehouse.heading("Weight", text="Wt");
        self.list_warehouse.column("Weight", width=50)
        self.list_warehouse.pack(fill="both", expand=True)

        btn_load = ctk.CTkButton(left, text="LOAD TO TRUCK >>", command=self.load_to_truck)
        btn_load.pack(pady=5)

        # Right: Truck
        right = ctk.CTkFrame(split)
        right.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.lbl_truck_status = ctk.CTkLabel(right, text="TRUCK MANIFEST (Empty)", font=("Arial", 14, "bold"))
        self.lbl_truck_status.pack()

        # Suspension Load Bar
        self.progress_weight = ctk.CTkProgressBar(right)
        self.progress_weight.pack(fill="x", padx=20, pady=5)
        self.progress_weight.set(0)
        self.lbl_weight_val = ctk.CTkLabel(right, text=f"0 / {TRUCK_MAX_WEIGHT} kg")
        self.lbl_weight_val.pack()

        self.list_truck = ttk.Treeview(right, columns=("Type", "Grp", "Weight"), show="headings")
        self.list_truck.heading("Type", text="Item")
        self.list_truck.heading("Grp", text="Haz");
        self.list_truck.column("Grp", width=40)
        self.list_truck.heading("Weight", text="Wt");
        self.list_truck.column("Weight", width=50)
        self.list_truck.pack(fill="both", expand=True)

        btn_clear = ctk.CTkButton(right, text="CLEAR MANIFEST", fg_color="#C0392B", command=self.clear_truck)
        btn_clear.pack(pady=5)

        # Bind tab switch to refresh
        self.refresh_warehouse_list()

    def refresh_warehouse_list(self):
        # Populate left list
        for i in self.list_warehouse.get_children():
            self.list_warehouse.delete(i)

        rows = self.db.get_all_inventory()
        for row in rows:
            # Check if already on truck (simple check by ID in memory)
            if not any(t['id'] == row[0] for t in self.truck_manifest):
                self.list_warehouse.insert("", "end", values=(row[0], row[1], row[3], row[4]))

    def load_to_truck(self):
        selected = self.list_warehouse.selection()
        if not selected: return

        item_vals = self.list_warehouse.item(selected[0])['values']
        item_id, item_name, item_grp, item_weight = item_vals
        item_weight = float(item_weight)

        # 1. Compatibility Check
        # Check new item against existing groups on truck
        for existing_grp in self.truck_groups:
            allowed = COMPATIBILITY_RULES.get(existing_grp, [])
            # Also check reverse (if new item allows existing)
            allowed_reverse = COMPATIBILITY_RULES.get(item_grp, [])

            # Logic: If item_grp is not allowed by existing_grp AND existing_grp is not allowed by item_grp
            # Actually, standard logic: Is 'item_grp' compatible with 'existing_grp'?
            # Usually strict rule: If A is on truck, B cannot be added.

            # Simple simulation check:
            # If we have D, and add B:
            # rules['D'] = ['C', 'S']. 'B' is NOT in allowed list. FAIL.

            if item_grp not in allowed and item_grp != existing_grp:
                messagebox.showwarning("SAFETY VIOLATION",
                                       f"INCOMPATIBLE HAZMAT CLASS!\n\n"
                                       f"Truck contains Group: {existing_grp}\n"
                                       f"Attempting to add: {item_grp}\n\n"
                                       "Load Rejected.")
                return

        # 2. Weight Check
        if self.truck_weight + item_weight > TRUCK_MAX_WEIGHT:
            messagebox.showwarning("OVERLOAD", "Truck suspension limit exceeded!")
            return

        # Add to truck
        self.truck_manifest.append({'id': item_id, 'grp': item_grp, 'wt': item_weight})
        self.truck_groups.add(str(item_grp))
        self.truck_weight += item_weight

        # Update UI
        self.list_truck.insert("", "end", values=(item_name, item_grp, item_weight))
        self.list_warehouse.delete(selected[0])

        # Update Bars
        ratio = self.truck_weight / TRUCK_MAX_WEIGHT
        self.progress_weight.set(ratio)
        self.lbl_weight_val.configure(text=f"{self.truck_weight:.1f} / {TRUCK_MAX_WEIGHT} kg")

        # Color warning
        if ratio > 0.9:
            self.progress_weight.configure(progress_color="red")
        else:
            self.progress_weight.configure(progress_color="#3B8ED0")

    def clear_truck(self):
        self.truck_manifest = []
        self.truck_groups = set()
        self.truck_weight = 0.0
        for i in self.list_truck.get_children():
            self.list_truck.delete(i)
        self.progress_weight.set(0)
        self.refresh_warehouse_list()

    # --- TAB 3: RECALL SYSTEM ---

    def build_recall_tab(self):
        frame_search = ctk.CTkFrame(self.tab_recall)
        frame_search.pack(fill="x", padx=10, pady=10)

        self.entry_recall = ctk.CTkEntry(frame_search, placeholder_text="Enter Defective Lot Number (e.g. IOP-92K)",
                                         width=300)
        self.entry_recall.pack(side="left", padx=10, pady=10)

        btn_search = ctk.CTkButton(frame_search, text="SEARCH DATABASE", fg_color="#C0392B",
                                   command=self.perform_search)
        btn_search.pack(side="left", padx=10)

        self.lbl_recall_status = ctk.CTkLabel(self.tab_recall, text="Status: Waiting for input...", font=("Arial", 16))
        self.lbl_recall_status.pack(pady=10)

        self.tree_recall = ttk.Treeview(self.tab_recall, columns=("Type", "Lot", "Pallet"), show="headings")
        self.tree_recall.heading("Type", text="Item")
        self.tree_recall.heading("Lot", text="Lot #")
        self.tree_recall.heading("Pallet", text="LOCATION (PALLET ID)")
        self.tree_recall.pack(fill="both", expand=True, padx=20, pady=20)

        # Style critical columns
        self.tree_recall.tag_configure('critical', background='#e74c3c', foreground='white')

    def perform_search(self):
        query = self.entry_recall.get()
        if not query: return

        # Clear
        for i in self.tree_recall.get_children():
            self.tree_recall.delete(i)

        results = self.db.search_by_lot(query)

        if results:
            self.lbl_recall_status.configure(text=f"CRITICAL: FOUND {len(results)} MATCHING UNITS", text_color="red")
            for row in results:
                # row[6] is pallet_id
                self.tree_recall.insert("", "end", values=(row[1], row[2], row[6]), tags=('critical',))
        else:
            self.lbl_recall_status.configure(text="No matching lots found in inventory.", text_color="green")


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()