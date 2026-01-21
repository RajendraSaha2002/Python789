import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2

# --- DATABASE CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'shop_inventory_db',
    'port': 5432
}


class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Desktop Inventory Manager")
        self.root.geometry("900x500")

        # Variables to store input
        self.var_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_supplier = tk.StringVar()

        # Store Supplier ID map (Name -> ID)
        self.supplier_map = {}

        # --- UI LAYOUT ---
        self.create_widgets()

        # --- LOAD INITIAL DATA ---
        self.load_suppliers()
        self.load_products()

    def create_widgets(self):
        # 1. Input Frame (Top)
        input_frame = tk.LabelFrame(self.root, text="Manage Product", padx=20, pady=20)
        input_frame.pack(fill="x", padx=10, pady=5)

        # Labels & Entries
        tk.Label(input_frame, text="Product Name:").grid(row=0, column=0, sticky="w")
        tk.Entry(input_frame, textvariable=self.var_name, width=25).grid(row=0, column=1, padx=5)

        tk.Label(input_frame, text="Price ($):").grid(row=0, column=2, sticky="w")
        tk.Entry(input_frame, textvariable=self.var_price, width=15).grid(row=0, column=3, padx=5)

        tk.Label(input_frame, text="Stock Count:").grid(row=0, column=4, sticky="w")
        tk.Entry(input_frame, textvariable=self.var_stock, width=15).grid(row=0, column=5, padx=5)

        tk.Label(input_frame, text="Supplier:").grid(row=0, column=6, sticky="w")
        self.supplier_combo = ttk.Combobox(input_frame, textvariable=self.var_supplier, state="readonly", width=20)
        self.supplier_combo.grid(row=0, column=7, padx=5)

        # Buttons
        btn_frame = tk.Frame(input_frame, pady=10)
        btn_frame.grid(row=1, column=0, columnspan=8)

        tk.Button(btn_frame, text="Add Product", command=self.add_product, bg="#90ee90", width=12).pack(side=tk.LEFT,
                                                                                                        padx=5)
        tk.Button(btn_frame, text="Update Selected", command=self.update_product, bg="#add8e6", width=12).pack(
            side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_product, bg="#ffcccb", width=12).pack(
            side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear Form", command=self.clear_form, width=12).pack(side=tk.LEFT, padx=5)

        # 2. Table Frame (Bottom)
        table_frame = tk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Scrollbar
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)

        # Treeview (The Table)
        columns = ("id", "name", "price", "stock", "supplier")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", yscrollcommand=scroll_y.set)

        scroll_y.config(command=self.tree.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Product Name")
        self.tree.heading("price", text="Price")
        self.tree.heading("stock", text="Stock")
        self.tree.heading("supplier", text="Supplier")

        self.tree.column("id", width=50)
        self.tree.column("name", width=200)

        self.tree.pack(fill="both", expand=True)

        # Bind Click Event (to populate inputs when a row is clicked)
        self.tree.bind("<ButtonRelease-1>", self.fill_inputs_from_table)

    # --- DATABASE HELPERS ---
    def connect(self):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            return None

    def load_suppliers(self):
        """Fetches suppliers to populate the dropdown."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM suppliers")
            rows = cur.fetchall()

            self.supplier_map = {row[1]: row[0] for row in rows}  # Map Name -> ID
            self.supplier_combo['values'] = list(self.supplier_map.keys())

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def load_products(self):
        """Fetches products + supplier names using a JOIN."""
        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            # SQL JOIN: This matches product.supplier_id to supplier.id to get the Name
            query = """
                    SELECT p.id, p.name, p.price, p.stock_count, s.name
                    FROM products p
                             LEFT JOIN suppliers s ON p.supplier_id = s.id
                    ORDER BY p.id ASC \
                    """
            cur.execute(query)
            rows = cur.fetchall()

            # Clear current table
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Insert new rows
            for row in rows:
                self.tree.insert("", tk.END, values=row)

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    # --- ACTION HANDLERS ---
    def add_product(self):
        name = self.var_name.get()
        price = self.var_price.get()
        stock = self.var_stock.get()
        supplier_name = self.var_supplier.get()

        if not (name and price and stock and supplier_name):
            messagebox.showwarning("Validation", "All fields are required!")
            return

        supplier_id = self.supplier_map.get(supplier_name)

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO products (name, price, stock_count, supplier_id) VALUES (%s, %s, %s, %s)",
                        (name, price, stock, supplier_id))
            conn.commit()
            messagebox.showinfo("Success", "Product Added!")
            self.clear_form()
            self.load_products()
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def update_product(self):
        prod_id = self.var_id.get()
        if not prod_id:
            messagebox.showwarning("Select", "Please select a product from the table first.")
            return

        supplier_id = self.supplier_map.get(self.var_supplier.get())

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("""
                        UPDATE products
                        SET name=%s,
                            price=%s,
                            stock_count=%s,
                            supplier_id=%s
                        WHERE id = %s
                        """, (self.var_name.get(), self.var_price.get(), self.var_stock.get(), supplier_id, prod_id))
            conn.commit()
            messagebox.showinfo("Success", "Product Updated!")
            self.clear_form()
            self.load_products()
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def delete_product(self):
        prod_id = self.var_id.get()
        if not prod_id:
            messagebox.showwarning("Select", "Please select a product from the table first.")
            return

        confirm = messagebox.askyesno("Confirm", "Are you sure you want to delete this product?")
        if not confirm: return

        conn = self.connect()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM products WHERE id=%s", (prod_id,))
            conn.commit()
            messagebox.showinfo("Deleted", "Product Deleted Successfully")
            self.clear_form()
            self.load_products()
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def fill_inputs_from_table(self, event):
        """Populates the input fields when a row is clicked."""
        selected_item = self.tree.focus()
        if not selected_item: return

        row_data = self.tree.item(selected_item)['values']

        self.var_id.set(row_data[0])
        self.var_name.set(row_data[1])
        self.var_price.set(row_data[2])
        self.var_stock.set(row_data[3])

        # Handle Supplier Combobox (row_data[4] is supplier name)
        supplier_name = row_data[4]
        if supplier_name in self.supplier_map:
            self.supplier_combo.set(supplier_name)
        else:
            self.supplier_combo.set("")  # Handle cases where supplier might be null

    def clear_form(self):
        self.var_id.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_stock.set("")
        self.supplier_combo.set("")


if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()