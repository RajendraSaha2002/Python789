import turtle
import time

screen = turtle.Screen()
screen.bgcolor("lightcyan")
screen.title("🐧 Penguin Perfect Match 🐧")
screen.setup(width=900, height=700)


def draw_penguin(t, x, y, size):
    # Body (black)
    t.penup()
    t.goto(x, y)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.setheading(0)
    t.circle(size, 180)
    t.goto(x, y)
    t.end_fill()

    # Belly (white)
    t.penup()
    t.goto(x, y + size * 0.2)
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    t.circle(size * 0.6, 180)
    t.goto(x, y + size * 0.2)
    t.end_fill()

    # Head
    t.penup()
    t.goto(x, y + size * 1.5)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.circle(size * 0.5)
    t.end_fill()

    # White face patch
    t.penup()
    t.goto(x - size * 0.15, y + size * 1.6)
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    t.circle(size * 0.25)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.15, y + size * 1.6)
    t.begin_fill()
    t.circle(size * 0.25)
    t.end_fill()

    # Eyes
    t.penup()
    t.goto(x - size * 0.15, y + size * 1.7)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.circle(size * 0.08)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.15, y + size * 1.7)
    t.begin_fill()
    t.circle(size * 0.08)
    t.end_fill()

    # Beak
    t.penup()
    t.goto(x, y + size * 1.5)
    t.color("orange")
    t.fillcolor("orange")
    t.begin_fill()
    t.setheading(270)
    t.forward(size * 0.3)
    t.left(120)
    t.forward(size * 0.3)
    t.left(120)
    t.forward(size * 0.3)
    t.end_fill()

    # Feet
    t.penup()
    t.goto(x - size * 0.3, y - size * 0.1)
    t.color("orange")
    t.fillcolor("orange")
    t.begin_fill()
    t.setheading(0)
    t.forward(size * 0.4)
    t.left(120)
    t.forward(size * 0.3)
    t.left(120)
    t.forward(size * 0.3)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.3, y - size * 0.1)
    t.begin_fill()
    t.setheading(0)
    t.forward(size * 0.4)
    t.left(120)
    t.forward(size * 0.3)
    t.left(120)
    t.forward(size * 0.3)
    t.end_fill()

    # Wings
    t.penup()
    t.goto(x - size * 0.7, y + size * 0.8)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.setheading(220)
    t.circle(size * 0.5, 100)
    t.goto(x - size * 0.7, y + size * 0.8)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.7, y + size * 0.8)
    t.begin_fill()
    t.setheading(320)
    t.circle(size * 0.5, -100)
    t.goto(x + size * 0.7, y + size * 0.8)
    t.end_fill()


penguin1 = turtle.Turtle()
penguin1.speed(0)
penguin1.hideturtle()

penguin2 = turtle.Turtle()
penguin2.speed(0)
penguin2.hideturtle()

# Draw ice/snow ground
ice = turtle.Turtle()
ice.hideturtle()
ice.speed(0)
ice.penup()
ice.goto(-450, -200)
ice.pendown()
ice.color("white")
ice.fillcolor("white")
ice.begin_fill()
for _ in range(2):
    ice.forward(900)
    ice.left(90)
    ice.forward(100)
    ice.left(90)
ice.end_fill()

# Penguin sliding animation
screen.tracer(0)
slide_positions = [(-350, -150), (-300, -150), (-250, -150), (-200, -150), (-150, -150)]

for pos in slide_positions:
    penguin1.clear()
    draw_penguin(penguin1, pos[0], pos[1], 35)
    screen.update()
    time.sleep(0.2)

# Second penguin
slide_positions2 = [(350, -150), (300, -150), (250, -150), (200, -150), (150, -150)]

for pos in slide_positions2:
    penguin2.clear()
    draw_penguin(penguin2, pos[0], pos[1], 35)
    screen.update()
    time.sleep(0.2)

# Final position
penguin1.clear()
penguin2.clear()
draw_penguin(penguin1, -70, -150, 35)
draw_penguin(penguin2, 70, -150, 35)
screen.update()

time.sleep(0.5)

# Draw fish with ring
fish = turtle.Turtle()
fish.hideturtle()
fish.speed(0)
fish.penup()
fish.goto(0, 50)
fish.color("blue")
fish.fillcolor("lightblue")
fish.begin_fill()
# Fish body
fish.circle(30, 180)
fish.setheading(270)
fish.forward(60)
fish.setheading(180)
fish.circle(30, 180)
fish.end_fill()

# Ring on fish
fish.penup()
fish.goto(0, 30)
fish.color("gold")
fish.width(6)
fish.pendown()
fish.circle(20)

# Diamond
fish.penup()
fish.goto(-5, 52)
fish.color("pink")
fish.fillcolor("pink")
fish.begin_fill()
for _ in range(4):
    fish.forward(10)
    fish.left(90)
fish.end_fill()

screen.update()

# Messages
text = turtle.Turtle()
text.hideturtle()
text.penup()
text.goto(0, 250)
text.color("navy")
text.write("🐧 You're My Penguin! 🐧", align="center", font=("Comic Sans MS", 32, "bold"))

text.goto(0, 200)
text.color("darkblue")
text.write("Will You Waddle Through Life With Me?", align="center", font=("Arial", 20, "italic"))

# Snowflakes
import random

snow = turtle.Turtle()
snow.hideturtle()
snow.speed(0)
snow.color("white")

for _ in range(30):
    x = random.randint(-400, 400)
    y = random.randint(-100, 300)
    snow.penup()
    snow.goto(x, y)
    snow.write("❄", font=("Arial", random.randint(10, 20), "normal"))

screen.update()
turtle.done()