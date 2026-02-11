import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import sqlalchemy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from faker import Faker
import random
import threading
import time

# DB CONNECTION
# REPLACE with your actual credentials
db_connection_str = 'postgresql+psycopg2://postgres:varrie75@localhost/postgres'
db_engine = sqlalchemy.create_engine(db_connection_str)


class SupplyChainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Global Supply Chain Command Center")
        self.root.geometry("1400x900")
        self.root.configure(bg="#263238")  # Dark Theme

        self.setup_header()
        self.setup_tabs()

    def setup_header(self):
        header = tk.Frame(self.root, bg="#37474f", height=80)
        header.pack(fill='x')

        tk.Label(header, text="📦 DISTRIBUTION INTELLIGENCE SYSTEM", bg="#37474f", fg="#eceff1",
                 font=("Oswald", 22, "bold")).pack(side="left", padx=20, pady=20)

        # Simulation Controls
        btn_frame = tk.Frame(header, bg="#37474f")
        btn_frame.pack(side="right", padx=20)

        self.btn_seed = tk.Button(btn_frame, text="INIT WAREHOUSE (SEED)", bg="#ff9800", fg="white",
                                  font=("Arial", 10, "bold"), command=self.seed_initial_data)
        self.btn_seed.pack(side="left", padx=5)

        self.btn_sim = tk.Button(btn_frame, text="RUN DEMAND SIMULATION", bg="#00e676", fg="black",
                                 font=("Arial", 10, "bold"), command=self.start_simulation)
        self.btn_sim.pack(side="left", padx=5)

    def setup_tabs(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#263238", borderwidth=0)
        style.configure("TNotebook.Tab", background="#455a64", foreground="white", padding=[20, 10],
                        font=('Arial', 10, 'bold'))
        style.map("TNotebook.Tab", background=[("selected", "#00bcd4")])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.tab_dashboard = tk.Frame(self.notebook, bg="white")
        self.tab_alerts = tk.Frame(self.notebook, bg="white")

        self.notebook.add(self.tab_dashboard, text="Inventory Analytics")
        self.notebook.add(self.tab_alerts, text="Critical Alerts & Stockouts")

        self.build_dashboard()
        self.build_alerts_tab()

    def run_query(self, sql):
        with db_engine.connect() as conn:
            return pd.read_sql(sql, conn)

    # ================= DASHBOARD TAB =================
    def build_dashboard(self):
        # Refresh Button
        tk.Button(self.tab_dashboard, text="Refresh Analytics", command=self.refresh_dashboard).pack(pady=5)

        self.dash_frame = tk.Frame(self.tab_dashboard, bg="white")
        self.dash_frame.pack(fill='both', expand=True)

    def refresh_dashboard(self):
        for w in self.dash_frame.winfo_children(): w.destroy()

        try:
            # 1. Fetch Velocity Data
            df = self.run_query("SELECT * FROM v_stock_velocity LIMIT 15")

            if df.empty:
                tk.Label(self.dash_frame, text="System Empty. Click 'INIT WAREHOUSE' first.").pack(pady=50)
                return

            fig = plt.figure(figsize=(12, 8))
            gs = fig.add_gridspec(2, 2)

            # Chart 1: Inventory Levels by Location
            ax1 = fig.add_subplot(gs[0, 0])
            sns.barplot(data=df, x='location_code', y='quantity_on_hand', hue='product_name', palette='magma', ax=ax1)
            ax1.set_title("Current Stock Levels per Warehouse")
            ax1.legend(loc='upper right', fontsize='small')

            # Chart 2: Demand Velocity (Sales)
            ax2 = fig.add_subplot(gs[0, 1])
            sns.barplot(data=df, y='product_name', x='monthly_sales', palette='viridis', ax=ax2)
            ax2.set_title("Top Movers (30-Day Velocity)")

            # Chart 3: Days of Supply Risk
            ax3 = fig.add_subplot(gs[1, :])  # Full width
            # Filter for items with low days of supply
            df['risk_status'] = df['days_of_supply'].apply(lambda x: 'Critical' if x < 10 else 'Healthy')
            sns.scatterplot(data=df, x='quantity_on_hand', y='monthly_sales', hue='risk_status', size='days_of_supply',
                            sizes=(50, 400), ax=ax3)
            ax3.set_title("Supply Risk Matrix (High Sales + Low Stock = Critical)")

            plt.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.dash_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)

        except Exception as e:
            print(e)

    # ================= ALERTS TAB =================
    def build_alerts_tab(self):
        self.tree = ttk.Treeview(self.tab_alerts, columns=("Warehouse", "Product", "Message", "Time"), show='headings')
        self.tree.heading("Warehouse", text="Warehouse ID")
        self.tree.heading("Product", text="Product ID")
        self.tree.heading("Message", text="Alert Message")
        self.tree.heading("Time", text="Detected At")

        self.tree.column("Message", width=400)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Button(self.tab_alerts, text="Refresh Alerts", command=self.load_alerts).pack(pady=5)

    def load_alerts(self):
        for i in self.tree.get_children(): self.tree.delete(i)

        df = self.run_query(
            "SELECT warehouse_id, product_id, message, created_at FROM inventory_alerts ORDER BY created_at DESC LIMIT 50")
        for _, row in df.iterrows():
            self.tree.insert("", "0",
                             values=(row['warehouse_id'], row['product_id'], row['message'], row['created_at']))

    # ================= SIMULATION LOGIC =================
    def seed_initial_data(self):
        messagebox.showinfo("Wait", "Seeding Warehouses and Products...")
        fake = Faker()

        # 1. Create Warehouses
        warehouses = [
            {'name': 'East Coast Hub', 'location_code': 'US-EAST', 'capacity': 50000},
            {'name': 'West Coast Hub', 'location_code': 'US-WEST', 'capacity': 40000},
            {'name': 'Euro Central', 'location_code': 'EU-BER', 'capacity': 35000}
        ]
        pd.DataFrame(warehouses).to_sql('warehouses', db_engine, if_exists='append', index=False)

        # 2. Create Products
        products = []
        for _ in range(20):
            products.append({
                'sku': fake.ean8(),
                'name': fake.bs().split()[0] + " " + fake.word().capitalize(),
                'category': random.choice(['Electronics', 'Home', 'Industrial']),
                'unit_cost': random.randint(10, 500),
                'reorder_point': 50,  # Alert if below 50
                'reorder_qty': 200
            })
        pd.DataFrame(products).to_sql('products', db_engine, if_exists='append', index=False)

        # 3. Initial Stocking
        # Get IDs back
        w_ids = self.run_query("SELECT warehouse_id FROM warehouses")['warehouse_id'].tolist()
        p_ids = self.run_query("SELECT product_id FROM products")['product_id'].tolist()

        inventory = []
        for w in w_ids:
            for p in p_ids:
                inventory.append({
                    'warehouse_id': w,
                    'product_id': p,
                    'quantity_on_hand': random.randint(100, 500),  # Healthy stock
                    'last_restock_date': datetime.datetime.now()
                })
        pd.DataFrame(inventory).to_sql('inventory', db_engine, if_exists='append', index=False)
        messagebox.showinfo("Success", "Warehouse Setup Complete!")

    def start_simulation(self):
        threading.Thread(target=self.run_demand_simulation).start()

    def run_demand_simulation(self):
        # Simulate High Demand (Sales) -> Lowers Stock -> Triggers Alerts
        messagebox.showinfo("Simulation", "Running Demand Spike! Check Alerts Tab in 5 seconds.")

        w_ids = self.run_query("SELECT warehouse_id FROM warehouses")['warehouse_id'].tolist()
        p_ids = self.run_query("SELECT product_id FROM products")['product_id'].tolist()

        with db_engine.connect() as conn:
            # Simulate 100 sales events
            for _ in range(100):
                w = random.choice(w_ids)
                p = random.choice(p_ids)
                qty_sold = random.randint(5, 20)

                # Update DB (Trigger will catch this)
                conn.execute(sqlalchemy.text(f"""
                    UPDATE inventory 
                    SET quantity_on_hand = quantity_on_hand - {qty_sold} 
                    WHERE warehouse_id = {w} AND product_id = {p}
                """))

                # Log movement
                conn.execute(sqlalchemy.text(f"""
                    INSERT INTO stock_movements (product_id, warehouse_id, movement_type, quantity)
                    VALUES ({p}, {w}, 'OUTBOUND', {qty_sold})
                """))
                conn.commit()
                time.sleep(0.05)  # fast simulation

        messagebox.showinfo("Done", "Simulation Ended. Refresh Dashboard.")


import datetime

if __name__ == "__main__":
    root = tk.Tk()
    app = SupplyChainApp(root)
    root.mainloop()