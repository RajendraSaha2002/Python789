# temperature_converter.py

import tkinter as tk

def convert():
    celsius = float(entry.get())
    fahrenheit = (celsius * 9/5) + 32
    result_label.config(text=f"{fahrenheit:.2f} °F")

root = tk.Tk()
root.title("Temperature Converter")

tk.Label(root, text="Celsius:").pack()
entry = tk.Entry(root)
entry.pack()

tk.Button(root, text="Convert", command=convert).pack()
result_label = tk.Label(root, text="")
result_label.pack()

root.mainloop()
# This code creates a simple GUI application to convert Celsius to Fahrenheit.
# It uses the tkinter library to create the interface.