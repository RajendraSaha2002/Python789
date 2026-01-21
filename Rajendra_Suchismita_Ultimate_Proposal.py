import turtle
import time
import winsound
import threading
import random
from datetime import datetime

screen = turtle.Screen()
screen.bgcolor("midnightblue")
screen.title("💕 Rajendra & Suchismita - An Eternal Love Story 💕")
screen.setup(width=1100, height=850)

# Global variables
proposal_accepted = False
no_button_clicks = 0
current_scene = 0


# Sound effect function (runs in separate thread)
def play_sound(frequency, duration):
    def sound_thread():
        try:
            winsound.Beep(frequency, duration)
        except:
            pass

    threading.Thread(target=sound_thread, daemon=True).start()


# Background music function (romantic melody)
def play_background_music():
    def music_thread():
        try:
            # Romantic melody loop
            melody = [
                (523, 400), (587, 400), (659, 400), (784, 400),  # C D E G
                (659, 400), (587, 400), (523, 800),  # E D C
                (587, 400), (659, 400), (784, 400), (880, 400),  # D E G A
                (784, 400), (659, 400), (587, 800)  # G E D
            ]
            for freq, dur in melody:
                if proposal_accepted:
                    break
                winsound.Beep(freq, dur)
                time.sleep(0.05)
        except:
            pass

    threading.Thread(target=music_thread, daemon=True).start()


# Save screenshot feature
def save_screenshot():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Rajendra_Suchismita_Proposal_{timestamp}.ps"
        screen.getcanvas().postscript(file=filename)
        print(f"📸 Screenshot saved as: {filename}")
        print("💡 Convert .ps to .png using online tools or ImageMagick")

        # Show save notification
        notif = turtle.Turtle()
        notif.hideturtle()
        notif.penup()
        notif.goto(0, -380)
        notif.color("lime")
        notif.write(f"📸 Screenshot Saved! {timestamp}", align="center", font=("Arial", 12, "bold"))
        play_sound(1200, 150)
        time.sleep(2)
        notif.clear()
    except Exception as e:
        print(f"Screenshot error: {e}")


# Draw moon and stars background
def draw_night_sky():
    sky = turtle.Turtle()
    sky.hideturtle()
    sky.speed(0)

    # Moon
    sky.penup()
    sky.goto(350, 300)
    sky.color("lightyellow")
    sky.fillcolor("lightyellow")
    sky.begin_fill()
    sky.circle(60)
    sky.end_fill()

    # Moon craters
    sky.penup()
    sky.goto(340, 320)
    sky.color("wheat")
    sky.fillcolor("wheat")
    sky.begin_fill()
    sky.circle(15)
    sky.end_fill()

    sky.penup()
    sky.goto(370, 290)
    sky.begin_fill()
    sky.circle(12)
    sky.end_fill()

    # Stars (twinkling effect)
    for _ in range(80):
        x = random.randint(-550, 550)
        y = random.randint(100, 400)
        size = random.randint(2, 6)
        sky.penup()
        sky.goto(x, y)
        sky.color("white")
        sky.dot(size)

    # Shooting star
    sky.penup()
    sky.goto(-400, 350)
    sky.pendown()
    sky.color("yellow")
    sky.width(2)
    sky.setheading(-30)
    for i in range(50):
        sky.forward(3)
        if i % 10 == 0:
            play_sound(1500 + i * 20, 50)

    screen.update()


