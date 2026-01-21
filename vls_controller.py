import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import random

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'warship_db',
    'port': 5432
}

CELL_TOTAL = 96
MODULES = 12  # 8 cells per module


class VLSManager:
    def __init__(self, root):
        self.root = root
        self.root.title("COMBAT SYSTEM // VLS INVENTORY MASTER")
        self.root.geometry("1200x800")
        self.root.configure(bg="#001100")  # Radar Green Theme

        self.cell_widgets = {}  # Map cell_id -> UI Widget

        self.init_db()
        self.setup_ui()
        self.refresh_grid()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def init_db(self):
        """Self-healing DB: Creates table and seeds 96 cells if empty."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS vls_cells
                        (
                            cell_id
                            INT
                            PRIMARY
                            KEY,
                            module_id
                            INT,
                            missile_type
                            VARCHAR
                        (
                            20
                        ) DEFAULT 'None',
                            status VARCHAR
                        (
                            20
                        ) DEFAULT 'ARMED'
                            );
                        """)

            # Check if seeded
            cur.execute("SELECT COUNT(*) FROM vls_cells")
            if cur.fetchone()[0] == 0:
                print("Seeding VLS Magazine...")
                # Generate realistic loadout
                loadout = []
                for i in range(1, CELL_TOTAL + 1):
                    # Assign Module (8 cells per module)
                    mod_id = (i - 1) // 8 + 1

                    # Random Missile Assignment
                    r = random.random()
                    if r < 0.4:
                        m_type = 'Tomahawk'  # 40% Land Attack
                    elif r < 0.8:
                        m_type = 'SM-2'  # 40% Anti-Air
                    else:
                        m_type = 'ESSM'  # 20% Self Defense

                    loadout.append((i, mod_id, m_type, 'ARMED'))

                args_str = ','.join(cur.mogrify("(%s,%s,%s,%s)", x).decode('utf-8') for x in loadout)
                cur.execute("INSERT INTO vls_cells (cell_id, module_id, missile_type, status) VALUES " + args_str)

            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#002200", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="VERTICAL LAUNCH SYSTEM (VLS) STATUS",
                 font=("Courier", 24, "bold"), bg="#002200", fg="#00ff00").pack()

        # --- CONTROLS ---
        control_frame = tk.LabelFrame(self.root, text=" FIRE CONTROL ", bg="#001100", fg="#00ff00")
        control_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(control_frame, text="SELECT ORDNANCE:", bg="#001100", fg="white").pack(side="left", padx=10)

        self.type_combo = ttk.Combobox(control_frame, values=["Tomahawk", "SM-2", "ESSM"], state="readonly", width=15)
        self.type_combo.set("Tomahawk")
        self.type_combo.pack(side="left", padx=10)

        tk.Label(control_frame, text="SALVO SIZE:", bg="#001100", fg="white").pack(side="left", padx=10)
        self.qty_entry = tk.Entry(control_frame, width=5)
        self.qty_entry.insert(0, "2")
        self.qty_entry.pack(side="left", padx=10)

        tk.Button(control_frame, text="EXECUTE LAUNCH", command=self.fire_salvo,
                  bg="#cc0000", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=30)

        tk.Button(control_frame, text="SYSTEM RESET (RELOAD)", command=self.reload_cells,
                  bg="#444", fg="white").pack(side="right", padx=10)

        # --- GRID DISPLAY ---
        self.grid_frame = tk.Frame(self.root, bg="#001100")
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=10)
        # We will draw the cells in refresh_grid()

    def refresh_grid(self):
        # Clear existing
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT cell_id, module_id, missile_type, status FROM vls_cells ORDER BY cell_id ASC")
            cells = cur.fetchall()

            # Layout: 12 Modules side-by-side? Too wide.
            # Let's do 2 rows of Modules (Forward Deck / Aft Deck)
            # Row 1: Modules 1-6 (Cells 1-48)
            # Row 2: Modules 7-12 (Cells 49-96)

            for row in cells:
                cid, mid, mtype, status = row

                # Determine Colors
                bg_col = "#004400"  # Ready Green
                fg_col = "white"

                if status == 'EMPTY':
                    bg_col = "#111"  # Black/Empty
                    fg_col = "#333"
                elif status == 'JAMMED':
                    bg_col = "#884400"  # Orange
                elif status == 'SAFE':
                    bg_col = "#444"  # Gray

                # Create Cell Visual
                # Grid Math:
                # Modules 1-6 on top row, 7-12 on bottom
                # Each module is a column block

                mod_col = (mid - 1) % 6
                mod_row_offset = 0 if mid <= 6 else 10  # Space between Fwd/Aft decks

                cell_in_mod = (cid - 1) % 8

                # Final Grid Coordinates
                r = cell_in_mod + mod_row_offset + (1 if mid > 6 else 0)  # Add a spacer row
                c = mod_col

                f = tk.Frame(self.grid_frame, bg="black", bd=1)
                f.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

                lbl = tk.Label(f, text=f"{cid}\n{mtype[:3]}", bg=bg_col, fg=fg_col,
                               width=8, height=2, font=("Arial", 8))
                lbl.pack(fill="both")

                self.cell_widgets[cid] = lbl

            # Add Labels for "FORWARD VLS" and "AFT VLS"
            tk.Label(self.grid_frame, text="FORWARD DECK (Modules 1-6)", bg="#001100", fg="#00ff00").grid(row=8,
                                                                                                          column=0,
                                                                                                          columnspan=6,
                                                                                                          pady=5)
            tk.Label(self.grid_frame, text="AFT DECK (Modules 7-12)", bg="#001100", fg="#00ff00").grid(row=19, column=0,
                                                                                                       columnspan=6,
                                                                                                       pady=5)

        finally:
            conn.close()

    def fire_salvo(self):
        m_type = self.type_combo.get()
        try:
            qty = int(self.qty_entry.get())
        except ValueError:
            return

        conn = self.connect()
        try:
            cur = conn.cursor()

            # 1. FIND CANDIDATES
            # Get all ARMED cells with correct missile type
            cur.execute("""
                        SELECT cell_id, module_id
                        FROM vls_cells
                        WHERE missile_type = %s
                          AND status = 'ARMED'
                        ORDER BY module_id ASC
                        """, (m_type,))
            candidates = cur.fetchall()  # List of (cell_id, module_id)

            if len(candidates) < qty:
                messagebox.showerror("INVENTORY ERROR",
                                     f"Not enough {m_type}s available!\nRequested: {qty}\nAvailable: {len(candidates)}")
                return

            # 2. SELECTION ALGORITHM (Balance the Ship)
            # We want to pick from different modules if possible.
            # Simple approach: Sort candidates by Module ID, then pick striding.
            # Example: If we have candidates in Mod 1, 1, 2, 8, 8...
            # We want to pick Mod 1, then Mod 8, then Mod 2...

            selected_cells = []

            # Separate candidates into Forward (Mods 1-6) and Aft (Mods 7-12)
            fwd = [c for c in candidates if c[1] <= 6]
            aft = [c for c in candidates if c[1] > 6]

            # Alternate picking Forward/Aft to balance weight
            while qty > 0:
                if fwd and qty > 0:
                    selected_cells.append(fwd.pop(0)[0])  # Take first available Fwd
                    qty -= 1
                if aft and qty > 0:
                    selected_cells.append(aft.pop(0)[0])  # Take first available Aft
                    qty -= 1

                # If we run out of one side, just consume the other
                if not fwd and not aft and qty > 0:
                    break  # Should be caught by initial count check, but safety first

            # 3. FIRE (Update DB)
            cell_ids_tuple = tuple(selected_cells)
            cur.execute("UPDATE vls_cells SET status = 'EMPTY' WHERE cell_id IN %s", (cell_ids_tuple,))
            conn.commit()

            # Visual Feedback
            self.refresh_grid()
            messagebox.showinfo("SALVO COMPLETE",
                                f"Fired {len(selected_cells)} {m_type}s from cells:\n{selected_cells}")

        finally:
            conn.close()

    def reload_cells(self):
        """Reset everything to ARMED."""
        if messagebox.askyesno("RELOAD", "Reset all cells to ARMED status?"):
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("UPDATE vls_cells SET status = 'ARMED' WHERE status = 'EMPTY'")
            conn.commit()
            conn.close()
            self.refresh_grid()


if __name__ == "__main__":
    root = tk.Tk()
    app = VLSManager(root)
    root.mainloop()