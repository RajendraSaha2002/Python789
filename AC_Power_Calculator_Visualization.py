import tkinter as tk
from tkinter import messagebox
import cmath
import math


# --- 1. THE LOGIC & DRAWING ---
def calculate_and_draw():
    try:
        # Clear previous drawings
        canvas.delete("all")

        # --- A. Get Inputs ---
        v_mag = float(entry_v_mag.get())
        v_ang = float(entry_v_ang.get())
        i_mag = float(entry_i_mag.get())
        i_ang = float(entry_i_ang.get())

        # --- B. Calculate Physics ---
        # Convert to radians
        v_rad = math.radians(v_ang)
        i_rad = math.radians(i_ang)

        # Phasors
        V = cmath.rect(v_mag, v_rad)
        I = cmath.rect(i_mag, i_rad)

        # Power (S = V * I_conjugate)
        S_complex = V * I.conjugate()

        P = S_complex.real  # Base (Watts)
        Q = S_complex.imag  # Height (VAR)
        S = abs(S_complex)  # Hypotenuse (VA)

        # Power Factor Angle
        theta_deg = v_ang - i_ang
        pf = math.cos(math.radians(theta_deg))

        # --- C. DRAWING LOGIC (The "Pro" Part) ---

        # 1. Define Canvas Center/Start Point
        start_x = 50
        start_y = 250  # Start near bottom-left

        # 2. Determine Scale (Fit triangle into 250px box)
        # We find the largest value (P or Q) to scale the drawing appropriately
        max_val = max(abs(P), abs(Q), 1)  # avoid divide by zero
        scale_factor = 200 / max_val

        # 3. Calculate Line Endpoints
        len_p = P * scale_factor
        len_q = Q * scale_factor  # In Tkinter, Y increases downwards!

        # Coordinates
        # Point A: Origin (start_x, start_y)
        # Point B: End of Real Power (horizontal)
        # Point C: Top of Triangle

        ax, ay = start_x, start_y
        bx, by = start_x + len_p, start_y
        cx, cy = bx, start_y - len_q  # Subtract because Y goes UP screen

        # 4. Draw Lines
        # Base (Real Power P) - Green
        canvas.create_line(ax, ay, bx, by, fill="green", width=3)

        # Height (Reactive Power Q) - Red
        canvas.create_line(bx, by, cx, cy, fill="red", width=3)

        # Hypotenuse (Apparent Power S) - Blue
        canvas.create_line(ax, ay, cx, cy, fill="blue", width=3, dash=(4, 2))

        # 5. Add Text Labels (Manual Values on Triangle)
        # Label P (Bottom)
        canvas.create_text((ax + bx) / 2, ay + 15, text=f"P = {P:.1f} W", fill="green", font=("Arial", 10, "bold"))

        # Label Q (Side)
        canvas.create_text(bx + 35, (by + cy) / 2, text=f"Q = {Q:.1f} VAR", fill="red", font=("Arial", 10, "bold"))

        # Label S (Hypotenuse)
        canvas.create_text((ax + cx) / 2 - 20, (ay + cy) / 2 - 20, text=f"S = {S:.1f} VA", fill="blue",
                           font=("Arial", 10, "bold"))

        # Label Angle
        canvas.create_text(ax + 30, ay - 10 if Q > 0 else ay + 10, text=f"θ={theta_deg:.1f}°")

        # 6. Status Text
        if Q > 0:
            status = "INDUCTIVE (Lagging)\nTriangle points UP"
        elif Q < 0:
            status = "CAPACITIVE (Leading)\nTriangle points DOWN"
        else:
            status = "RESISTIVE (Unity)"

        lbl_result.config(text=f"PF: {abs(pf):.3f}\n{status}")

    except ValueError:
        messagebox.showerror("Error", "Check your number inputs.")


# --- 2. GUI SETUP ---
window = tk.Tk()
window.title("Visual Power Triangle")
window.geometry("600x400")

# --- Left Panel: Inputs ---
frame_left = tk.Frame(window, width=200, padx=10, pady=10)
frame_left.pack(side=tk.LEFT, fill=tk.Y)

tk.Label(frame_left, text="INPUTS", font=("Arial", 12, "bold")).pack(pady=5)

tk.Label(frame_left, text="Voltage Mag (V):").pack()
entry_v_mag = tk.Entry(frame_left)
entry_v_mag.pack()

tk.Label(frame_left, text="Voltage Angle (°):").pack()
entry_v_ang = tk.Entry(frame_left)
entry_v_ang.insert(0, "0")
entry_v_ang.pack()

tk.Label(frame_left, text="Current Mag (A):").pack()
entry_i_mag = tk.Entry(frame_left)
entry_i_mag.pack()

tk.Label(frame_left, text="Current Angle (°):").pack()
entry_i_ang = tk.Entry(frame_left)
entry_i_ang.pack()

btn = tk.Button(frame_left, text="Draw Triangle", command=calculate_and_draw, bg="orange", font=("Arial", 11, "bold"))
btn.pack(pady=20)

lbl_result = tk.Label(frame_left, text="Waiting...", font=("Arial", 10), justify=tk.LEFT)
lbl_result.pack(pady=10)

# --- Right Panel: Drawing Canvas ---
frame_right = tk.Frame(window, bg="white")
frame_right.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

# The Canvas is the "Paper" we draw on
canvas = tk.Canvas(frame_right, bg="white")
canvas.pack(fill=tk.BOTH, expand=True)

# Add a grid for reference
canvas.create_line(50, 250, 400, 250, fill="gray")  # X-axis

# Start
window.mainloop()