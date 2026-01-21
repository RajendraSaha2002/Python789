import turtle
import time

def draw_diya():
    """Function to draw a glowing diya (lamp)."""
    turtle.penup()
    turtle.goto(0, -200)
    turtle.pendown()
    # Base of the diya
    turtle.color("orange")
    turtle.begin_fill()
    turtle.circle(100, steps=3)
    turtle.end_fill()

    # Flame of the diya
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    turtle.color("gold")
    turtle.begin_fill()
    turtle.circle(50, steps=3)
    turtle.end_fill()

    turtle.penup()
    turtle.goto(0, 0)
    turtle.pendown()
    turtle.color("yellow")
    turtle.begin_fill()
    turtle.circle(25, steps=3)
    turtle.end_fill()

def draw_shield():
    """Function to draw a shield with a lock for cyber safety."""
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    # Outer shield
    turtle.color("blue")
    turtle.begin_fill()
    turtle.circle(100, steps=5)
    turtle.end_fill()

    # Inner lock
    turtle.penup()
    turtle.goto(-20, 30)
    turtle.pendown()
    turtle.color("white")
    turtle.width(2)
    turtle.begin_fill()
    turtle.circle(20)
    turtle.end_fill()

    turtle.penup()
    turtle.goto(-20, 50)
    turtle.pendown()
    turtle.width(3)
    turtle.goto(20, 50)

def display_text(message, y, size, color):
    """Function to display a message."""
    turtle.penup()
    turtle.goto(0, y)
    turtle.pendown()
    turtle.color(color)
    turtle.write(message, align="center", font=("Arial", size, "bold"))

def animate_text(messages, y, size, color, delay=1.5):
    """Animate a sequence of messages."""
    for message in messages:
        display_text(message, y, size, color)
        time.sleep(delay)
        turtle.clear()

def main_animation():
    """Main animation combining Diwali wishes and cyber safety."""
    screen = turtle.Screen()
    screen.bgcolor("black")
    screen.title("Diwali Wishes and Cyber Safety")

    turtle.speed(10)

    # Step 1: Draw diya with Diwali message
    draw_diya()
    animate_text(["Light up your life!", "Happy Diwali!"], 200, 24, "orange")

    # Step 2: Draw cyber safety shield with safety message
    draw_shield()
    animate_text(["Protect your online world!", "Stay Cyber Safe!"], 200, 24, "blue")

    # Step 3: Combine messages
    display_text("Celebrate Brightness & Stay Protected!", 0, 20, "white")
    time.sleep(3)

    # End animation
    turtle.done()

if __name__ == "__main__":
    main_animation()