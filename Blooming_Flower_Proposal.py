import turtle
import time

screen = turtle.Screen()
screen.bgcolor("lightblue")
screen.title("🌸 Watch This Bloom 🌸")

pen = turtle.Turtle()
pen.speed(0)


# Draw flower petals
def draw_petal(t, radius):
    t.color("hotpink")
    t.fillcolor("pink")
    t.begin_fill()
    t.circle(radius, 60)
    t.left(120)
    t.circle(radius, 60)
    t.left(120)
    t.end_fill()


# Draw complete flower
def draw_flower(x, y, size):
    pen.penup()
    pen.goto(x, y)
    pen.pendown()

    # Draw 6 petals
    for _ in range(6):
        draw_petal(pen, size)
        pen.left(60)

    # Draw center
    pen.color("gold")
    pen.fillcolor("yellow")
    pen.begin_fill()
    pen.circle(size / 3)
    pen.end_fill()


# Draw stem
def draw_stem(x, y):
    pen.color("green")
    pen.width(5)
    pen.penup()
    pen.goto(x, y)
    pen.pendown()
    pen.setheading(270)
    pen.forward(150)

    # Draw leaves
    pen.setheading(225)
    pen.circle(30, 90)
    pen.penup()
    pen.goto(x, y - 75)
    pen.pendown()
    pen.setheading(315)
    pen.circle(-30, 90)


# Animate blooming
pen.hideturtle()
draw_stem(0, -50)

# Bloom animation (growing flower)
for size in range(10, 70, 3):
    pen.clear()
    draw_stem(0, -50)
    draw_flower(0, -50, size)
    screen.update()
    time.sleep(0.05)

# Add proposal text
time.sleep(0.5)
pen.penup()
pen.goto(0, 150)
pen.color("darkred")
pen.write("I LOVE YOU! 💕", align="center", font=("Comic Sans MS", 36, "bold"))

pen.goto(0, 100)
pen.color("purple")
pen.write("Will You Be Mine Forever?", align="center", font=("Arial", 22, "italic"))

# Add decorative hearts
heart_pos = [(-150, 120), (150, 120), (-150, -180), (150, -180)]
for pos in heart_pos:
    pen.goto(pos)
    pen.color("red")
    pen.write("❤️", font=("Arial", 30, "normal"))

turtle.done()