import turtle
import time

screen = turtle.Screen()
screen.bgcolor("lavender")
screen.title("💝 An Important Question 💝")
screen.setup(width=800, height=600)

pen = turtle.Turtle()
pen.hideturtle()
pen.speed(0)

# Draw question
pen.penup()
pen.goto(0, 200)
pen.color("darkred")
pen.write("Will You Be My Valentine?", align="center", font=("Arial", 32, "bold"))

pen.goto(0, 150)
pen.color("purple")
pen.write("💕", align="center", font=("Arial", 50, "normal"))


# Draw buttons
def draw_button(x, y, width, height, color, text):
    pen.penup()
    pen.goto(x, y)
    pen.pendown()
    pen.fillcolor(color)
    pen.begin_fill()
    for _ in range(2):
        pen.forward(width)
        pen.left(90)
        pen.forward(height)
        pen.left(90)
    pen.end_fill()

    pen.penup()
    pen.goto(x + width / 2, y + 20)
    pen.color("white")
    pen.write(text, align="center", font=("Arial", 24, "bold"))


# Initial button positions
yes_x, yes_y = -200, -50
no_x, no_y = 50, -50
button_width = 150
button_height = 60

draw_button(yes_x, yes_y, button_width, button_height, "green", "YES ✓")
draw_button(no_x, no_y, button_width, button_height, "red", "NO ✗")


# Click handlers
def clicked_yes(x, y):
    pen.clear()
    screen.bgcolor("pink")

    # Draw big heart
    pen.goto(0, 0)
    pen.color("red")
    pen.fillcolor("red")
    pen.begin_fill()
    pen.left(50)
    pen.forward(133)
    pen.circle(50, 200)
    pen.right(140)
    pen.circle(50, 200)
    pen.forward(133)
    pen.end_fill()

    # Success message
    pen.penup()
    pen.goto(0, 200)
    pen.color("darkred")
    pen.write("YAY! 🎉💕🎉", align="center", font=("Arial", 48, "bold"))

    pen.goto(0, 140)
    pen.color("purple")
    pen.write("You Made Me The Happiest!", align="center", font=("Arial", 20, "italic"))

    # Confetti
    import random
    confetti = turtle.Turtle()
    confetti.hideturtle()
    confetti.speed(0)
    colors = ["red", "yellow", "blue", "green", "orange", "pink"]

    for _ in range(100):
        confetti.penup()
        confetti.goto(random.randint(-400, 400), random.randint(-300, 300))
        confetti.color(random.choice(colors))
        confetti.dot(random.randint(5, 15))


def clicked_no(x, y):
    global no_x, no_y
    import random

    # Move "NO" button to random position (dodge!)
    pen.clear()
    no_x = random.randint(-300, 200)
    no_y = random.randint(-200, 200)

    # Redraw everything
    pen.goto(0, 200)
    pen.color("darkred")
    pen.write("Will You Be My Valentine?", align="center", font=("Arial", 32, "bold"))

    pen.goto(0, 150)
    pen.color("purple")
    pen.write("💕", align="center", font=("Arial", 50, "normal"))

    # Make YES button bigger!
    yes_width = button_width + 20
    yes_height = button_height + 10
    draw_button(yes_x, yes_y, yes_width, yes_height, "green", "YES ✓")
    draw_button(no_x, no_y, button_width, button_height, "red", "NO ✗")

    # Hint message
    pen.goto(0, -200)
    pen.color("blue")
    pen.write("Try clicking YES! 😊", align="center", font=("Arial", 18, "italic"))


# Set up click detection
def check_click(x, y):
    # Check if YES button clicked
    if yes_x <= x <= yes_x + button_width and yes_y <= y <= yes_y + button_height:
        clicked_yes(x, y)
    # Check if NO button clicked
    elif no_x <= x <= no_x + button_width and no_y <= y <= no_y + button_height:
        clicked_no(x, y)


screen.onclick(check_click)

pen.goto(0, -200)
pen.color("gray")
pen.write("Click a button!", align="center", font=("Arial", 16, "italic"))

turtle.done()