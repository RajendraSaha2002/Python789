import turtle
import time

screen = turtle.Screen()
screen.bgcolor("lightyellow")
screen.title("🦊 Fox-y Love Proposal 🦊")
screen.setup(width=900, height=700)


def draw_fox(t, x, y, size):
    # Body
    t.penup()
    t.goto(x, y)
    t.color("orange")
    t.fillcolor("orange")
    t.begin_fill()
    t.circle(size * 0.8)
    t.end_fill()

    # Head
    t.penup()
    t.goto(x, y + size * 1.2)
    t.begin_fill()
    t.circle(size * 0.6)
    t.end_fill()

    # Ears (triangular)
    t.penup()
    t.goto(x - size * 0.4, y + size * 1.8)
    t.color("orange")
    t.fillcolor("orange")
    t.begin_fill()
    t.setheading(60)
    t.forward(size * 0.5)
    t.right(120)
    t.forward(size * 0.5)
    t.goto(x - size * 0.4, y + size * 1.8)
    t.end_fill()

    # Ear inner (white)
    t.penup()
    t.goto(x - size * 0.35, y + size * 1.85)
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    t.setheading(60)
    t.forward(size * 0.3)
    t.right(120)
    t.forward(size * 0.3)
    t.goto(x - size * 0.35, y + size * 1.85)
    t.end_fill()

    # Right ear
    t.penup()
    t.goto(x + size * 0.4, y + size * 1.8)
    t.color("orange")
    t.fillcolor("orange")
    t.begin_fill()
    t.setheading(120)
    t.forward(size * 0.5)
    t.right(-120)
    t.forward(size * 0.5)
    t.goto(x + size * 0.4, y + size * 1.8)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.35, y + size * 1.85)
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    t.setheading(120)
    t.forward(size * 0.3)
    t.right(-120)
    t.forward(size * 0.3)
    t.goto(x + size * 0.35, y + size * 1.85)
    t.end_fill()

    # White face patch
    t.penup()
    t.goto(x, y + size * 1.0)
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    t.circle(size * 0.35)
    t.end_fill()

    # Eyes
    t.penup()
    t.goto(x - size * 0.2, y + size * 1.35)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.circle(size * 0.1)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.2, y + size * 1.35)
    t.begin_fill()
    t.circle(size * 0.1)
    t.end_fill()

    # Nose
    t.penup()
    t.goto(x, y + size * 1.05)
    t.begin_fill()
    t.circle(size * 0.08)
    t.end_fill()

    # Smile
    t.penup()
    t.goto(x - size * 0.2, y + size * 0.95)
    t.pendown()
    t.setheading(-60)
    t.circle(size * 0.3, 120)

    # Tail (fluffy)
    t.penup()
    t.goto(x - size * 0.7, y - size * 0.3)
    t.color("orange")
    t.fillcolor("orange")
    t.begin_fill()
    t.setheading(200)
    t.circle(size * 0.6, 120)
    t.goto(x - size * 0.7, y - size * 0.3)
    t.end_fill()

    # White tail tip
    t.penup()
    t.goto(x - size * 1.1, y - size * 0.8)
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    t.circle(size * 0.25)
    t.end_fill()


def draw_balloon(t, x, y, color, string_length):
    # Balloon
    t.penup()
    t.goto(x, y)
    t.color(color)
    t.fillcolor(color)
    t.begin_fill()
    t.circle(30)
    t.end_fill()

    # Balloon tie
    t.penup()
    t.goto(x, y - 30)
    t.pendown()
    t.color(color)
    t.width(2)
    t.setheading(270)
    t.forward(10)

    # String
    t.color("gray")
    t.width(1)
    import random
    for _ in range(string_length):
        t.right(random.randint(-20, 20))
        t.forward(10)


fox = turtle.Turtle()
fox.speed(0)
fox.hideturtle()

# Draw fox
screen.tracer(0)
draw_fox(fox, 0, -200, 50)
screen.update()

time.sleep(0.5)

# Balloons rising animation
balloon = turtle.Turtle()
balloon.speed(0)
balloon.hideturtle()

balloon_positions = [
    (0, -100), (0, -50), (0, 0), (0, 50), (0, 100)
]

colors = ["red", "pink", "purple", "hotpink", "red"]

for i, pos in enumerate(balloon_positions):
    balloon.clear()
    draw_balloon(balloon, pos[0], pos[1], colors[i % len(colors)], 10 - i)
    screen.update()
    time.sleep(0.3)

# Final balloon position with message
balloon.clear()

# Multiple balloons
balloon_data = [
    (-120, 200, "red"),
    (-40, 220, "pink"),
    (40, 220, "purple"),
    (120, 200, "hotpink")
]

for bx, by, bc in balloon_data:
    draw_balloon(balloon, bx, by, bc, 25)

screen.update()

# Message on banner
banner = turtle.Turtle()
banner.hideturtle()
banner.speed(0)
banner.penup()
banner.goto(-150, 100)
banner.pendown()
banner.color("white")
banner.fillcolor("white")
banner.begin_fill()
for _ in range(2):
    banner.forward(300)
    banner.right(90)
    banner.forward(50)
    banner.right(90)
banner.end_fill()

# Text on banner
text = turtle.Turtle()
text.hideturtle()
text.penup()
text.goto(0, 115)
text.color("red")
text.write("MARRY ME? 💍", align="center", font=("Comic Sans MS", 24, "bold"))

# Title message
text.goto(0, 280)
text.color("darkorange")
text.write("🦊 You Make My Heart Flutter! 🦊", align="center", font=("Arial", 26, "bold"))

# Bottom message
text.goto(0, -300)
text.color("brown")
text.write("Let's Start Our Adventure Together!", align="center", font=("Arial", 18, "italic"))

# Add hearts floating
hearts = turtle.Turtle()
hearts.hideturtle()
hearts.speed(0)
hearts.color("red")

import random

for _ in range(15):
    x = random.randint(-400, 400)
    y = random.randint(-250, 250)
    hearts.penup()
    hearts.goto(x, y)
    hearts.write("❤", font=("Arial", random.randint(12, 24), "normal"))

screen.update()
turtle.done()