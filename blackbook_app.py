import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2


class BlackBookApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CIA Black Book // Intel Manager")
        self.root.geometry("600x500")
        self.root.configure(bg="#222")  # Dark Mode for "Hacker" feel

        self.db_connection = None

        # Start with Login Screen
        self.show_login_screen()

    def show_login_screen(self):
        self.clear_window()

        # Style
        lbl_font = ("Courier New", 12)
        entry_font = ("Courier New", 12)

        tk.Label(self.root, text="/// CLASSIFIED LOGIN ///", font=("Courier New", 20, "bold"),
                 bg="#222", fg="#0f0").pack(pady=40)

        # Form Frame
        frame = tk.Frame(self.root, bg="#222")
        frame.pack()

        tk.Label(frame, text="AGENT ID (Username):", font=lbl_font, bg="#222", fg="#fff").grid(row=0, column=0, pady=5,
                                                                                               sticky="e")
        self.user_entry = tk.Entry(frame, font=entry_font)
        self.user_entry.grid(row=0, column=1, pady=5, padx=10)

        tk.Label(frame, text="ACCESS CODE (Password):", font=lbl_font, bg="#222", fg="#fff").grid(row=1, column=0,
                                                                                                  pady=5, sticky="e")
        self.pass_entry = tk.Entry(frame, show="*", font=entry_font)
        self.pass_entry.grid(row=1, column=1, pady=5, padx=10)

        tk.Button(self.root, text="AUTHENTICATE", command=self.login,
                  font=("Courier New", 14, "bold"), bg="#444", fg="#0f0", width=20).pack(pady=30)

        tk.Label(self.root, text="HINT: junior_analyst / junior123\nOR: general_wolf / general123",
                 bg="#222", fg="#666").pack(side=tk.BOTTOM, pady=10)

    def login(self):
        username = self.user_entry.get()
        password = self.pass_entry.get()

        try:
            # CONNECT AS THE SPECIFIC USER
            # This is crucial. We do NOT connect as 'postgres'.
            # We connect as whoever is logging in, so RLS applies to THEM.
            self.db_connection = psycopg2.connect(
                host="localhost",
                database="postgres",  # Or whatever DB you ran the script on
                user=username,
                password=password
            )
            self.current_user = username
            self.show_dashboard()

        except psycopg2.Error as e:
            messagebox.showerror("Access Denied", f"Invalid Credentials or Permission Error.\n\nDB Error: {e}")

    def show_dashboard(self):
        self.clear_window()

        # Header
        header = tk.Frame(self.root, bg="#000")
        header.pack(fill="x")
        tk.Label(header, text=f"LOGGED IN AS: {self.current_user.upper()}",
                 font=("Courier New", 10), bg="#000", fg="#0f0", padx=10, pady=5).pack(side=tk.LEFT)
        tk.Button(header, text="LOGOUT", command=self.logout,
                  font=("Courier New", 8), bg="#300", fg="#fff").pack(side=tk.RIGHT, padx=5, pady=5)

        # Search Bar
        search_frame = tk.Frame(self.root, bg="#222", pady=20)
        search_frame.pack()

        tk.Label(search_frame, text="SEARCH INTEL:", font=("Courier New", 12), bg="#222", fg="#fff").pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, font=("Courier New", 12), width=30)
        self.search_entry.pack(side=tk.LEFT, padx=10)
        tk.Button(search_frame, text="SCAN", command=self.perform_search,
                  bg="#004", fg="#fff", font=("Courier New", 10)).pack(side=tk.LEFT)

        # Results Table
        columns = ("codename", "content", "level")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")

        self.tree.heading("codename", text="CODENAME")
        self.tree.heading("content", text="INTEL REPORT")
        self.tree.heading("level", text="CLEARANCE")

        self.tree.column("codename", width=150)
        self.tree.column("content", width=300)
        self.tree.column("level", width=100)

        self.tree.pack(fill="both", expand=True, padx=20, pady=20)

        # Load all data initially
        self.perform_search(query_all=True)

    def perform_search(self, query_all=False):
        if not self.db_connection: return

        search_term = self.search_entry.get()
        cursor = self.db_connection.cursor()

        # CLEAR TABLE
        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            sql = "SELECT codename, content, clearance_level FROM intel_reports"

            if not query_all and search_term:
                sql += " WHERE content ILIKE %s OR codename ILIKE %s"
                cursor.execute(sql, (f"%{search_term}%", f"%{search_term}%"))
            else:
                cursor.execute(sql)

            rows = cursor.fetchall()

            for row in rows:
                self.tree.insert("", tk.END, values=row)

            if not rows:
                messagebox.showinfo("Scanner", "No Intel Found (or Access Restricted).")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def logout(self):
        if self.db_connection:
            self.db_connection.close()
        self.show_login_screen()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = BlackBookApp(root)
    root.mainloop()