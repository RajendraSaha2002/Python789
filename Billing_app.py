import tkinter as tk
from tkinter import messagebox
import random

class SimpleBillingApp:
    def __init__(self, Root):
        self.root = Root
        self.root.title("Simple Billing Software")
        self.root.geometry("600x400")


        self.products = {
            "Sanitizer": 2,
            "Mask": 5,
            "Rice": 10,
            "Food Oil": 10,
            "Sprite": 10,
            "Coke": 10,
        }

        self.entries = {}
        row = 0
        tk.Label(Root, text="Product", font=("Arial", 14, "bold")).grid(row=row, column=0, padx=10, pady=5)
        tk.Label(Root, text="Quantity", font=("Arial", 14, "bold")).grid(row=row, column=1, padx=10, pady=5)
        row += 1

        # Entry for each product
        for prod in self.products:
            tk.Label(Root, text=prod, font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10)
            var = tk.IntVar()
            self.entries[prod] = var
            tk.Entry(Root, textvariable=var, width=5).grid(row=row, column=1)
            row += 1

        # Customer info
        tk.Label(Root, text="Customer Name:", font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10)
        self.cust_name = tk.Entry(Root)
        self.cust_name.grid(row=row, column=1)
        row += 1

        tk.Label(Root, text="Customer Phone:", font=("Arial", 12)).grid(row=row, column=0, sticky="w", padx=10)
        self.cust_phone = tk.Entry(Root)
        self.cust_phone.grid(row=row, column=1)
        row += 1


        tk.Button(Root, text="Generate Bill", command=self.generate_bill, font=("Arial", 12), bg="green", fg="white").grid(row=row, column=0, columnspan=2, pady=10)

        # Bill display
        self.bill_text = tk.Text(Root, height=10, width=60)
        self.bill_text.grid(row=row+1, column=0, columnspan=2, padx=10)

    def generate_bill(self):
        name = self.cust_name.get().strip()
        phone = self.cust_phone.get().strip()
        if not name or not phone:
            messagebox.showerror("Input Error", "Please enter customer name and phone.")
            return

        bill_no = random.randint(1000, 9999)
        self.bill_text.delete("1.0", tk.END)
        self.bill_text.insert(tk.END, f"Bill No: {bill_no}\nCustomer: {name}\nPhone: {phone}\n")
        self.bill_text.insert(tk.END, "-"*50 + "\n")
        self.bill_text.insert(tk.END, "Product\tQty\tPrice\n")

        total = 0
        for prod, price in self.products.items():
            qty = self.entries[prod].get()
            if qty > 0:
                line_price = qty * price
                total += line_price
                self.bill_text.insert(tk.END, f"{prod}\t{qty}\t{line_price}\n")
        self.bill_text.insert(tk.END, "-"*50 + "\n")
        self.bill_text.insert(tk.END, f"Total: {total}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleBillingApp(root)
    root.mainloop()