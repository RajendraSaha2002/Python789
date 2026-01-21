import turtle
import time

screen = turtle.Screen()
screen.bgcolor("lavenderblush")
screen.title("🐱 Purr-fact Love Proposal 🐱")
screen.setup(width=900, height=700)


def draw_cat(t, x, y, size, tail_angle=30):
    # Body
    t.penup()
    t.goto(x, y)
    t.color("gray")
    t.fillcolor("lightgray")
    t.begin_fill()
    t.circle(size)
    t.end_fill()

    # Head
    t.penup()
    t.goto(x, y + size * 1.3)
    t.begin_fill()
    t.circle(size * 0.7)
    t.end_fill()

    # Ears (triangular)
    t.penup()
    t.goto(x - size * 0.5, y + size * 1.9)
    t.color("gray")
    t.fillcolor("lightgray")
    t.begin_fill()
    t.setheading(70)
    t.forward(size * 0.4)
    t.right(140)
    t.forward(size * 0.4)
    t.goto(x - size * 0.5, y + size * 1.9)
    t.end_fill()

    # Pink inner ear
    t.penup()
    t.goto(x - size * 0.45, y + size * 1.95)
    t.color("pink")
    t.fillcolor("pink")
    t.begin_fill()
    t.setheading(70)
    t.forward(size * 0.2)
    t.right(140)
    t.forward(size * 0.2)
    t.goto(x - size * 0.45, y + size * 1.95)
    t.end_fill()

    # Right ear
    t.penup()
    t.goto(x + size * 0.5, y + size * 1.9)
    t.color("gray")
    t.fillcolor("lightgray")
    t.begin_fill()
    t.setheading(110)
    t.forward(size * 0.4)
    t.right(-140)
    t.forward(size * 0.4)
    t.goto(x + size * 0.5, y + size * 1.9)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.45, y + size * 1.95)
    t.color("pink")
    t.fillcolor("pink")
    t.begin_fill()
    t.setheading(110)
    t.forward(size * 0.2)
    t.right(-140)
    t.forward(size * 0.2)
    t.goto(x + size * 0.45, y + size * 1.95)
    t.end_fill()

    # Eyes (closed/happy)
    t.penup()
    t.goto(x - size * 0.25, y + size * 1.5)
    t.pendown()
    t.color("black")
    t.width(3)
    t.setheading(200)
    t.circle(size * 0.15, 160)

    t.penup()
    t.goto(x + size * 0.25, y + size * 1.5)
    t.pendown()
    t.setheading(340)
    t.circle(-size * 0.15, 160)

    # Nose
    t.penup()
    t.goto(x, y + size * 1.25)
    t.color("pink")
    t.fillcolor("pink")
    t.begin_fill()
    t.setheading(0)
    for _ in range(3):
        t.forward(size * 0.1)
        t.left(120)
    t.end_fill()

    # Smile
    t.penup()
    t.goto(x - size * 0.15, y + size * 1.2)
    t.pendown()
    t.color("black")
    t.width(2)
    t.setheading(-60)
    t.circle(size * 0.2, 120)

    # Whiskers
    t.width(1)
    # Left
    for angle in [160, 180, 200]:
        t.penup()
        t.goto(x, y + size * 1.25)
        t.pendown()
        t.setheading(angle)
        t.forward(size * 0.5)

    # Right
    for angle in [20, 0, 340]:
        t.penup()
        t.goto(x, y + size * 1.25)
        t.pendown()
        t.setheading(angle)
        t.forward(size * 0.5)

    # Animated tail
    t.penup()
    t.goto(x - size * 0.8, y + size * 0.3)
    t.pendown()
    t.color("gray")
    t.width(8)
    t.setheading(180 + tail_angle)
    t.circle(size * 0.8, 90)


cat = turtle.Turtle()
cat.speed(0)
cat.hideturtle()

# Cat dancing animation (tail wagging)
screen.tracer(0)
tail_angles = [30, 20, 10, 0, -10, -20, -30, -20, -10, 0, 10, 20, 30]

for angle in tail_angles:
    cat.clear()
    draw_cat(cat, 0, -150, 45, angle)
    screen.update()
    time.sleep(0.15)

# Final position
cat.clear()
draw_cat(cat, 0, -150, 45, 15)
screen.update()

# Musical notes floating
notes_symbols = ["♪", "♫", "♬", "♩"]
notes = turtle.Turtle()
notes.hideturtle()
notes.speed(0)

import random

colors = ["purple", "blue", "pink", "red", "orange"]

for _ in range(20):
    x = random.randint(-350, 350)
    y = random.randint(-100, 280)
    notes.penup()
    notes.goto(x, y)
    notes.color(random.choice(colors))
    notes.write(random.choice(notes_symbols), font=("Arial", random.randint(20, 35), "bold"))

screen.update()

# Title
text = turtle.Turtle()
text.hideturtle()
text.penup()
text.goto(0, 280)
text.color("purple")
text.write("🐱 You're Purr-fect For Me! 🐱", align="center", font=("Comic Sans MS", 30, "bold"))

# Main message
text.goto(0, 230)
text.color("hotpink")
text.write("Will You Dance Through Life With Me?", align="center", font=("Arial", 20, "italic"))

# Hearts
text.goto(0, 180)
text.color("red")
text.write("❤️ 💕 ❤️", align="center", font=("Arial", 30, "normal"))

# Bottom message
text.goto(0, -280)
text.color("darkviolet")
text.write("Say MEOW if You Love Me Too! 😻", align="center", font=("Arial", 18, "bold"))

turtle.done()