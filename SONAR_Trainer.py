import pygame
import numpy as np
import random
import math

# --- Configuration ---
WIDTH, HEIGHT = 1000, 800
WATERFALL_HEIGHT = 650
UI_HEIGHT = HEIGHT - WATERFALL_HEIGHT
FPS = 30

# Colors (Sonar Palette)
BLACK = (0, 0, 0)
DARK_GREEN = (0, 30, 0)
BRIGHT_GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
RED = (255, 50, 50)
CYAN = (0, 255, 255)
WHITE = (255, 255, 255)
BTN_BG = (50, 50, 50)
BTN_HOVER = (80, 80, 80)


# --- Acoustic Physics Entities ---

class Contact:
    def __init__(self, c_type, start_x):
        self.type = c_type  # "MERCHANT", "SUB", "WHALE"
        self.x = float(start_x)
        self.history = []  # List of (x, intensity) tuples for hit detection
        self.active = True
        self.id = random.randint(1000, 9999)
        self.discovered = False

        # Movement Characteristics
        if self.type == "MERCHANT":
            self.width = 8  # Wide noisy signal
            self.intensity = 200  # Bright
            self.speed = random.uniform(-0.2, 0.2)  # Steady slow
            self.wobble = 0.0

        elif self.type == "SUB":
            self.width = 2  # Thin silent signal
            self.intensity = 90  # Faint (hard to see)
            self.speed = random.uniform(-0.1, 0.1)
            self.wobble = 0.0
            self.maneuver_timer = 0

        elif self.type == "WHALE":
            self.width = 4
            self.intensity = 150
            self.speed = 0.5
            self.wobble = 2.0  # Sinusoidal movement
            self.wobble_phase = random.random() * math.pi

    def update(self):
        # Movement Logic
        if self.type == "WHALE":
            self.wobble_phase += 0.05
            self.x += math.sin(self.wobble_phase) * self.wobble + (random.random() - 0.5)

        elif self.type == "SUB":
            self.x += self.speed
            # Random tactical maneuvers
            self.maneuver_timer += 1
            if self.maneuver_timer > 200 and random.random() < 0.02:
                self.speed = random.uniform(-0.5, 0.5)  # Change course
                self.maneuver_timer = 0

        else:  # MERCHANT
            self.x += self.speed

        # Bounds Check
        if self.x < 0: self.x = 0; self.speed *= -1
        if self.x > WIDTH: self.x = WIDTH; self.speed *= -1

        # Record history for click detection (store only X for current frame)
        # We limit history length to screen height later
        self.history.insert(0, self.x)
        if len(self.history) > WATERFALL_HEIGHT:
            self.history.pop()

    def get_signal_slice(self):
        """Returns the intensity contribution to the current scanline."""
        return int(self.x), self.width, self.intensity


# --- Main Application ---

