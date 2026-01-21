import turtle
import time

def draw_diya():
    """Function to draw a diya (lamp)."""
    turtle.color("orange")
    turtle.begin_fill()
    turtle.circle(50, steps=3)
    turtle.end_fill()

    # Flame
    turtle.penup()
    turtle.goto(0, 50)
    turtle.pendown()
    turtle.color("yellow")
    turtle.begin_fill()
    turtle.circle(20)
    turtle.end_fill()

def show_message(message, y_offset):
    """Function to display a message."""
    turtle.penup()
    turtle.goto(0, y_offset)
    turtle.pendown()
    turtle.color("white")
    turtle.write(message, align="center", font=("Arial", 20, "bold"))

def draw_cyber_shield():
    """Function to draw a shield for cyber safety."""
    turtle.penup()
    turtle.goto(0, -50)
    turtle.pendown()
    turtle.color("blue")
    turtle.begin_fill()
    turtle.circle(50, steps=5)
    turtle.end_fill()

def main_animation():
    """Main animation for Diwali wishes and cyber safety."""
    screen = turtle.Screen()
    screen.bgcolor("black")
    screen.title("Diwali Wishes and Cyber Safety")

    # Draw Diya
    turtle.speed(3)
    turtle.penup()
    turtle.goto(0, -150)
    turtle.pendown()
    draw_diya()

    # Show Diwali Wishes
    show_message("Happy Diwali!", 100)
    time.sleep(2)

    # Clear and Show Cyber Safety Message
    turtle.clear()
    draw_cyber_shield()
    show_message("Stay Safe Online!", 100)
    time.sleep(2)

    # Show Combined Message
    turtle.clear()
    show_message("Celebrate Brightness & Stay Protected!", 0)
    time.sleep(3)

    # Close the animation
    turtle.done()

if __name__ == "__main__":
    main_animation()