# Draw Romeo (Rajendra)
def draw_romeo(t, x, y, size):
    # Body (royal suit)
    t.penup()
    t.goto(x, y)
    t.color("darkblue")
    t.fillcolor("royalblue")
    t.begin_fill()
    t.circle(size * 0.8)
    t.end_fill()

    # Gold belt
    t.penup()
    t.goto(x - size * 0.8, y + size * 0.3)
    t.color("gold")
    t.fillcolor("gold")
    t.begin_fill()
    for _ in range(2):
        t.forward(size * 1.6)
        t.left(90)
        t.forward(size * 0.15)
        t.left(90)
    t.end_fill()

    # Head
    t.penup()
    t.goto(x, y + size * 1.3)
    t.color("peachpuff")
    t.fillcolor("peachpuff")
    t.begin_fill()
    t.circle(size * 0.6)
    t.end_fill()

    # Hair (brown)
    t.penup()
    t.goto(x - size * 0.4, y + size * 1.8)
    t.color("saddlebrown")
    t.fillcolor("saddlebrown")
    t.begin_fill()
    t.circle(size * 0.5, 180)
    t.goto(x - size * 0.4, y + size * 1.8)
    t.end_fill()

    # Eyes
    t.penup()
    t.goto(x - size * 0.2, y + size * 1.5)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.circle(size * 0.1)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.2, y + size * 1.5)
    t.begin_fill()
    t.circle(size * 0.1)
    t.end_fill()

    # Eye sparkle
    t.penup()
    t.goto(x - size * 0.18, y + size * 1.52)
    t.color("white")
    t.dot(size * 0.05)
    t.goto(x + size * 0.22, y + size * 1.52)
    t.dot(size * 0.05)

    # Smile
    t.penup()
    t.goto(x - size * 0.25, y + size * 1.2)
    t.pendown()
    t.color("black")
    t.width(2)
    t.setheading(-60)
    t.circle(size * 0.3, 120)

    # Crown (prince)
    t.penup()
    t.goto(x - size * 0.35, y + size * 2.0)
    t.color("gold")
    t.fillcolor("gold")
    t.begin_fill()
    points = []
    for i in range(6):
        points.append((x - size * 0.35 + i * size * 0.14, y + size * 2.0))
        points.append((x - size * 0.35 + i * size * 0.14, y + size * 2.3))
    for px, py in points:
        t.goto(px, py)
    t.goto(x - size * 0.35, y + size * 2.0)
    t.end_fill()

    # Ruby on crown
    t.penup()
    t.goto(x, y + size * 2.25)
    t.color("red")
    t.fillcolor("red")
    t.begin_fill()
    t.circle(size * 0.08)
    t.end_fill()

    # Cape
    t.penup()
    t.goto(x - size * 0.9, y + size * 1.0)
    t.color("purple")
    t.fillcolor("purple")
    t.begin_fill()
    t.setheading(210)
    t.forward(size * 0.7)
    t.right(30)
    t.forward(size * 0.5)
    t.goto(x - size * 0.9, y + size * 1.0)
    t.end_fill()

    # Name tag with date
    t.penup()
    t.goto(x, y - size * 1.1)
    t.color("gold")
    t.write("Rajendra", align="center", font=("Times New Roman", 14, "bold"))
    t.goto(x, y - size * 1.4)
    t.color("lightblue")
    t.write("(Romeo)", align="center", font=("Arial", 10, "italic"))


