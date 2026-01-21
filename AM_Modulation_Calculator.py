import tkinter as tk
from tkinter import messagebox


# --- 1. THE LOGIC ---
def calculate_modulation():
    try:
        # Get values from the white text boxes
        # We assume users might enter integers or decimals
        v_max = float(entry_vmax.get())
        v_min = float(entry_vmin.get())

        # Validation: V_max cannot be smaller than V_min
        if v_min > v_max:
            messagebox.showerror("Physics Error", "V_max must be greater than V_min!")
            return

        # The AM Formula
        m_index = (v_max - v_min) / (v_max + v_min)
        m_percent = m_index * 100

        # Determine Status
        if m_index > 1:
            status = "OVER MODULATION (Distortion!)"
            color = "red"
        elif m_index == 1:
            status = "CRITICAL MODULATION (100% - Ideal)"
            color = "green"
        else:
            status = "UNDER MODULATION (Standard)"
            color = "blue"

        # Update the Result Labels
        # We use f-strings to format to 3 decimal places (.3f)
        lbl_m_result.config(text=f"{m_index:.3f}")
        lbl_p_result.config(text=f"{m_percent:.1f} %")
        lbl_status.config(text=status, fg=color)

    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers.")


def clear_inputs():
    # Helper function to wipe the boxes clean
    entry_vmax.delete(0, tk.END)
    entry_vmin.delete(0, tk.END)
    lbl_m_result.config(text="-")
    lbl_p_result.config(text="-")
    lbl_status.config(text="Waiting...", fg="black")


# --- 2. THE GUI SETUP ---
window = tk.Tk()
window.title("AM Modulation Calculator")
window.geometry("400x350")

# Header
tk.Label(window, text="AM Index Calculator", font=("Arial", 16, "bold")).pack(pady=10)
tk.Label(window, text="Enter Oscilloscope Readings (Volts)", font=("Arial", 10, "italic")).pack()

# -- Input Section (Frame) --
frame_inputs = tk.Frame(window)
frame_inputs.pack(pady=10)

# Vmax Row
tk.Label(frame_inputs, text="V max (Peak-Peak):").grid(row=0, column=0, padx=10, pady=5)
entry_vmax = tk.Entry(frame_inputs)
entry_vmax.grid(row=0, column=1, padx=10, pady=5)

# Vmin Row
tk.Label(frame_inputs, text="V min (Peak-Peak):").grid(row=1, column=0, padx=10, pady=5)
entry_vmin = tk.Entry(frame_inputs)
entry_vmin.grid(row=1, column=1, padx=10, pady=5)

# -- Buttons --
frame_btns = tk.Frame(window)
frame_btns.pack(pady=10)

btn_calc = tk.Button(frame_btns, text="Calculate", command=calculate_modulation,
                     bg="#4CAF50", fg="white", width=15)  # Green Button
btn_calc.pack(side=tk.LEFT, padx=5)

btn_clear = tk.Button(frame_btns, text="Clear", command=clear_inputs,
                      bg="#f44336", fg="white", width=10)  # Red Button
btn_clear.pack(side=tk.LEFT, padx=5)

# -- Output Section --
tk.Label(window, text="--- Results ---", font=("Arial", 10, "bold")).pack(pady=5)

# Result Grid
frame_results = tk.Frame(window)
frame_results.pack()

tk.Label(frame_results, text="Modulation Index (m):").grid(row=0, column=0, sticky="e")
lbl_m_result = tk.Label(frame_results, text="-", font=("Arial", 12, "bold"))
lbl_m_result.grid(row=0, column=1, sticky="w", padx=10)

tk.Label(frame_results, text="Percentage (%):").grid(row=1, column=0, sticky="e")
lbl_p_result = tk.Label(frame_results, text="-", font=("Arial", 12, "bold"))
lbl_p_result.grid(row=1, column=1, sticky="w", padx=10)

# Status Label (Changes Color)
lbl_status = tk.Label(window, text="Waiting...", font=("Arial", 11, "bold"), fg="gray")
lbl_status.pack(pady=15)

# --- 3. RUN ---
window.mainloop()