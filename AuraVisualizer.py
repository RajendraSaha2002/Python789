import pygame
import psycopg2
import math
import random
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'dbname': 'aura_chronicles',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'host': 'localhost',
    'port': '5432'
}

# --- COLORS & SETTINGS ---
DEEP_BG = (20, 10, 20)  # Dark romantic background
TEXT_COLOR = (255, 240, 245)  # Lavender Blush
HEART_COLOR = (220, 20, 60)  # Crimson
FLOWER_CENTER = (255, 215, 0)
WIDTH, HEIGHT = 1200, 800

# --- TIMING SETTINGS ---
TOTAL_POEM_DURATION = 30000  # 30 Seconds total to write all lines
READING_PAUSE = 5000  # 5 Seconds pause after completion before reset


class Heart:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.randint(50, WIDTH - 50)
        self.y = HEIGHT + random.randint(10, 100)
        self.speed = random.uniform(0.5, 2.0)
        self.size = random.uniform(5, 15)
        self.wobble = random.uniform(0, 6.28)
        self.wobble_speed = random.uniform(0.02, 0.05)
        self.alpha = 255

    def move(self):
        self.y -= self.speed
        self.x += math.sin(self.wobble) * 0.5
        self.wobble += self.wobble_speed
        self.alpha -= 0.3  # Slow fade
        if self.y < -50 or self.alpha <= 0:
            self.reset()

    def draw(self, surface):
        # Parametric Heart Equation
        scale = self.size / 15
        points = []
        for t in range(0, 628, 10):  # 0 to 2pi * 100
            rad = t / 100
            x = 16 * math.sin(rad) ** 3
            y = 13 * math.cos(rad) - 5 * math.cos(2 * rad) - 2 * math.cos(3 * rad) - math.cos(4 * rad)
            # Flip Y and center
            points.append((self.x + x * scale, self.y - y * scale))

        if len(points) > 2:
            pygame.draw.lines(surface, HEART_COLOR, True, points, 2)


class Flower:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.bloom_stage = 0
        self.max_radius = random.randint(10, 20)
        self.color = (random.randint(200, 255), random.randint(100, 180), random.randint(180, 220))

    def grow(self):
        if self.bloom_stage < self.max_radius:
            self.bloom_stage += 0.2

    def draw(self, surface):
        if self.bloom_stage > 0:
            for i in range(5):
                angle = math.radians(72 * i)
                ox = self.x + math.cos(angle) * self.bloom_stage
                oy = self.y + math.sin(angle) * self.bloom_stage
                pygame.draw.circle(surface, self.color, (int(ox), int(oy)), int(self.bloom_stage / 1.5))
            pygame.draw.circle(surface, FLOWER_CENTER, (self.x, self.y), int(self.bloom_stage / 3))


def get_lines_from_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT line_text FROM poetic_lines ORDER BY display_order ASC")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return ["Database unavailable.", "Check configuration."]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("The January Aura - 2026")
    clock = pygame.time.Clock()

    # Font Setup
    try:
        # Slightly smaller font to fit 12 lines comfortably
        font_large = pygame.font.SysFont("Georgia", 28, italic=True)
    except:
        font_large = pygame.font.SysFont(None, 28)

    # Objects
    hearts = [Heart() for _ in range(40)]
    flowers = []

    # Load Lines
    lines = get_lines_from_db()
    if not lines: lines = ["Waiting for inspiration..."]

    # Timing Logic
    sequence_start_time = pygame.time.get_ticks()

    # Layout Config
    TOP_MARGIN = 80
    LINE_SPACING = 55

    running = True
    while running:
        dt = clock.tick(60)
        screen.fill(DEEP_BG)

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                flowers.append(Flower(event.pos[0], event.pos[1]))

        # 1. Animate Background (Hearts/Flowers)
        for h in hearts:
            h.move()
            h.draw(screen)
        for f in flowers:
            f.grow()
            f.draw(screen)

        # 2. Animate Poetry (Waterfall Effect)
        current_time = pygame.time.get_ticks()
        elapsed = current_time - sequence_start_time

        # Calculate time budget per line to fit exactly in TOTAL_POEM_DURATION
        line_count = max(len(lines), 1)
        time_per_line = TOTAL_POEM_DURATION / line_count

        # Determine how many lines should be fully visible based on time elapsed
        visible_lines_count = int(elapsed // time_per_line)

        for i in range(len(lines)):
            y_pos = TOP_MARGIN + (i * LINE_SPACING)

            if i < visible_lines_count:
                # CASE A: Line is fully visible (time for this line has passed)
                text_surf = font_large.render(lines[i], True, TEXT_COLOR)
                rect = text_surf.get_rect(center=(WIDTH // 2, y_pos))
                screen.blit(text_surf, rect)

            elif i == visible_lines_count:
                # CASE B: Line is currently being "Typed"
                # Calculate percentage of this specific line's time budget
                line_elapsed = elapsed % time_per_line
                progress = line_elapsed / time_per_line

                # Determine how many characters to show
                char_count = int(len(lines[i]) * progress)
                partial_text = lines[i][:char_count]

                text_surf = font_large.render(partial_text, True, TEXT_COLOR)
                # Left-align the rect calculation slightly so typing looks centered as it grows
                # But simple center works fine for visual effect
                rect = text_surf.get_rect(center=(WIDTH // 2, y_pos))
                screen.blit(text_surf, rect)

        # 3. Reset Logic
        if elapsed > TOTAL_POEM_DURATION + READING_PAUSE:
            # Restart sequence
            sequence_start_time = current_time
            # Optional: Refresh lines from DB to see updates from Java
            new_lines = get_lines_from_db()
            if new_lines: lines = new_lines
            # Clear flowers for fresh start
            flowers.clear()

        # Random automated flowers
        if random.randint(0, 300) == 1:
            flowers.append(Flower(random.randint(50, WIDTH - 50), random.randint(HEIGHT - 150, HEIGHT - 50)))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()