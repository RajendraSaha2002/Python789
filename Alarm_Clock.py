from tkinter import *
import datetime
import time
import winsound
from threading import Thread

root = Tk()
root.geometry("400x200")

Label(root, text="Alarm Clock", font="Helvetica 20 bold", fg="red").pack(pady=10)
Label(root, text="Set Time", font="Helvetica 15 bold").pack()

frame = Frame(root)
frame.pack()

hour = StringVar(root)
hours = [f"{i:02}" for i in range(24)]
hour.set(hours[0])
hrs = OptionMenu(frame, hour, *hours)
hrs.pack(side="left")

minute = StringVar(root)
minutes = [f"{i:02}" for i in range(60)]
minute.set(minutes[0])
mins = OptionMenu(frame, minute, *minutes)
mins.pack(side="left")

second = StringVar(root)
seconds = [f"{i:02}" for i in range(60)]
second.set(seconds[0])
secs = OptionMenu(frame, second, *seconds)
secs.pack(side="left")

def alarm():
    while True:
        set_alarm_time = f"{hour.get()}:{minute.get()}:{second.get()}"
        time.sleep(1)
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        print(current_time, set_alarm_time)
        if current_time == set_alarm_time:
            print("Time to Wake up")
            winsound.PlaySound("sound.wav", winsound.SND_ASYNC)
            break  # Optional: stop after first ring

def Threading():
    t1 = Thread(target=alarm)
    t1.daemon = True
    t1.start()

Button(root, text="Set Alarm", font="Helvetica 15", command=Threading).pack(pady=20)

root.mainloop()