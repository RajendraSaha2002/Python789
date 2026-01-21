
import psutil
from win10toast import ToastNotifier

battery = psutil.sensors_battery()
if battery is None:
    print("No battery information found.")
else:
    plugged = battery.power_plugged
    percent = battery.percent

    if percent <= 30 and not plugged:
        toaster = ToastNotifier()
        toaster.show_toast(
            "Battery Low",
            f"{percent}% Battery remaining!",
            duration=5,
            threaded=True
        )