# Draw Juliet (Suchismita)
def draw_juliet(t, x, y, size):
    # Body (elegant dress)
    t.penup()
    t.goto(x, y)
    t.color("hotpink")
    t.fillcolor("pink")
    t.begin_fill()
    t.circle(size * 0.8)
    t.end_fill()

    # Dress bottom (wider, flowing)
    t.penup()
    t.goto(x - size * 0.7, y - size * 0.3)
    t.fillcolor("lightpink")
    t.begin_fill()
    t.setheading(0)
    for _ in range(2):
        t.forward(size * 1.4)
        t.left(90)
        t.forward(size * 0.6)
        t.left(90)
    t.end_fill()

    # Dress pattern (hearts)
    for hx in [x - 0.3 * size, x, x + 0.3 * size]:
        t.penup()
        t.goto(hx, y - 0.4 * size)
        t.color("red")
        t.write("♥", font=("Arial", 8, "normal"))

    # Golden necklace
    t.penup()
    t.goto(x, y + size * 1.0)
    t.color("gold")
    t.width(3)
    t.pendown()
    t.circle(size * 0.3)

    # Head
    t.penup()
    t.goto(x, y + size * 1.3)
    t.color("peachpuff")
    t.fillcolor("peachpuff")
    t.begin_fill()
    t.circle(size * 0.6)
    t.end_fill()

    # Hair (long, flowing brown)
    t.penup()
    t.goto(x - size * 0.5, y + size * 1.8)
    t.color("saddlebrown")
    t.fillcolor("saddlebrown")
    t.begin_fill()
    t.circle(size * 0.5, 180)
    t.goto(x - size * 0.5, y + size * 1.8)
    t.end_fill()

    # Long hair strands (both sides)
    t.penup()
    t.goto(x - size * 0.55, y + size * 1.3)
    t.begin_fill()
    t.setheading(270)
    for _ in range(2):
        t.forward(size * 1.2)
        t.left(90)
        t.forward(size * 0.25)
        t.left(90)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.3, y + size * 1.3)
    t.begin_fill()
    t.setheading(270)
    for _ in range(2):
        t.forward(size * 1.2)
        t.left(90)
        t.forward(size * 0.25)
        t.left(90)
    t.end_fill()

    # Eyes
    t.penup()
    t.goto(x - size * 0.2, y + size * 1.5)
    t.color("black")
    t.fillcolor("black")
    t.begin_fill()
    t.circle(size * 0.1)
    t.end_fill()

    t.penup()
    t.goto(x + size * 0.2, y + size * 1.5)
    t.begin_fill()
    t.circle(size * 0.1)
    t.end_fill()

    # Eyelashes
    t.width(2)
    for eye_x in [x - size * 0.2, x + size * 0.2]:
        for angle in [-30, 0, 30]:
            t.penup()
            t.goto(eye_x, y + size * 1.6)
            t.pendown()
            t.setheading(90 + angle)
            t.forward(size * 0.15)

    # Eye sparkle
    t.penup()
    t.goto(x - size * 0.18, y + size * 1.52)
    t.color("white")
    t.dot(size * 0.05)
    t.goto(x + size * 0.22, y + size * 1.52)
    t.dot(size * 0.05)

    # Rosy cheeks
    t.penup()
    t.goto(x - size * 0.35, y + size * 1.35)
    t.color("pink")
    t.fillcolor("pink")
    t.begin_fill()
    t.circle(size * 0.12)
    t.end_fill()

    t.goto(x + size * 0.35, y + size * 1.35)
    t.begin_fill()
    t.circle(size * 0.12)
    t.end_fill()

    # Smile
    t.penup()
    t.goto(x - size * 0.25, y + size * 1.2)
    t.pendown()
    t.color("black")
    t.width(2)
    t.setheading(-60)
    t.circle(size * 0.3, 120)

    # Flower crown (colorful)
    flower_colors = ["red", "yellow", "pink", "purple", "orange", "magenta"]
    for i in range(7):
        t.penup()
        angle = i * 51.4  # 360/7
        fx = x + size * 0.45 * turtle.math.cos(turtle.math.radians(angle + 90))
        fy = y + size * 2.05 + size * 0.45 * turtle.math.sin(turtle.math.radians(angle + 90))
        t.goto(fx, fy)
        t.color(flower_colors[i % len(flower_colors)])
        t.fillcolor(flower_colors[i % len(flower_colors)])
        t.begin_fill()
        t.circle(size * 0.13)
        t.end_fill()

        # Flower center
        t.color("yellow")
        t.dot(size * 0.08)

    # Name tag with date
    t.penup()
    t.goto(x, y - size * 1.7)
    t.color("hotpink")
    t.write("Suchismita", align="center", font=("Times New Roman", 14, "bold"))
    t.goto(x, y - size * 2.0)
    t.color("lightpink")
    t.write("(Juliet)", align="center", font=("Arial", 10, "italic"))


# Draw rose with stem
def draw_rose(t, x, y, size):
    # Stem
    t.penup()
    t.goto(x, y)
    t.color("green")
    t.fillcolor("darkgreen")
    t.width(4)
    t.pendown()
    t.setheading(90)
    t.forward(size * 2)

    # Leaves
    t.penup()
    t.goto(x, y + size * 0.8)
    t.setheading(150)
    t.color("green")
    t.fillcolor("limegreen")
    t.begin_fill()
    t.circle(size * 0.3, 90)
    t.left(90)
    t.circle(size * 0.3, 90)
    t.end_fill()

    t.penup()
    t.goto(x, y + size * 1.3)
    t.setheading(30)
    t.begin_fill()
    t.circle(-size * 0.3, 90)
    t.right(90)
    t.circle(-size * 0.3, 90)
    t.end_fill()

    # Rose petals (red)
    t.penup()
    t.goto(x, y + size * 2)
    t.color("darkred")
    t.fillcolor("red")

    # Outer petals
    for i in range(8):
        t.penup()
        angle = i * 45
        px = x + size * 0.4 * turtle.math.cos(turtle.math.radians(angle))
        py = y + size * 2 + size * 0.4 * turtle.math.sin(turtle.math.radians(angle))
        t.goto(px, py)
        t.setheading(angle)
        t.begin_fill()
        t.circle(size * 0.3, 180)
        t.end_fill()

    # Inner petals (darker)
    t.fillcolor("darkred")
    for i in range(6):
        t.penup()
        angle = i * 60
        px = x + size * 0.2 * turtle.math.cos(turtle.math.radians(angle))
        py = y + size * 2 + size * 0.2 * turtle.math.sin(turtle.math.radians(angle))
        t.goto(px, py)
        t.setheading(angle)
        t.begin_fill()
        t.circle(size * 0.2, 180)
        t.end_fill()

    # Center
    t.penup()
    t.goto(x, y + size * 2)
    t.color("maroon")
    t.dot(size * 0.3)


