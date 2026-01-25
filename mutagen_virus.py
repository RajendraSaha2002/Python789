import tkinter as tk
from tkinter import messagebox, scrolledtext
import psycopg2
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'gene_bank_db',
    'port': 5432
}


class MutagenVirusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PROJECT CRISPR-MALWARE // TERMINAL")
        self.root.geometry("600x550")
        self.root.configure(bg="#0d0d0d")  # Hacker Black

        self.setup_ui()

    def setup_ui(self):
        # Main Container
        main_frame = tk.Frame(self.root, bg="#0d0d0d", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Header
        lbl_title = tk.Label(main_frame, text="☣️ MUTAGEN INJECTION CONSOLE ☣️",
                             font=("Courier New", 18, "bold"), bg="#0d0d0d", fg="#00ff00")
        lbl_title.pack(pady=(0, 10))

        # DNA Visual (ASCII Art)
        ascii_art_text = "   A-T\n  C---G\n T-----A\nG-------C\n T-----A\n  C---G\n   A-T"
        self.ascii_art = tk.Label(main_frame, text=ascii_art_text,
                                  font=("Courier New", 12), bg="#0d0d0d", fg="#008800")
        self.ascii_art.pack(pady=10)

        # Inputs Frame
        input_frame = tk.Frame(main_frame, bg="#0d0d0d")
        input_frame.pack(fill="x", pady=10)

        # Target Input
        tk.Label(input_frame, text="TARGET SEQUENCE (GENE TO CORRUPT):",
                 font=("Courier New", 10), bg="#0d0d0d", fg="#00ff00").pack(anchor="w")
        self.input_target = tk.Entry(input_frame, font=("Courier New", 12), bg="#222", fg="#fff",
                                     insertbackground="white")
        self.input_target.insert(0, "AAA")
        self.input_target.pack(fill="x", pady=(0, 10))

        # Payload Input
        tk.Label(input_frame, text="VIRAL PAYLOAD (MUTATION):",
                 font=("Courier New", 10), bg="#0d0d0d", fg="#ff0000").pack(anchor="w")
        self.input_payload = tk.Entry(input_frame, font=("Courier New", 12), bg="#222", fg="#ff5555",
                                      insertbackground="red")
        self.input_payload.insert(0, "TTT")
        self.input_payload.pack(fill="x", pady=(0, 10))

        # Buttons
        btn_inject = tk.Button(main_frame, text="INITIATE RETROVIRUS ATTACK", command=self.execute_attack,
                               font=("Courier New", 12, "bold"), bg="#cc0000", fg="white", activebackground="#ff0000",
                               activeforeground="white")
        btn_inject.pack(fill="x", pady=5)

        btn_restore = tk.Button(main_frame, text="ROLLBACK DNA (RESTORE)", command=self.restore_dna,
                                font=("Courier New", 10), bg="#444", fg="white", activebackground="#666",
                                activeforeground="white")
        btn_restore.pack(fill="x", pady=5)

        # Log Console
        self.console = scrolledtext.ScrolledText(main_frame, height=8, font=("Courier New", 10),
                                                 bg="#000", fg="#00ff00", state="disabled")
        self.console.pack(fill="both", expand=True, pady=(10, 0))

    def log(self, message):
        self.console.config(state="normal")
        self.console.insert(tk.END, f"> {message}\n")
        self.console.see(tk.END)
        self.console.config(state="disabled")

    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            self.log(f"DB CONNECTION ERROR: {e}")
            return None

    def execute_attack(self):
        target = self.input_target.get().upper()
        payload = self.input_payload.get().upper()

        if not target or not payload:
            self.log("ERROR: Define target and payload.")
            return

        self.log(f"SCANNING GENE BANK FOR PATTERN: [{target}]...")

        conn = self.connect()
        if not conn: return

        try:
            cur = conn.cursor()

            # Logic: Update rows where DNA contains target, replacing it with payload
            sql = "UPDATE soldiers SET dna_sequence = REPLACE(dna_sequence, %s, %s) WHERE dna_sequence LIKE %s"
            cur.execute(sql, (target, payload, f"%{target}%"))
            affected = cur.rowcount

            conn.commit()

            if affected > 0:
                self.log(f"SUCCESS: {affected} genomes compromised.")
                self.log(f"MUTATION: {target} -> {payload} complete.")
            else:
                self.log("FAILURE: Target sequence not found in any subject.")

        except Exception as e:
            self.log(f"ATTACK ERROR: {str(e)}")
        finally:
            conn.close()

    def restore_dna(self):
        # Simply reverses the default logic for demo purposes
        target = "TTT"
        payload = "AAA"
        self.log("INITIATING BIO-RESTORE PROTOCOL...")

        conn = self.connect()
        if not conn: return

        try:
            cur = conn.cursor()
            sql = "UPDATE soldiers SET dna_sequence = REPLACE(dna_sequence, %s, %s)"
            cur.execute(sql, (target, payload))
            conn.commit()
            self.log("SYSTEM RESTORED. Genetic integrity verified.")
        except Exception as e:
            self.log(f"RESTORE ERROR: {str(e)}")
        finally:
            conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = MutagenVirusApp(root)
    root.mainloop()