import turtle
import random
import time

screen = turtle.Screen()
screen.bgcolor("midnightblue")
screen.title("🌟 Written in the Stars 🌟")
screen.tracer(0)


# Draw star
def draw_star(t, X, Y, Size, color):
    t.penup()
    t.goto(X, Y)
    t.pendown()
    t.color(color)
    t.fillcolor(color)
    t.begin_fill()
    for _ in range(5):
        t.forward(Size)
        t.right(144)
    t.end_fill()


# Create twinkling stars background
star_pen = turtle.Turtle()
star_pen.hideturtle()
star_pen.speed(0)

stars = []
for _ in range(50):
    x = random.randint(-400, 400)
    y = random.randint(-300, 300)
    size = random.randint(5, 15)
    stars.append((x, y, size))

# Draw background stars
for star in stars:
    draw_star(star_pen, star[0], star[1], star[2], "white")

screen.update()
time.sleep(1)

# Draw moon
moon = turtle.Turtle()
moon.hideturtle()
moon.speed(0)
moon.penup()
moon.goto(-200, 150)
moon.color("yellow")
moon.fillcolor("lightyellow")
moon.begin_fill()
moon.circle(50)
moon.end_fill()

# Write message with stars
message_pen = turtle.Turtle()
message_pen.hideturtle()
message_pen.speed(0)
message_pen.color("gold")

# Animate text appearing
messages = [
    ("I", 0, 100, 50),
    ("LOVE", 0, 40, 50),
    ("YOU", 0, -20, 50)
]

for msg, x, y, size in messages:
    message_pen.penup()
    message_pen.goto(x, y)
    message_pen.write(msg, align="center", font=("Arial", size, "bold"))
    screen.update()
    time.sleep(0.5)

    # Add sparkles around text
    for _ in range(5):
        sx = x + random.randint(-80, 80)
        sy = y + random.randint(-30, 30)
        draw_star(star_pen, sx, sy, 8, "yellow")
        screen.update()
        time.sleep(0.1)

time.sleep(1)

# Final question
message_pen.goto(0, -100)
message_pen.color("pink")
message_pen.write("Will You Marry Me? 💕", align="center", font=("Courier", 28, "bold"))

# Draw heart constellation
heart_points = [
    (0, -150), (15, -140), (25, -155), (15, -170), (0, -160),
    (-15, -170), (-25, -155), (-15, -140)
]

for point in heart_points:
    draw_star(star_pen, point[0], point[1], 10, "red")
    screen.update()
    time.sleep(0.2)

screen.tracer(1)
turtle.done()