# Draw ring box with opening animation
def draw_ring_box(t, x, y, size, open_angle=0):
    # Box bottom
    t.penup()
    t.goto(x - size * 0.5, y)
    t.color("maroon")
    t.fillcolor("maroon")
    t.begin_fill()
    for _ in range(2):
        t.forward(size)
        t.left(90)
        t.forward(size * 0.4)
        t.left(90)
    t.end_fill()

    # Box lid (rotates when opening)
    t.penup()
    t.goto(x - size * 0.5, y + size * 0.4)
    t.setheading(open_angle)
    t.color("darkred")
    t.fillcolor("darkred")
    t.begin_fill()
    t.forward(size)
    t.left(90)
    t.forward(size * 0.3)
    t.left(90)
    t.forward(size)
    t.left(90)
    t.forward(size * 0.3)
    t.end_fill()

    if open_angle >= 80:
        # Ring inside (visible when open)
        t.penup()
        t.goto(x, y + size * 0.2)
        t.color("gold")
        t.width(5)
        t.pendown()
        t.circle(size * 0.15)

        # Diamond
        t.penup()
        t.goto(x - size * 0.1, y + size * 0.4)
        t.color("cyan")
        t.fillcolor("lightcyan")
        t.begin_fill()
        for _ in range(4):
            t.forward(size * 0.2)
            t.left(90)
        t.end_fill()

        # Diamond sparkle
        t.penup()
        t.goto(x, y + size * 0.5)
        t.color("white")
        t.write("✨", font=("Arial", int(size * 0.3), "normal"))


# Draw castle scene
def draw_castle():
    castle = turtle.Turtle()
    castle.hideturtle()
    castle.speed(0)

    # Ground
    castle.penup()
    castle.goto(-550, -250)
    castle.color("darkgreen")
    castle.fillcolor("darkgreen")
    castle.begin_fill()
    for _ in range(2):
        castle.forward(1100)
        castle.left(90)
        castle.forward(200)
        castle.left(90)
    castle.end_fill()

    # Castle walls
    castle.penup()
    castle.goto(-450, -50)
    castle.color("gray")
    castle.fillcolor("lightgray")
    castle.begin_fill()
    for _ in range(2):
        castle.forward(900)
        castle.left(90)
        castle.forward(200)
        castle.left(90)
    castle.end_fill()

    # Castle towers
    tower_positions = [-350, -100, 150, 400]
    for tx in tower_positions:
        castle.penup()
        castle.goto(tx, 150)
        castle.fillcolor("gray")
        castle.begin_fill()
        for _ in range(2):
            castle.forward(100)
            castle.left(90)
            castle.forward(180)
            castle.left(90)
        castle.end_fill()

        # Tower roof
        castle.penup()
        castle.goto(tx, 330)
        castle.fillcolor("darkred")
        castle.begin_fill()
        castle.goto(tx + 50, 380)
        castle.goto(tx + 100, 330)
        castle.goto(tx, 330)
        castle.end_fill()

        # Windows
        for wy in [200, 260]:
            castle.penup()
            castle.goto(tx + 30, wy)
            castle.color("yellow")
            castle.fillcolor("yellow")
            castle.begin_fill()
            for _ in range(2):
                castle.forward(40)
                castle.left(90)
                castle.forward(30)
                castle.left(90)
            castle.end_fill()

    # Main gate
    castle.penup()
    castle.goto(-100, -50)
    castle.color("saddlebrown")
    castle.fillcolor("saddlebrown")
    castle.begin_fill()
    for _ in range(2):
        castle.forward(200)
        castle.left(90)
        castle.forward(120)
        castle.left(90)
    castle.end_fill()

    # Gate arch
    castle.penup()
    castle.goto(-100, 70)
    castle.fillcolor("saddlebrown")
    castle.begin_fill()
    castle.circle(100, 180)
    castle.goto(-100, 70)
    castle.end_fill()

    screen.update()