class SonarTrainer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Sonar Analyst Trainer: Passive Broadband Waterfall")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 16)
        self.font_large = pygame.font.SysFont("Consolas", 24, bold=True)

        # The Waterfall Surface (Scrolls down)
        self.waterfall = pygame.Surface((WIDTH, WATERFALL_HEIGHT))
        self.waterfall.fill(BLACK)

        # Game State
        self.contacts = []
        self.score = 0
        self.feedback = "System Ready. Analyzing Acoustic Spectrum..."
        self.feedback_color = CYAN

        # Cursor Selection
        self.selected_pos = None  # (x, y)
        self.cursor_active = False

        # Spawn initial contacts
        self.spawn_contact("MERCHANT")
        self.spawn_contact("SUB")  # The challenge

        # Buttons
        self.btn_sub = pygame.Rect(20, WATERFALL_HEIGHT + 60, 150, 40)
        self.btn_mer = pygame.Rect(190, WATERFALL_HEIGHT + 60, 150, 40)
        self.btn_bio = pygame.Rect(360, WATERFALL_HEIGHT + 60, 150, 40)

    def spawn_contact(self, type_force=None):
        if type_force:
            c_type = type_force
        else:
            r = random.random()
            if r < 0.5:
                c_type = "MERCHANT"
            elif r < 0.8:
                c_type = "WHALE"
            else:
                c_type = "SUB"

        x = random.randint(100, WIDTH - 100)
        self.contacts.append(Contact(c_type, x))

    def generate_scanline(self):
        """Generates one horizontal line of sonar data."""
        # 1. Background Noise (Static)
        # Create an array of random noise
        # Intensity between 0 and 40 (very dark green)
        noise = np.random.randint(0, 40, size=(WIDTH,))

        # 2. Add Contacts
        for c in self.contacts:
            cx, width, intensity = c.get_signal_slice()

            # Simple Gaussian-ish spread
            start = max(0, cx - width * 2)
            end = min(WIDTH, cx + width * 2)

            for i in range(start, end):
                dist = abs(i - cx)
                # Brighter in center
                signal_str = intensity * (1 - (dist / (width * 2 + 1)))
                if signal_str > 0:
                    noise[i] = min(255, noise[i] + signal_str)

        # 3. Create Surface from Array
        # We need to map intensity (0-255) to Green Palette
        # R=0, B=0, G=intensity

        # Create RGB array
        rgb_array = np.zeros((WIDTH, 3), dtype=int)
        rgb_array[:, 1] = noise  # Set Green channel

        # Optimization: Pygame can create surface from buffer, but for a single line
        # drawing lines is actually okay, or pixel array.
        # Let's use pixel array manipulation for speed on the new line surface.

        line_surf = pygame.Surface((WIDTH, 1))

        # Fast pixel setting using surfarray
        # pygame uses (x, y) mapping, so (WIDTH, 1) array
        # We need to stack the RGB to shape (WIDTH, 1, 3)
        pixels = np.zeros((WIDTH, 1, 3), dtype=np.uint8)
        pixels[:, 0, 1] = noise  # Green channel

        # Make loud noises slightly yellow (R+G)
        high_intensity = noise > 180
        pixels[high_intensity, 0, 0] = noise[high_intensity] - 50  # Add some Red

        pygame.surfarray.blit_array(line_surf, pixels)

        return line_surf

    def update_waterfall(self):
        # 1. Shift existing image down by 1 pixel
        # Create a temp copy or just blit to self
        # We want to move (0,0) to (0,1)
        self.waterfall.scroll(0, 1)

        # 2. Generate and Blit new line at (0,0)
        new_line = self.generate_scanline()
        self.waterfall.blit(new_line, (0, 0))

    def handle_click(self, pos):
        mx, my = pos

        # Check if click is in waterfall area
        if my < WATERFALL_HEIGHT:
            self.selected_pos = pos
            self.cursor_active = True
            self.feedback = "Track Selected. Classify Contact below."
            self.feedback_color = WHITE

        # Check Buttons (only if cursor active)
        elif self.cursor_active:
            if self.btn_sub.collidepoint(pos):
                self.classify("SUB")
            elif self.btn_mer.collidepoint(pos):
                self.classify("MERCHANT")
            elif self.btn_bio.collidepoint(pos):
                self.classify("WHALE")

    def classify(self, guess):
        # Logic: Find if the selected pixel touches a contact trace
        # The click Y coordinate represents Time (depth in history)
        # Y=0 is Now, Y=10 is 10 frames ago.

        cursor_x, cursor_y = self.selected_pos

        # Find which contact was near cursor_x at history index cursor_y
        hit = None
        min_dist = 20  # Tolerance

        for c in self.contacts:
            if cursor_y < len(c.history):
                hist_x = c.history[cursor_y]
                dist = abs(hist_x - cursor_x)
                if dist < min_dist:
                    hit = c
                    break

        if hit:
            if hit.type == guess:
                if hit.type == "SUB":
                    self.score += 500
                    self.feedback = "EXCELLENT! Submarine Verified."
                    self.feedback_color = BRIGHT_GREEN
                else:
                    self.score += 100
                    self.feedback = f"Correct. Verified as {hit.type}."
                    self.feedback_color = BRIGHT_GREEN
                hit.discovered = True
            else:
                self.score -= 50
                self.feedback = f"INCORRECT. Signature does not match {guess}."
                self.feedback_color = RED
        else:
            self.feedback = "Miss. Only static noise at that bearing."
            self.feedback_color = YELLOW

        self.cursor_active = False
        self.selected_pos = None

    def draw_ui(self):
        # Draw Separator
        pygame.draw.line(self.screen, WHITE, (0, WATERFALL_HEIGHT), (WIDTH, WATERFALL_HEIGHT), 2)

        # Info Text
        score_surf = self.font_large.render(f"SCORE: {self.score}", True, WHITE)
        self.screen.blit(score_surf, (20, WATERFALL_HEIGHT + 10))

        fb_surf = self.font.render(self.feedback, True, self.feedback_color)
        self.screen.blit(fb_surf, (200, WATERFALL_HEIGHT + 15))

        # Buttons
        self.draw_button(self.btn_sub, "CLASS: SUBMARINE", RED)
        self.draw_button(self.btn_mer, "CLASS: MERCHANT", CYAN)
        self.draw_button(self.btn_bio, "CLASS: BIOLOGIC", BRIGHT_GREEN)

        # Cursor
        if self.cursor_active and self.selected_pos:
            cx, cy = self.selected_pos
            pygame.draw.line(self.screen, RED, (cx - 10, cy), (cx + 10, cy), 2)
            pygame.draw.line(self.screen, RED, (cx, cy - 10), (cx, cy + 10), 2)
            pygame.draw.circle(self.screen, RED, (cx, cy), 15, 1)

            # Draw bearing line
            pygame.draw.line(self.screen, (50, 50, 50), (cx, 0), (cx, WATERFALL_HEIGHT), 1)

    def draw_button(self, rect, text, text_col):
        # Hover effect
        mp = pygame.mouse.get_pos()
        col = BTN_HOVER if rect.collidepoint(mp) else BTN_BG

        pygame.draw.rect(self.screen, col, rect, border_radius=5)
        pygame.draw.rect(self.screen, WHITE, rect, 2, border_radius=5)

        txt = self.font.render(text, True, text_col)
        self.screen.blit(txt, (rect.x + 10, rect.y + 10))

    def run(self):
        running = True
        while running:
            # Event Loop
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    # Debug: Spawn random
                    if event.key == pygame.K_s:
                        self.spawn_contact()

            # Update Logic
            for c in self.contacts:
                c.update()

            # Spawn new contacts rarely
            if random.random() < 0.002:
                self.spawn_contact()

            # Drawing
            self.update_waterfall()
            self.screen.blit(self.waterfall, (0, 0))
            self.draw_ui()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    app = SonarTrainer()
    app.run()