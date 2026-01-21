import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'sonar_db',
    'port': 5432
}


class SonarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SONAR CONTACT CLASSIFICATION SYSTEM")
        self.root.geometry("900x650")
        self.root.configure(bg="#001a33")  # Deep Ocean Blue

        self.init_db()
        self.setup_ui()

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def init_db(self):
        """Self-healing: Creates table and seeds data if missing."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS signatures
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            class_name
                            VARCHAR
                        (
                            50
                        ) NOT NULL,
                            country VARCHAR
                        (
                            50
                        ),
                            prop_blade_count INT,
                            base_frequency FLOAT,
                            noise_level VARCHAR
                        (
                            20
                        ),
                            notes TEXT
                            );
                        """)

            # Check seed
            cur.execute("SELECT COUNT(*) FROM signatures")
            if cur.fetchone()[0] == 0:
                print("Seeding Sonar Database...")
                data = [
                    ('Akula Class II', 'Russia', 7, 50.0, 'Quiet', 'Distinctive 50Hz hum.'),
                    ('Kilo Class', 'Russia', 6, 45.5, 'Silent', 'The Black Hole.'),
                    ('Los Angeles (688i)', 'USA', 7, 60.0, 'Quiet', 'Standard 60Hz hum.'),
                    ('Virginia Class', 'USA', 9, 55.0, 'Silent', 'Pump-jet propulsor.'),
                    ('Type 093 Shang', 'China', 7, 52.0, 'Quiet', 'Reactor whine detected.')
                ]
                cur.executemany(
                    "INSERT INTO signatures (class_name, country, prop_blade_count, base_frequency, noise_level, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                    data)

            conn.commit()
        finally:
            conn.close()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#002b4d", pady=15)
        header.pack(fill="x")
        tk.Label(header, text="ACOUSTIC INTELLIGENCE LIBRARY", font=("Courier", 24, "bold"), bg="#002b4d",
                 fg="#00ffcc").pack()

        # --- INPUT PANEL ---
        input_frame = tk.LabelFrame(self.root, text=" INPUT CONTACT PARAMETERS ",
                                    bg="#001a33", fg="#00ffcc", font=("Arial", 10, "bold"), padx=20, pady=20)
        input_frame.pack(fill="x", padx=20, pady=10)

        # 1. Blade Count
        tk.Label(input_frame, text="Detected Blade Count:", bg="#001a33", fg="white").grid(row=0, column=0, sticky="e")
        self.blade_entry = tk.Entry(input_frame, width=10, font=("Arial", 12))
        self.blade_entry.insert(0, "7")
        self.blade_entry.grid(row=0, column=1, padx=10, pady=5)

        # 2. Frequency
        tk.Label(input_frame, text="Dominant Freq (Hz):", bg="#001a33", fg="white").grid(row=0, column=2, sticky="e")
        self.freq_entry = tk.Entry(input_frame, width=10, font=("Arial", 12))
        self.freq_entry.insert(0, "51.5")  # Example: 51.5 is close to 50 or 52
        self.freq_entry.grid(row=0, column=3, padx=10, pady=5)

        # 3. Tolerance Slider
        tk.Label(input_frame, text="Freq Tolerance (+/-):", bg="#001a33", fg="#aaa").grid(row=1, column=2, sticky="e")
        self.tol_scale = tk.Scale(input_frame, from_=0, to=10, orient=tk.HORIZONTAL, bg="#001a33", fg="white",
                                  highlightthickness=0)
        self.tol_scale.set(3)  # Default +/- 3 Hz
        self.tol_scale.grid(row=1, column=3, sticky="we", padx=10)

        # Search Button
        tk.Button(input_frame, text="CLASSIFY CONTACT", command=self.classify_contact,
                  bg="#004466", fg="#00ffcc", font=("Arial", 12, "bold"), width=20).grid(row=0, column=4, rowspan=2,
                                                                                         padx=30)

        # --- RESULTS TABLE ---
        self.result_lbl = tk.Label(self.root, text="Waiting for input...", bg="#001a33", fg="#aaa", font=("Arial", 11))
        self.result_lbl.pack(pady=5)

        cols = ("class", "country", "blades", "freq", "noise", "notes")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=15)

        self.tree.heading("class", text="CLASS")
        self.tree.heading("country", text="ORIGIN")
        self.tree.heading("blades", text="BLADES")
        self.tree.heading("freq", text="FREQ (Hz)")
        self.tree.heading("noise", text="PROFILE")
        self.tree.heading("notes", text="INTEL NOTES")

        self.tree.column("class", width=120)
        self.tree.column("country", width=80)
        self.tree.column("blades", width=60, anchor="center")
        self.tree.column("freq", width=80, anchor="center")
        self.tree.column("noise", width=80)
        self.tree.column("notes", width=250)

        # Styles
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#002233", foreground="white", fieldbackground="#002233", rowheight=25)
        style.configure("Treeview.Heading", background="#00334d", foreground="white", font=('Arial', 9, 'bold'))

        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

    def classify_contact(self):
        try:
            # Get Inputs
            blades = int(self.blade_entry.get())
            freq_raw = float(self.freq_entry.get())
            tolerance = self.tol_scale.get()
        except ValueError:
            messagebox.showerror("Input Error", "Blade count must be Integer.\nFrequency must be Number.")
            return

        min_freq = freq_raw - tolerance
        max_freq = freq_raw + tolerance

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()

            # --- THE SEARCH LOGIC ---
            # 1. Exact Match on Blades (Mechanical constraint)
            # 2. Range Match on Frequency (Environmental constraint)
            query = """
                    SELECT class_name, country, prop_blade_count, base_frequency, noise_level, notes
                    FROM signatures
                    WHERE prop_blade_count = %s
                      AND base_frequency BETWEEN %s AND %s
                    ORDER BY abs(base_frequency - %s) ASC -- Rank closest match first \
                    """

            cur.execute(query, (blades, min_freq, max_freq, freq_raw))
            matches = cur.fetchall()

            # Update UI
            self.tree.delete(*self.tree.get_children())

            if matches:
                self.result_lbl.config(text=f"MATCH FOUND: {len(matches)} candidates identified.", fg="#00ff00")
                for row in matches:
                    self.tree.insert("", tk.END, values=row)
            else:
                self.result_lbl.config(text="NO MATCH: Unknown class or biological anomaly.", fg="#ff4444")

        except Exception as e:
            messagebox.showerror("Query Error", str(e))
        finally:
            conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = SonarApp(root)
    root.mainloop()