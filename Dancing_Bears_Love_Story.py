import turtle
import time

screen = turtle.Screen()
screen.bgcolor("lightpink")
screen.title("🐻 Bear-y Special Proposal 🐻")
screen.setup(width=900, height=700)


# Function to draw a cartoon bear
def draw_bear(t, x, y, size, color):
    t.penup()
    t.goto(x, y)
    t.setheading(0)

    # Head
    t.color(color)
    t.fillcolor(color)
    t.begin_fill()
    t.circle(size)
    t.end_fill()

    # Ears
    t.penup()
    t.goto(x - size * 0.6, y + size * 0.8)
    t.begin_fill()
    t.circle(size * 0.4)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.6, y + size * 0.8)
    t.begin_fill()
    t.circle(size * 0.4)
    t.end_fill()

    # Eyes
    t.penup()
    t.goto(x - size * 0.3, y + size * 0.3)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.circle(size * 0.15)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.3, y + size * 0.3)
    t.begin_fill()
    t.circle(size * 0.15)
    t.end_fill()

    # Nose
    t.penup()
    t.goto(x, y)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.circle(size * 0.2)
    t.end_fill()

    # Smile
    t.penup()
    t.goto(x - size * 0.3, y - size * 0.2)
    t.pendown()
    t.color("black")
    t.width(3)
    t.setheading(-60)
    t.circle(size * 0.5, 120)

    # Body
    t.penup()
    t.goto(x, y - size)
    t.color(color)
    t.fillcolor(color)
    t.begin_fill()
    t.circle(size * 0.8)
    t.end_fill()

    # Arms
    t.penup()
    t.goto(x - size * 0.8, y - size * 0.5)
    t.begin_fill()
    t.circle(size * 0.3)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.8, y - size * 0.5)
    t.begin_fill()
    t.circle(size * 0.3)
    t.end_fill()


# Create bears
bear1 = turtle.Turtle()
bear1.speed(0)
bear1.hideturtle()

bear2 = turtle.Turtle()
bear2.speed(0)
bear2.hideturtle()

# Animation: Bears walking towards each other
positions = [(-300, -50), (-250, -50), (-200, -50), (-150, -50)]
for pos in positions:
    screen.tracer(0)
    bear1.clear()
    draw_bear(bear1, pos[0], pos[1], 40, "brown")
    screen.update()
    time.sleep(0.3)

positions2 = [(300, -50), (250, -50), (200, -50), (150, -50)]
for pos in positions2:
    screen.tracer(0)
    bear2.clear()
    draw_bear(bear2, pos[0], pos[1], 40, "tan")
    screen.update()
    time.sleep(0.3)

# Final position together
screen.tracer(0)
bear1.clear()
bear2.clear()
draw_bear(bear1, -80, -50, 40, "brown")
draw_bear(bear2, 80, -50, 40, "tan")
screen.update()

time.sleep(0.5)

# Draw heart between them
heart = turtle.Turtle()
heart.hideturtle()
heart.speed(0)
heart.penup()
heart.goto(0, 50)
heart.color("red")
heart.fillcolor("red")
heart.begin_fill()
heart.setheading(0)
heart.left(50)
heart.forward(50)
heart.circle(20, 200)
heart.right(140)
heart.circle(20, 200)
heart.forward(50)
heart.end_fill()

# Add message
text = turtle.Turtle()
text.hideturtle()
text.penup()
text.goto(0, 250)
text.color("darkred")
text.write("Will You Be My Bear Forever? 🐻💕", align="center", font=("Comic Sans MS", 28, "bold"))

text.goto(0, -200)
text.color("purple")
text.write("I Love You Bear-y Much!", align="center", font=("Arial", 22, "italic"))


# Add floating hearts
def draw_small_heart(x, y):
    heart.penup()
    heart.goto(x, y)
    heart.setheading(0)
    heart.color("pink")
    heart.fillcolor("pink")
    heart.begin_fill()
    heart.left(50)
    heart.forward(20)
    heart.circle(8, 200)
    heart.right(140)
    heart.circle(8, 200)
    heart.forward(20)
    heart.end_fill()


heart_positions = [(-200, 180), (200, 180), (-250, 100), (250, 100)]
for pos in heart_positions:
    draw_small_heart(pos[0], pos[1])
    screen.update()
    time.sleep(0.2)

turtle.done()