# Animation: Rose giving
def animate_rose_giving():
    rose_pen = turtle.Turtle()
    rose_pen.hideturtle()
    rose_pen.speed(0)

    # Draw rose moving from Romeo to Juliet
    positions = [(-120, -100), (-80, -80), (-40, -60), (0, -40), (40, -60), (80, -80), (120, -100)]

    screen.tracer(0)
    for pos in positions:
        rose_pen.clear()
        draw_rose(rose_pen, pos[0], pos[1], 15)
        screen.update()
        play_sound(600 + positions.index(pos) * 50, 100)
        time.sleep(0.3)

    # Final position in Juliet's hands
    time.sleep(0.5)
    play_sound(880, 500)


# Animation: Ring box opening
def animate_ring_box():
    ring_pen = turtle.Turtle()
    ring_pen.hideturtle()
    ring_pen.speed(0)

    screen.tracer(0)

    # Box appears
    draw_ring_box(ring_pen, 0, 80, 40, 0)
    screen.update()
    play_sound(400, 200)
    time.sleep(0.5)

    # Box opens gradually
    for angle in range(0, 95, 5):
        ring_pen.clear()
        draw_ring_box(ring_pen, 0, 80, 40, angle)
        screen.update()
        play_sound(500 + angle * 5, 50)
        time.sleep(0.1)

    # Diamond sparkle sound
    play_sound(1500, 400)
    time.sleep(0.5)


# Scene 1: Opening with night sky and castle
def scene_opening():
    screen.clear()
    screen.bgcolor("midnightblue")
    screen.tracer(0)

    draw_night_sky()
    draw_castle()

    # Title
    title = turtle.Turtle()
    title.hideturtle()
    title.penup()
    title.goto(0, 350)
    title.color("gold")
    title.write("🎭 A Romeo & Juliet Love Story 🎭", align="center", font=("Times New Roman", 26, "bold"))

    title.goto(0, -360)
    title.color("lightblue")
    title.write("📅 Date: October 17, 2025 | 👤 Created by: RajendraSaha2002",
                align="center", font=("Arial", 11, "italic"))

    screen.update()
    play_sound(1000, 600)
    time.sleep(3)


