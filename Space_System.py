import pygame
import math

# --- Initialize Pygame ---
pygame.init()
pygame.font.init()  # Initialize the font module

# --- Constants ---
# Set the dimensions of the screen
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
# Set screen center (for the sun)
CENTER_X = SCREEN_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2

# --- Colors (RGB values) ---
BLACK = (0, 0, 0)  # Background (space)
WHITE = (255, 255, 255)  # For orbits and text
YELLOW = (255, 255, 0)  # Sun
RED = (190, 0, 0)  # Mars
BLUE = (100, 149, 237)  # Earth
GREEN = (0, 150, 0)  # Gas giant-like planet (will reuse for Uranus)
GRAY = (128, 128, 128)  # Mercury
VENUS_YELLOW = (230, 200, 100)  # Venus
JUPITER_BROWN = (210, 180, 140)  # Jupiter
SATURN_GOLD = (210, 210, 160)  # Saturn
URANUS_CYAN = (170, 230, 240)  # Uranus
NEPTUNE_BLUE = (60, 80, 200)  # Neptune
PLUTO_GRAY = (200, 200, 200)  # Pluto

# --- Setup the Display ---
# Create the game window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Area Animation")

# Clock to control the frame rate (FPS)
clock = pygame.time.Clock()

# --- Font ---
# Create a font object. We'll use a default system font.
# The size 14 is small enough to not clutter the screen.
PLANET_FONT = pygame.font.SysFont(None, 16)


# --- Planet Class ---
# We use a class to easily create and manage multiple planets
class Planet:
    def __init__(self, name, orbit_radius, color, planet_radius, speed):
        self.name = name  # Name of the planet
        self.orbit_radius = orbit_radius  # Distance from the sun
        self.color = color  # Planet's color
        self.planet_radius = planet_radius  # Size of the planet
        self.speed = speed  # Orbit speed (radians per frame)
        self.angle = 0  # Current angle in orbit (starts at 0)
        self.x = 0  # Planet's x position
        self.y = 0  # Planet's y position

    def update(self):
        """ Update the planet's position for the new frame """
        # Increase the angle based on speed to make it orbit
        self.angle += self.speed

        # Calculate the new (x, y) position using trigonometry
        # math.cos and math.sin give us the position on a circle
        self.x = CENTER_X + int(self.orbit_radius * math.cos(self.angle))
        self.y = CENTER_Y + int(self.orbit_radius * math.sin(self.angle))

    def draw(self, surface):
        """ Draw the planet and its name on the screen """
        # First, draw the orbit path (a thin white circle)
        pygame.draw.circle(surface, WHITE, (CENTER_X, CENTER_Y), self.orbit_radius, 1)

        # Second, draw the planet itself at its calculated (x, y) position
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.planet_radius)

        # --- Special: Draw Saturn's Rings ---
        if self.name == "Saturn":
            # Draw a thin, slightly larger circle (ellipse) for the rings
            # We create a rectangle for the rings to be drawn in
            ring_rect = pygame.Rect(self.x - self.planet_radius - 5,
                                    self.y - self.planet_radius + 5,
                                    (self.planet_radius + 5) * 2,
                                    (self.planet_radius - 5) * 2)
            pygame.draw.ellipse(surface, SATURN_GOLD, ring_rect, 2)

        # Third, draw the planet's name
        # Create the text surface
        name_surface = PLANET_FONT.render(self.name, True, WHITE)
        # Draw the text slightly above and to the right of the planet
        surface.blit(name_surface, (self.x + self.planet_radius + 2, self.y - self.planet_radius - 2))


# --- Create Planet Objects ---
# We create 9 planets with names and adjusted properties.
# Planet(name, orbit_distance, color, size, speed)
# Speeds are relative (inner planets are faster)

BASE_SPEED = 0.02

planet_mercury = Planet(name="Mercury", orbit_radius=50, color=GRAY, planet_radius=3, speed=BASE_SPEED * 1.6)
planet_venus = Planet(name="Venus", orbit_radius=70, color=VENUS_YELLOW, planet_radius=6, speed=BASE_SPEED * 1.2)
planet_earth = Planet(name="Earth", orbit_radius=90, color=BLUE, planet_radius=6, speed=BASE_SPEED * 1.0)
planet_mars = Planet(name="Mars", orbit_radius=110, color=RED, planet_radius=4, speed=BASE_SPEED * 0.8)
planet_jupiter = Planet(name="Jupiter", orbit_radius=160, color=JUPITER_BROWN, planet_radius=14, speed=BASE_SPEED * 0.4)
planet_saturn = Planet(name="Saturn", orbit_radius=200, color=SATURN_GOLD, planet_radius=11, speed=BASE_SPEED * 0.3)
planet_uranus = Planet(name="Uranus", orbit_radius=240, color=URANUS_CYAN, planet_radius=9, speed=BASE_SPEED * 0.2)
planet_neptune = Planet(name="Neptune", orbit_radius=280, color=NEPTUNE_BLUE, planet_radius=9, speed=BASE_SPEED * 0.1)
planet_pluto = Planet(name="Pluto", orbit_radius=310, color=PLUTO_GRAY, planet_radius=2, speed=BASE_SPEED * 0.05)

# Put all planets in a list to easily update and draw them all
planets = [
    planet_mercury,
    planet_venus,
    planet_earth,
    planet_mars,
    planet_jupiter,
    planet_saturn,
    planet_uranus,
    planet_neptune,
    planet_pluto
]

# --- Main Game Loop ---
running = True
while running:
    # --- 1. Event Handling ---
    # Check for any user events (like closing the window)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- 2. Update Game State ---
    # Update the position of each planet in our list
    for planet in planets:
        planet.update()

    # --- 3. Drawing ---
    # Fill the entire screen with BLACK (to clear the previous frame)
    screen.fill(BLACK)

    # Draw the Sun (a static circle in the center)
    pygame.draw.circle(screen, YELLOW, (CENTER_X, CENTER_Y), 20)

    # Draw each planet
    for planet in planets:
        planet.draw(screen)

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

