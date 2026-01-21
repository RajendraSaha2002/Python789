import pygame
import random

# --- Initialize Pygame ---
pygame.init()
pygame.font.init()  # Initialize the font module

# --- Constants ---
# Set the dimensions of the screen
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# --- Colors (RGB values) ---
BLACK = (0, 0, 0)  # Background (space)
WHITE = (255, 255, 255)  # Rocket body and stars
RED = (255, 0, 0)  # Rocket fins
YELLOW = (255, 255, 0)  # Flame color 1
ORANGE = (255, 165, 0)  # Flame color 2
EARTH_BLUE = (100, 149, 237)  # Earth color
EARTH_GREEN = (0, 150, 0)  # A bit of land on Earth

# --- Setup the Display ---
# Create the game window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Rocket Launch")

# Clock to control the frame rate (FPS)
clock = pygame.time.Clock()

# --- Font ---
# Create a font object for displaying information
INFO_FONT = pygame.font.SysFont(None, 28)

# --- Create Stars ---
# Create a list of 100 random (x, y) positions for stars
stars = []
for _ in range(100):
    x = random.randint(0, SCREEN_WIDTH)
    y = random.randint(0, SCREEN_HEIGHT)
    stars.append((x, y))

# --- Rocket Initial Position and Speed ---
# Start the rocket at the bottom-center of the screen
rocket_x = SCREEN_WIDTH // 2
rocket_y = SCREEN_HEIGHT - 100
rocket_speed = 3

# --- Earth Rotation ---
# This variable will control the horizontal position of the "land"
land_x_offset = 100

# --- Main Game Loop ---
running = True
while running:
    # --- 1. Event Handling ---
    # Check for any user events (like closing the window)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- 2. Update Game State ---
    # Move the rocket up the screen
    rocket_y -= rocket_speed

    # If the rocket goes off the top of the screen, reset it to the bottom
    # This makes the animation loop
    if rocket_y < -50:
        rocket_y = SCREEN_HEIGHT - 100

    # Update Earth rotation
    # We move the land to the left. When it goes too far, reset it to the right.
    land_x_offset -= 0.5  # Controls the speed of rotation
    if land_x_offset < -150:
        land_x_offset = 250

    # --- 3. Drawing ---
    # Fill the entire screen with BLACK (space)
    screen.fill(BLACK)

    # Draw all the stars
    for x, y in stars:
        pygame.draw.circle(screen, WHITE, (x, y), 1)  # Draw a small 1-pixel star

    # Draw "Earth" at the bottom
    # We draw a very large circle centered below the screen,
    # so only the top curve is visible.
    pygame.draw.circle(screen, EARTH_BLUE, (SCREEN_WIDTH // 2, SCREEN_HEIGHT + 750), 800)
    # Draw a little "land" using the offset to make it move
    pygame.draw.circle(screen, EARTH_GREEN, (SCREEN_WIDTH // 2 + int(land_x_offset), SCREEN_HEIGHT + 700), 100)

    # --- Draw the Rocket ---

    # 1. Draw the Flame (draw this first, so it's "behind" the rocket)
    # We make it flicker by choosing a random height and color each frame
    flame_height = random.randint(20, 35)
    flame_color = random.choice([YELLOW, ORANGE])

    # Flame is a triangle (polygon)
    flame_points = [
        (rocket_x - 8, rocket_y + 12),  # Bottom-left of rocket
        (rocket_x + 8, rocket_y + 12),  # Bottom-right of rocket
        (rocket_x, rocket_y + 12 + flame_height)  # Tip of the flame
    ]
    pygame.draw.polygon(screen, flame_color, flame_points)

    # 2. Draw the Rocket Body (a white rectangle)
    # rect = (left, top, width, height)
    pygame.draw.rect(screen, WHITE, (rocket_x - 10, rocket_y - 20, 20, 35))

    # 3. Draw the Nose Cone (a white triangle)
    nose_points = [
        (rocket_x - 10, rocket_y - 20),  # Top-left of body
        (rocket_x + 10, rocket_y - 20),  # Top-right of body
        (rocket_x, rocket_y - 35)  # Tip of the nose
    ]
    pygame.draw.polygon(screen, WHITE, nose_points)

    # 4. Draw the Fins (red triangles)
    # Left fin
    fin_left_points = [
        (rocket_x - 10, rocket_y + 15),  # Bottom-left of body
        (rocket_x - 10, rocket_y - 5),
        (rocket_x - 18, rocket_y + 18)
    ]
    pygame.draw.polygon(screen, RED, fin_left_points)
    # Right fin
    fin_right_points = [
        (rocket_x + 10, rocket_y + 15),  # Bottom-right of body
        (rocket_x + 10, rocket_y - 5),
        (rocket_x + 18, rocket_y + 18)
    ]
    pygame.draw.polygon(screen, RED, fin_right_points)

    # --- Draw Information Text ---
    # Calculate altitude (how far it has traveled from the start)
    # The starting 'y' is SCREEN_HEIGHT - 100
    altitude = (SCREEN_HEIGHT - 100) - rocket_y

    # Create the text surfaces
    status_text = INFO_FONT.render("STATUS: LAUNCHING", True, WHITE)
    alt_text = INFO_FONT.render(f"ALTITUDE: {altitude} m", True, WHITE)

    # Draw the text to the screen
    screen.blit(status_text, (20, 20))
    screen.blit(alt_text, (20, 50))

    # --- 4. Refresh Screen ---
    # Flip the display to show the new frame
    pygame.display.flip()

    # --- 5. Control Frame Rate ---
    # Wait for a short time to keep the animation at 60 frames per second
    clock.tick(60)

# --- Quit Pygame ---
# This runs after the loop is (running = False)
pygame.font.quit()  # Uninitialize the font module
pygame.quit()

