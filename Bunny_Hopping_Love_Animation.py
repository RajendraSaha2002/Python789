import turtle
import time

screen = turtle.Screen()
screen.bgcolor("lightgreen")
screen.title("🐰 Hop Into My Heart 🐰")
screen.setup(width=900, height=700)


def draw_bunny(t, x, y, size):
    t.penup()
    t.goto(x, y)
    t.setheading(0)

    # Body
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    t.circle(size)
    t.end_fill()

    # Head
    t.penup()
    t.goto(x, y + size * 1.3)
    t.begin_fill()
    t.circle(size * 0.7)
    t.end_fill()

    # Ears (long)
    t.penup()
    t.goto(x - size * 0.3, y + size * 1.8)
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    for _ in range(2):
        t.forward(size * 0.3)
        t.left(90)
        t.forward(size * 1.2)
        t.left(90)
    t.end_fill()

    # Inner ear (pink)
    t.penup()
    t.goto(x - size * 0.25, y + size * 1.85)
    t.color("pink")
    t.fillcolor("pink")
    t.begin_fill()
    for _ in range(2):
        t.forward(size * 0.2)
        t.left(90)
        t.forward(size * 0.8)
        t.left(90)
    t.end_fill()

    # Second ear
    t.penup()
    t.goto(x + size * 0.3, y + size * 1.8)
    t.color("white")
    t.fillcolor("white")
    t.begin_fill()
    for _ in range(2):
        t.forward(size * 0.3)
        t.left(90)
        t.forward(size * 1.2)
        t.left(90)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.35, y + size * 1.85)
    t.color("pink")
    t.fillcolor("pink")
    t.begin_fill()
    for _ in range(2):
        t.forward(size * 0.2)
        t.left(90)
        t.forward(size * 0.8)
        t.left(90)
    t.end_fill()

    # Eyes
    t.penup()
    t.goto(x - size * 0.25, y + size * 1.5)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.circle(size * 0.1)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.25, y + size * 1.5)
    t.begin_fill()
    t.circle(size * 0.1)
    t.end_fill()

    # Nose
    t.penup()
    t.goto(x, y + size * 1.2)
    t.color("pink")
    t.fillcolor("pink")
    t.begin_fill()
    t.circle(size * 0.15)
    t.end_fill()

    # Whiskers
    t.penup()
    t.goto(x, y + size * 1.2)
    t.pendown()
    t.color("black")
    t.width(2)

    # Left whiskers
    t.setheading(150)
    t.forward(size * 0.6)
    t.penup()
    t.goto(x, y + size * 1.2)
    t.pendown()
    t.setheading(180)
    t.forward(size * 0.6)
    t.penup()
    t.goto(x, y + size * 1.2)
    t.pendown()
    t.setheading(210)
    t.forward(size * 0.6)

    # Right whiskers
    t.penup()
    t.goto(x, y + size * 1.2)
    t.pendown()
    t.setheading(30)
    t.forward(size * 0.6)
    t.penup()
    t.goto(x, y + size * 1.2)
    t.pendown()
    t.setheading(0)
    t.forward(size * 0.6)
    t.penup()
    t.goto(x, y + size * 1.2)
    t.pendown()
    t.setheading(330)
    t.forward(size * 0.6)


bunny = turtle.Turtle()
bunny.speed(0)
bunny.hideturtle()

# Bunny hopping animation
hop_positions = [
    (-300, -150), (-300, -130),  # hop up
    (-250, -150), (-250, -130),  # hop up
    (-200, -150), (-200, -130),
    (-150, -150), (-150, -130),
    (-100, -150), (-100, -130),
    (-50, -150), (-50, -130),
    (0, -150), (0, -130)
]

screen.tracer(0)
for i, pos in enumerate(hop_positions):
    bunny.clear()
    draw_bunny(bunny, pos[0], pos[1], 40)
    screen.update()
    time.sleep(0.2)

time.sleep(0.5)

# Draw carrot with ring
carrot = turtle.Turtle()
carrot.hideturtle()
carrot.speed(0)

# Carrot body
carrot.penup()
carrot.goto(100, -50)
carrot.color("orange")
carrot.fillcolor("orange")
carrot.begin_fill()
carrot.setheading(240)
for _ in range(3):
    carrot.forward(60)
    carrot.left(120)
carrot.end_fill()

# Carrot top (green leaves)
carrot.penup()
carrot.goto(100, -50)
carrot.color("green")
carrot.fillcolor("green")
carrot.begin_fill()
carrot.setheading(90)
carrot.forward(30)
carrot.left(120)
carrot.forward(30)
carrot.left(120)
carrot.forward(30)
carrot.end_fill()

# Ring on carrot
carrot.penup()
carrot.goto(85, -80)
carrot.color("gold")
carrot.width(5)
carrot.pendown()
carrot.circle(15)

# Diamond on ring
carrot.penup()
carrot.goto(85, -60)
carrot.color("cyan")
carrot.fillcolor("cyan")
carrot.begin_fill()
carrot.setheading(0)
for _ in range(4):
    carrot.forward(10)
    carrot.left(90)
carrot.end_fill()

screen.update()
time.sleep(0.5)

# Message
text = turtle.Turtle()
text.hideturtle()
text.penup()
text.goto(0, 250)
text.color("darkgreen")
text.write("🥕 Will You Hop Into My Life? 🥕", align="center", font=("Comic Sans MS", 26, "bold"))

text.goto(0, 200)
text.color("purple")
text.write("Let's Be Bun-Mates Forever! 🐰💕", align="center", font=("Arial", 20, "italic"))

# Draw grass
grass = turtle.Turtle()
grass.hideturtle()
grass.speed(0)
grass.color("darkgreen")
grass.penup()

for x in range(-400, 400, 30):
    grass.goto(x, -250)
    grass.pendown()
    grass.setheading(90)
    for _ in range(5):
        grass.forward(20)
        grass.backward(20)
        grass.right(20)
    grass.penup()

screen.update()
turtle.done()