# Scene 2: Characters meet
def scene_characters_meet():
    romeo = turtle.Turtle()
    romeo.hideturtle()
    romeo.speed(0)

    juliet = turtle.Turtle()
    juliet.hideturtle()
    juliet.speed(0)

    # Animation: Walking towards each other
    positions_romeo = [(-400, -150), (-350, -150), (-300, -150), (-250, -150),
                       (-200, -150), (-150, -150), (-120, -150)]
    positions_juliet = [(400, -150), (350, -150), (300, -150), (250, -150),
                        (200, -150), (150, -150), (120, -150)]

    screen.tracer(0)
    for i in range(len(positions_romeo)):
        romeo.clear()
        juliet.clear()
        draw_romeo(romeo, positions_romeo[i][0], positions_romeo[i][1], 40)
        draw_juliet(juliet, positions_juliet[i][0], positions_juliet[i][1], 40)
        screen.update()
        play_sound(400 + i * 50, 150)
        time.sleep(0.4)

    time.sleep(0.5)

    # Heart appears between them
    heart = turtle.Turtle()
    heart.hideturtle()
    heart.speed(0)

    # Animated growing heart
    for heart_size in range(10, 65, 5):
        heart.clear()
        heart.penup()
        heart.goto(0, 20)
        heart.color("red")
        heart.fillcolor("red")
        heart.begin_fill()
        heart.setheading(0)
        heart.left(50)
        heart.forward(heart_size)
        heart.circle(heart_size // 2.5, 200)
        heart.right(140)
        heart.circle(heart_size // 2.5, 200)
        heart.forward(heart_size)
        heart.end_fill()
        screen.update()
        play_sound(600 + heart_size * 5, 80)
        time.sleep(0.1)

    time.sleep(1)


# Scene 3: Rose giving
def scene_rose_giving():
    # Message
    msg = turtle.Turtle()
    msg.hideturtle()
    msg.penup()
    msg.goto(0, 200)
    msg.color("pink")
    msg.write("🌹 Rajendra Gives A Rose To Suchismita 🌹",
              align="center", font=("Comic Sans MS", 20, "bold"))
    screen.update()

    time.sleep(1)
    animate_rose_giving()
    time.sleep(1)


# Scene 4: Ring proposal
def scene_ring_proposal():
    msg = turtle.Turtle()
    msg.hideturtle()
    msg.penup()
    msg.goto(0, 170)
    msg.color("gold")
    msg.write("💍 The Moment of Truth 💍", align="center", font=("Arial", 22, "bold"))
    screen.update()

    time.sleep(1)
    animate_ring_box()
    time.sleep(1)


# Scene 5: Proposal question
def scene_proposal_question():
    screen.tracer(0)

    # Shakespeare quotes
    quote = turtle.Turtle()
    quote.hideturtle()
    quote.penup()

    quotes_list = [
        '"My bounty is as boundless as the sea,',
        'My love as deep; the more I give to thee,',
        'The more I have, for both are infinite."',
        '- William Shakespeare, Romeo & Juliet'
    ]

    y_pos = 260
    for q in quotes_list:
        quote.goto(0, y_pos)
        quote.color("lavender")
        quote.write(q, align="center", font=("Times New Roman", 14, "italic"))
        y_pos -= 25

    # Main proposal
    quote.goto(0, 150)
    quote.color("gold")
    quote.write("💕 Rajendra ❤️ Suchismita 💕", align="center", font=("Comic Sans MS", 26, "bold"))

    quote.goto(0, 110)
    quote.color("hotpink")
    quote.write("Will You Be My Juliet Forever?", align="center", font=("Arial", 22, "bold"))

    screen.update()
    play_sound(800, 800)
    time.sleep(2)


# Draw interactive buttons
def draw_interactive_buttons():
    global yes_button_bounds, no_button_bounds

    screen.tracer(0)

    # YES button
    yes_x, yes_y = -250, -320
    yes_width, yes_height = 200, 80

    btn = turtle.Turtle()
    btn.hideturtle()
    btn.speed(0)
    btn.penup()
    btn.goto(yes_x, yes_y)
    btn.pendown()
    btn.color("gold")
    btn.fillcolor("green")
    btn.begin_fill()
    for _ in range(2):
        btn.forward(yes_width)
        btn.left(90)
        btn.forward(yes_height)
        btn.left(90)
    btn.end_fill()

    # YES border glow
    btn.penup()
    btn.goto(yes_x, yes_y)
    btn.pendown()
    btn.width(4)
    btn.color("yellow")
    for _ in range(2):
        btn.forward(yes_width)
        btn.left(90)
        btn.forward(yes_height)
        btn.left(90)

    btn.penup()
    btn.goto(yes_x + yes_width / 2, yes_y + yes_height / 2.5)
    btn.color("white")
    btn.write("YES! ✓", align="center", font=("Arial", 24, "bold"))

    yes_button_bounds = (yes_x, yes_y, yes_x + yes_width, yes_y + yes_height)

    # NO button
    no_x, no_y = 50, -320
    no_width, no_height = 200, 80

    btn.penup()
    btn.goto(no_x, no_y)
    btn.pendown()
    btn.color("darkred")
    btn.fillcolor("red")
    btn.begin_fill()
    for _ in range(2):
        btn.forward(no_width)
        btn.left(90)
        btn.forward(no_height)
        btn.left(90)
    btn.end_fill()

    btn.penup()
    btn.goto(no_x + no_width / 2, no_y + no_height / 2.5)
    btn.color("white")
    btn.write("NO ✗", align="center", font=("Arial", 24, "bold"))

    no_button_bounds = (no_x, no_y, no_x + no_width, no_y + no_height)

    # Instruction
    btn.penup()
    btn.goto(0, -390)
    btn.color("yellow")
    btn.write("💡 Click a button to answer! | Press 'S' to save screenshot",
              align="center", font=("Arial", 12, "italic"))

    screen.update()


# YES button handler - Celebration!
def handle_yes():
    global proposal_accepted
    proposal_accepted = True

    screen.clear()
    screen.bgcolor("pink")
    screen.tracer(0)

    # Victory music
    celebration_melody = [
        (523, 200), (659, 200), (784, 200), (1047, 200),
        (784, 200), (1047, 400), (1047, 200), (784, 200),
        (659, 200), (784, 800)
    ]

    def play_celebration():
        for freq, dur in celebration_melody:
            play_sound(freq, dur)
            time.sleep(dur / 1000 + 0.05)

    threading.Thread(target=play_celebration, daemon=True).start()

    # Giant heart
    heart = turtle.Turtle()
    heart.hideturtle()
    heart.speed(0)
    heart.penup()
    heart.goto(0, -20)
    heart.color("red")
    heart.fillcolor("red")
    heart.begin_fill()
    heart.left(50)
    heart.forward(180)
    heart.circle(70, 200)
    heart.right(140)
    heart.circle(70, 200)
    heart.forward(180)
    heart.end_fill()

    # Success messages
    msg = turtle.Turtle()
    msg.hideturtle()
    msg.penup()
    msg.goto(0, 300)
    msg.color("darkred")
    msg.write("🎉 SHE SAID YES! 🎉", align="center", font=("Impact", 50, "bold"))

    msg.goto(0, 240)
    msg.color("purple")
    msg.write("Rajendra & Suchismita", align="center", font=("Times New Roman", 32, "bold"))

    msg.goto(0, 200)
    msg.color("hotpink")
    msg.write("Forever Together! 💕", align="center", font=("Comic Sans MS", 26, "italic"))

    msg.goto(0, 160)
    msg.color("gold")
    msg.write("October 17, 2025", align="center", font=("Arial", 20, "bold"))

    msg.goto(0, -220)
    msg.color("darkviolet")
    msg.write('"For never was a story of more joy,"', align="center", font=("Times New Roman", 18, "italic"))

    msg.goto(0, -245)
    msg.write('"Than this of Rajendra and his Suchismita!" 💕', align="center", font=("Times New Roman", 18, "italic"))

    msg.goto(0, -300)
    msg.color("blue")
    msg.write("Created with love by RajendraSaha2002 🎭", align="center", font=("Arial", 14, "bold"))

    msg.goto(0, -360)
    msg.color("gray")
    msg.write("Press 'S' to save this moment! 📸", align="center", font=("Arial", 12, "italic"))

    # Confetti explosion
    confetti = turtle.Turtle()
    confetti.hideturtle()
    confetti.speed(0)
    colors = ["red", "pink", "yellow", "orange", "purple", "blue", "green", "magenta", "cyan"]

    for _ in range(200):
        confetti.penup()
        confetti.goto(random.randint(-550, 550), random.randint(-400, 400))
        confetti.color(random.choice(colors))
        confetti.dot(random.randint(5, 25))

    # Sparkles
    for _ in range(40):
        confetti.penup()
        confetti.goto(random.randint(-500, 500), random.randint(-350, 350))
        confetti.color(random.choice(["gold", "yellow", "white"]))
        confetti.write("✨", font=("Arial", random.randint(15, 35), "normal"))

    # Hearts everywhere
    for _ in range(35):
        confetti.penup()
        confetti.goto(random.randint(-500, 500), random.randint(-350, 350))
        confetti.color(random.choice(["red", "pink", "hotpink", "deeppink"]))
        confetti.write("❤", font=("Arial", random.randint(15, 40), "normal"))

    # Rings
    for _ in range(15):
        confetti.penup()
        confetti.goto(random.randint(-500, 500), random.randint(-300, 300))
        confetti.write("💍", font=("Arial", random.randint(20, 35), "normal"))

    screen.update()


# NO button handler - Dodging!
def handle_no():
    global no_button_bounds, no_button_clicks
    no_button_clicks += 1

    play_sound(300, 250)

    # Redraw everything
    screen.clear()
    screen.bgcolor("midnightblue")
    screen.tracer(0)

    draw_night_sky()
    draw_castle()

    # Characters
    romeo = turtle.Turtle()
    romeo.hideturtle()
    romeo.speed(0)
    draw_romeo(romeo, -120, -150, 40)

    juliet = turtle.Turtle()
    juliet.hideturtle()
    juliet.speed(0)
    draw_juliet(juliet, 120, -150, 40)

    # Heart
    heart = turtle.Turtle()
    heart.hideturtle()
    heart.speed(0)
    heart.penup()
    heart.goto(0, 20)
    heart.color("red")
    heart.fillcolor("red")
    heart.begin_fill()
    heart.left(50)
    heart.forward(60)
    heart.circle(25, 200)
    heart.right(140)
    heart.circle(25, 200)
    heart.forward(60)
    heart.end_fill()

    scene_proposal_question()

    # YES button gets BIGGER!
    yes_width = 200 + no_button_clicks * 25
    yes_height = 80 + no_button_clicks * 12
    yes_x = -280 - no_button_clicks * 12

    btn = turtle.Turtle()
    btn.hideturtle()
    btn.speed(0)
    btn.penup()
    btn.goto(yes_x, -320)
    btn.pendown()
    btn.color("gold")
    btn.fillcolor("green")
    btn.begin_fill()
    for _ in range(2):
        btn.forward(yes_width)
        btn.left(90)
        btn.forward(yes_height)
        btn.left(90)
    btn.end_fill()

    # Glowing border
    btn.penup()
    btn.goto(yes_x, -320)
    btn.pendown()
    btn.width(5)
    btn.color("yellow")
    for _ in range(2):
        btn.forward(yes_width)
        btn.left(90)
        btn.forward(yes_height)
        btn.left(90)

    btn.penup()
    btn.goto(yes_x + yes_width / 2, -280)
    btn.color("white")
    btn.write("YES! ✓", align="center", font=("Arial", 24 + no_button_clicks * 2, "bold"))

    yes_button_bounds = (yes_x, -320, yes_x + yes_width, -320 + yes_height)

    # NO button dodges to random position
    no_x = random.randint(-400, 250)
    no_y = random.randint(-290, 120)
    no_width, no_height = 200, 80

    btn.penup()
    btn.goto(no_x, no_y)
    btn.pendown()
    btn.color("darkred")
    btn.fillcolor("red")
    btn.begin_fill()
    for _ in range(2):
        btn.forward(no_width)
        btn.left(90)
        btn.forward(no_height)
        btn.left(90)
    btn.end_fill()

    btn.penup()
    btn.goto(no_x + no_width / 2, no_y + no_height / 2.5)
    btn.color("white")
    btn.write("NO ✗", align="center", font=("Arial", 24, "bold"))

    no_button_bounds = (no_x, no_y, no_x + no_width, no_y + no_height)

    # Funny messages
    funny_messages = [
        "😄 Oops! The button escaped!",
        "💚 Try the BIG GREEN button instead!",
        "😊 Come on, you know you want to say YES!",
        "🏃 The NO button is shy! Click YES!",
        "😉 Seriously? Click the GLOWING YES button!",
        "💕 Your heart knows the answer is YES!",
        "✨ Destiny says YES! Don't fight it!",
        "🎭 Even Shakespeare says YES!"
    ]

    hint = turtle.Turtle()
    hint.hideturtle()
    hint.penup()
    hint.goto(0, -390)
    hint.color("yellow")
    hint.write(funny_messages[min(no_button_clicks - 1, len(funny_messages) - 1)],
               align="center", font=("Comic Sans MS", 16, "bold"))

    screen.update()


# Click handler
def on_click(x, y):
    if yes_button_bounds[0] <= x <= yes_button_bounds[2] and yes_button_bounds[1] <= y <= yes_button_bounds[3]:
        handle_yes()
    elif no_button_bounds[0] <= x <= no_button_bounds[2] and no_button_bounds[1] <= y <= no_button_bounds[3]:
        handle_no()


# Keyboard handler for screenshot
def on_key_s():
    save_screenshot()


# Main execution
def main():
    print("=" * 60)
    print("🎭 ROMEO & JULIET PROPOSAL ANIMATION 🎭")
    print("=" * 60)
    print("👨 Romeo: Rajendra")
    print("👩 Juliet: Suchismita")
    print("📅 Date: October 17, 2025")
    print("👤 Created by: RajendraSaha2002")
    print("=" * 60)
    print("\n✨ Special Features:")
    print("   🌙 Moon and stars background")
    print("   🏰 Medieval castle setting")
    print("   🎵 Romantic background music (winsound)")
    print("   🌹 Rose giving animation")
    print("   💍 Ring box opening animation")
    print("   🎭 Shakespeare quotes")
    print("   🖱️ Interactive YES/NO buttons")
    print("   📸 Screenshot feature (Press 'S')")
    print("   🎉 Celebration with confetti")
    print("   😄 Funny NO button dodging")
    print("\n🎬 Starting animation...\n")

    # Play opening sound
    play_sound(1200, 400)
    time.sleep(0.5)

    # Start background music
    play_background_music()

    # Run scenes
    scene_opening()
    scene_characters_meet()
    scene_rose_giving()
    scene_ring_proposal()
    scene_proposal_question()
    draw_interactive_buttons()

    # Set up interactions
    screen.onclick(on_click)
    screen.onkey(on_key_s, 's')
    screen.onkey(on_key_s, 'S')
    screen.listen()

    print("✅ Animation ready!")
    print("👆 Click YES or NO button in the window")
    print("📸 Press 'S' key to save screenshot")
    print("=" * 60)

    turtle.done()


if __name__ == "__main__":
    main()