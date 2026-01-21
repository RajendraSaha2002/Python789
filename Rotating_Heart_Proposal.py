import turtle
import math

# Setup
screen = turtle.Screen()
screen.bgcolor("black")
screen.title("❤️ A Special Message ❤️")

pen = turtle.Turtle()
pen.speed(0)
pen.width(2)


# Draw parametric heart that rotates
def draw_rotating_heart(t, angle):
    pen.clear()
    pen.color("red")
    pen.fillcolor("red")
    pen.begin_fill()
    pen.penup()

    # Parametric heart equations
    for i in range(360):
        rad = math.radians(i)
        x = 16 * math.sin(rad) ** 3
        y = 13 * math.cos(rad) - 5 * math.cos(2 * rad) - 2 * math.cos(3 * rad) - math.cos(4 * rad)

        # Rotate coordinates
        x_rot = x * math.cos(angle) - y * math.sin(angle)
        y_rot = x * math.sin(angle) + y * math.cos(angle)

        pen.goto(x_rot * 10, y_rot * 10)
        if i == 0:
            pen.pendown()

    pen.end_fill()
    pen.hideturtle()


# Animation loop
def animate():
    for angle in range(0, 360, 5):
        draw_rotating_heart(pen, math.radians(angle))
        screen.update()

    # Write message after rotation
    pen.penup()
    pen.goto(0, 200)
    pen.color("pink")
    pen.write("Will You Marry Me Pure Smile?", align="center", font=("Courier", 32, "bold"))

    pen.goto(0, -200)
    pen.color("gold")
    pen.write("💍 Say Yes! 💍", align="center", font=("Arial", 24, "italic"))


screen.tracer(0)
animate()
screen.tracer(1)
turtle.done()