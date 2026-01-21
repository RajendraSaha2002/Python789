import tkinter as tk
from tkinter import messagebox


# --- 1. THE LOGIC (The Brains) ---
def calculate_star():
    try:
        # Get values from the white text boxes (Entry widgets)
        r1 = float(entry_r1.get())
        r2 = float(entry_r2.get())
        r3 = float(entry_r3.get())

        # Calculate the Denominator
        r_sum = r1 + r2 + r3

        # Calculate Star Resistors (Ra, Rb, Rc)
        ra = (r1 * r2) / r_sum
        rb = (r2 * r3) / r_sum
        rc = (r3 * r1) / r_sum

        # Update the result text on the screen
        result_text.set(f"Results (Star Configuration):\n"
                        f"Ra = {ra:.2f} Ω\n"
                        f"Rb = {rb:.2f} Ω\n"
                        f"Rc = {rc:.2f} Ω")

    except ValueError:
        # If the user types "abc" instead of numbers
        messagebox.showerror("Input Error", "Please enter valid numbers only.")


# --- 2. THE GUI SETUP (The Body) ---
# Create the main window
window = tk.Tk()
window.title("ECE Resistor Calculator")
window.geometry("350x300")  # Width x Height

# -- Input Section --
# Label and Box for R1
tk.Label(window, text="Enter R1 (Delta) in Ohms:").pack(pady=5)
entry_r1 = tk.Entry(window)
entry_r1.pack()

# Label and Box for R2
tk.Label(window, text="Enter R2 (Delta) in Ohms:").pack(pady=5)
entry_r2 = tk.Entry(window)
entry_r2.pack()

# Label and Box for R3
tk.Label(window, text="Enter R3 (Delta) in Ohms:").pack(pady=5)
entry_r3 = tk.Entry(window)
entry_r3.pack()

# -- Button Section --
# When clicked, it calls the 'calculate_star' function above
btn_calc = tk.Button(window, text="Calculate Star Values",
                     command=calculate_star,
                     bg="lightblue", font=("Arial", 10, "bold"))
btn_calc.pack(pady=20)

# -- Output Section --
result_text = tk.StringVar()
result_text.set("Results will appear here...")
lbl_result = tk.Label(window, textvariable=result_text,
                      fg="blue", font=("Courier", 12))
lbl_result.pack()

# --- 3. START THE APP ---
window.mainloop()