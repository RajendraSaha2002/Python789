import turtle
import random
import time

screen = turtle.Screen()
screen.bgcolor("navy")
screen.title("🎆 Surprise! 🎆")
screen.tracer(0)


# Firework particle class
class Particle:
    def __init__(self, x, y, color):
        self.t = turtle.Turtle()
        self.t.hideturtle()
        self.t.speed(0)
        self.t.penup()
        self.t.goto(x, y)
        self.t.color(color)
        self.t.pensize(2)
        self.angle = random.randint(0, 360)
        self.speed = random.randint(5, 15)
        self.life = 30

    def move(self):
        self.t.setheading(self.angle)
        self.t.forward(self.speed)
        self.speed *= 0.95
        self.life -= 1

    def is_alive(self):
        return self.life > 0


# Create fireworks
def create_firework(x, y):
    colors = ["red", "yellow", "orange", "pink", "cyan", "lime", "magenta"]
    particles = []
    for _ in range(30):
        color = random.choice(colors)
        particles.append(Particle(x, y, color))
    return particles


# Animation
all_particles = []
firework_positions = [(0, 0), (-150, 100), (150, 100), (-100, -100), (100, -100)]

# Launch fireworks
for pos in firework_positions:
    all_particles.extend(create_firework(pos[0], pos[1]))

    # Animate particles
    for _ in range(30):
        screen.update()
        for particle in all_particles:
            if particle.is_alive():
                particle.t.clear()
                particle.move()
                particle.t.pendown()
                particle.t.forward(2)
                particle.t.penup()
        time.sleep(0.02)

# Show message
time.sleep(0.5)
message = turtle.Turtle()
message.hideturtle()
message.color("white")
message.penup()
message.goto(0, 200)
message.write("💍 MARRY ME? 💍", align="center", font=("Impact", 48, "bold"))

message.goto(0, 150)
message.color("gold")
message.write("You Light Up My Life!", align="center", font=("Arial", 24, "italic"))

screen.tracer(1)
turtle.done()