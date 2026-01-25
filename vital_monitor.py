import psycopg2
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import time

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'dbname': 'smart_hospital_db',
    'port': 5432
}

TARGET_DEVICE = 'PM-001'  # Monitoring John Doe's Pacemaker

# Setup Plot
fig, ax = plt.subplots(figsize=(8, 5))
fig.canvas.manager.set_window_title("ICU BEDSIDE MONITOR - PATIENT: JOHN DOE")

x_data = list(range(50))
y_data = [75] * 50  # Initial flat line buffer

line, = ax.plot(x_data, y_data, lw=2, color='green')
ax.set_ylim(0, 350)
ax.set_ylabel("Heart Rate (BPM)")
ax.set_title("Status: STABLE")
ax.grid(True, color='green', linestyle='--', alpha=0.3)
ax.set_facecolor('black')


def fetch_vitals():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT config_value, status_message FROM medical_devices WHERE device_uuid = %s", (TARGET_DEVICE,))
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        print(f"DB Error: {e}")
        return None


def update(frame):
    global y_data

    data = fetch_vitals()
    if not data: return line,

    raw_value, status_msg = data

    try:
        # --- THE VULNERABILITY ---
        # The system expects a Number. If Ransomware sends text, this crashes.
        heart_rate = float(raw_value)

        # 1. Update Data Buffer
        y_data.append(heart_rate)
        y_data = y_data[-50:]  # Keep last 50 points

        line.set_ydata(y_data)

        # 2. Logic: Check Ranges
        if 60 <= heart_rate <= 100:
            # Normal
            line.set_color('green')
            ax.set_facecolor('black')
            ax.set_title(f"Status: STABLE ({int(heart_rate)} BPM) | Msg: {status_msg}")
        elif heart_rate > 200:
            # Lethal / Fibrillation
            line.set_color('red')
            ax.set_facecolor('#330000')  # Dark Red BG
            ax.set_title(f"!!! CRITICAL: FIBRILLATION ({int(heart_rate)} BPM) !!!", color='red', fontweight='bold')
        else:
            line.set_color('yellow')
            ax.set_title(f"Status: WARNING ({int(heart_rate)} BPM)")

    except ValueError:
        # --- RANSOMWARE STATE ---
        # The value was not a number (Encryption detected)
        line.set_color('white')
        ax.set_facecolor('blue')  # Blue Screen of Death style

        # Draw "Crash" line (Flatline at 0 or erratic noise)
        y_data.append(0)
        y_data = y_data[-50:]
        line.set_ydata(y_data)

        ax.set_title(f"SYSTEM FAILURE: {status_msg}", color='white', backgroundcolor='red')
        print(f"[ALERT] Data Corruption detected! Payload: {raw_value}")

    return line,


# Animate every 500ms
ani = animation.FuncAnimation(fig, update, interval=500)
plt.show()