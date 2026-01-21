import pygame
import math
import random
import time

# --- Configuration ---
WIDTH, HEIGHT = 1000, 800
FPS = 60

# Colors
COLOR_SEA = (20, 40, 60)
COLOR_SHIP = (100, 150, 200)
COLOR_TORPEDO = (255, 50, 50)
COLOR_DECOY = (255, 255, 0)
COLOR_TEXT = (200, 255, 200)
COLOR_ALERT = (255, 0, 0)

# Physics Constants
SHIP_MAX_SPEED = 4.0
TURN_RATE = 2.0
TORPEDO_SPEED = 6.5
DETECTION_RANGE = 400


class Ship:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.heading = 0.0  # Degrees (0 is Up)
        self.speed = 2.0  # Cruising speed
        self.rudder = 0.0  # -1 (Left) to 1 (Right)

        self.decoys_active = False
        self.decoy_pos = None  # (x, y)

        self.status = "PATROLLING"  # PATROLLING, EVADING, HIT

    def update(self):
        # Physics: Move based on heading and speed
        # Pygame Y is down, Math Y is up. 0 deg = Up (-Y)
        rad = math.radians(self.heading - 90)

        self.x += math.cos(rad) * self.speed
        self.y += math.sin(rad) * self.speed

        # Turn Logic
        self.heading += self.rudder * TURN_RATE
        self.heading %= 360

        # Decoy trailing
        if self.decoys_active:
            # Drop a decoy 50px behind ship
            back_rad = math.radians(self.heading - 90 + 180)
            dx = self.x + math.cos(back_rad) * 50
            dy = self.y + math.sin(back_rad) * 50
            self.decoy_pos = (dx, dy)

        # Boundary wrap (Open ocean)
        self.x %= WIDTH
        self.y %= HEIGHT

    def draw(self, screen):
        # Draw Ship (Triangle)
        h_rad = math.radians(self.heading - 90)

        # Nose
        p1 = (self.x + math.cos(h_rad) * 20, self.y + math.sin(h_rad) * 20)
        # Rear Left
        p2 = (self.x + math.cos(h_rad + 2.5) * 15, self.y + math.sin(h_rad + 2.5) * 15)
        # Rear Right
        p3 = (self.x + math.cos(h_rad - 2.5) * 15, self.y + math.sin(h_rad - 2.5) * 15)

        color = COLOR_ALERT if self.status == "HIT" else COLOR_SHIP
        pygame.draw.polygon(screen, color, [p1, p2, p3])

        # Draw Decoy
        if self.decoys_active and self.decoy_pos:
            pygame.draw.circle(screen, COLOR_DECOY, (int(self.decoy_pos[0]), int(self.decoy_pos[1])), 5)
            # Tow line
            pygame.draw.line(screen, (100, 100, 100), (self.x, self.y), self.decoy_pos, 1)


class Torpedo:
    def __init__(self, target_ship):
        # Spawn at random edge
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top':
            self.x, self.y = random.randint(0, WIDTH), 0
        elif side == 'bottom':
            self.x, self.y = random.randint(0, WIDTH), HEIGHT
        elif side == 'left':
            self.x, self.y = 0, random.randint(0, HEIGHT)
        else:
            self.x, self.y = WIDTH, random.randint(0, HEIGHT)

        self.target = target_ship
        self.active = True
        self.locked_on_decoy = False

    def update(self):
        if not self.active: return

        # Homing Logic
        # If decoy active, 50% chance to chase decoy
        target_obj = self.target
        if self.target.decoys_active:
            if not self.locked_on_decoy:
                # One time check when countermeasures deploy
                if random.random() < 0.8:  # 80% effectiveness
                    self.locked_on_decoy = True

            if self.locked_on_decoy:
                # Chase the decoy point
                tx, ty = self.target.decoy_pos
            else:
                tx, ty = self.target.x, self.target.y
        else:
            tx, ty = self.target.x, self.target.y

        # Simple Homing
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist < 10:
            self.active = False
            # Check what we hit
            if self.locked_on_decoy and self.target.decoys_active:
                return "DECOY_HIT"
            else:
                return "SHIP_HIT"

        # Move
        self.x += (dx / dist) * TORPEDO_SPEED
        self.y += (dy / dist) * TORPEDO_SPEED

        return "RUNNING"

    def draw(self, screen):
        if self.active:
            pygame.draw.circle(screen, COLOR_TORPEDO, (int(self.x), int(self.y)), 4)
            # Wake trail
            pass


class DefenseComputer:
    """
    The Reflex Logic.
    Simulates: Detection -> Processing (Lag) -> Action.
    """

    def __init__(self, ship):
        self.ship = ship
        self.state = "MONITORING"
        self.processing_start_time = 0
        self.processing_delay = 0
        self.threat_bearing = 0
        self.log = []

    def detect_threat(self, torpedo):
        if self.state != "MONITORING": return

        # Calculate Bearing to Threat relative to Ship Heading
        # 1. Absolute angle to torpedo
        dx = torpedo.x - self.ship.x
        dy = torpedo.y - self.ship.y
        abs_angle_rad = math.atan2(dy, dx)
        abs_angle_deg = math.degrees(abs_angle_rad) + 90  # Convert to compass (0 Up)

        # 2. Relative Bearing (0 to 360)
        # Relative = (Threat_Abs - Ship_Heading)
        rel_bearing = (abs_angle_deg - self.ship.heading) % 360

        self.threat_bearing = rel_bearing
        self.state = "PROCESSING"

        # Simulate Computer Lag (The "Survival Score" Mechanic)
        # Random lag between 0.5s (Fast) and 3.0s (Fatal)
        self.processing_delay = random.uniform(0.5, 3.0)
        self.processing_start_time = time.time()

        self.log_msg(f"CONTACT! High-Freq Noise. Bearing {int(rel_bearing)}.")
        self.log_msg(f"Computing solution... (Lag: {self.processing_delay:.2f}s)")

    def update(self):
        if self.state == "PROCESSING":
            elapsed = time.time() - self.processing_start_time

            if elapsed >= self.processing_delay:
                # Check for "Death by Lag"
                if self.processing_delay > 2.0:
                    self.log_msg("CRITICAL ERROR: SYSTEM TIMEOUT.")
                    self.log_msg("Reaction too slow. IMPACT IMMINENT.")
                    self.state = "FAILED"
                else:
                    self.execute_reflex()

    def execute_reflex(self):
        self.state = "ENGAGED"
        self.ship.status = "EVADING"

        # 1. Throttle Logic
        self.ship.speed = SHIP_MAX_SPEED
        self.log_msg("ACTION: FLANK SPEED.")

        # 2. Rudder Logic (Turn AWAY)
        # If threat is Right (0-180), Turn Left (-1)
        # If threat is Left (180-360), Turn Right (+1)
        # Goal: Put threat at 180 (Stern)
        if 0 <= self.threat_bearing < 180:
            self.ship.rudder = -1.0  # Hard Left
            self.log_msg(f"ACTION: HARD LEFT (Threat at {int(self.threat_bearing)}°)")
        else:
            self.ship.rudder = 1.0  # Hard Right
            self.log_msg(f"ACTION: HARD RIGHT (Threat at {int(self.threat_bearing)}°)")

        # 3. Countermeasures
        self.ship.decoys_active = True
        self.log_msg("ACTION: NIXIE DECOY DEPLOYED.")

    def log_msg(self, text):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {text}")
        if len(self.log) > 5: self.log.pop(0)


class TorpedoSim:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Automated Defense Reflex Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 16)
        self.font_big = pygame.font.SysFont("Consolas", 32, bold=True)

        self.reset_sim()

    def reset_sim(self):
        self.ship = Ship()
        self.computer = DefenseComputer(self.ship)
        self.torpedo = None
        self.game_over = False
        self.result_text = ""

    def run(self):
        running = True
        while running:
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t and not self.torpedo:
                        # Spawn Threat
                        self.torpedo = Torpedo(self.ship)
                        self.computer.detect_threat(self.torpedo)
                    elif event.key == pygame.K_r:
                        self.reset_sim()

            if not self.game_over:
                # Updates
                self.ship.update()
                self.computer.update()

                if self.torpedo:
                    status = self.torpedo.update()

                    # Detection check (Simulate sensor range)
                    dist = math.hypot(self.torpedo.x - self.ship.x, self.torpedo.y - self.ship.y)

                    # End Conditions
                    if status == "SHIP_HIT":
                        self.ship.status = "HIT"
                        self.game_over = True
                        self.result_text = "SHIP DESTROYED"
                        self.computer.log_msg("HULL BREACH DETECTED.")
                    elif status == "DECOY_HIT":
                        self.game_over = True
                        self.result_text = "THREAT NEUTRALIZED (Decoy Hit)"
                        self.computer.log_msg("Torpedo detonated on Decoy.")

            # Drawing
            self.screen.fill(COLOR_SEA)

            # Grid
            for x in range(0, WIDTH, 100):
                pygame.draw.line(self.screen, (30, 50, 70), (x, 0), (x, HEIGHT))
            for y in range(0, HEIGHT, 100):
                pygame.draw.line(self.screen, (30, 50, 70), (0, y), (WIDTH, y))

            self.ship.draw(self.screen)

            if self.torpedo:
                self.torpedo.draw(self.screen)
                # Draw bearing line if detected
                pygame.draw.line(self.screen, (50, 50, 50), (self.ship.x, self.ship.y),
                                 (self.torpedo.x, self.torpedo.y), 1)

            # UI Overlay
            self.draw_ui()

            if self.game_over:
                # Center Message
                col = COLOR_ALERT if "DESTROYED" in self.result_text else COLOR_DECOY
                text = self.font_big.render(self.result_text, True, col)
                rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
                pygame.draw.rect(self.screen, (0, 0, 0), rect.inflate(20, 20))
                self.screen.blit(text, rect)

                sub = self.font.render("Press 'R' to Reset", True, (255, 255, 255))
                self.screen.blit(sub, (WIDTH // 2 - 60, HEIGHT // 2 + 40))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

    def draw_ui(self):
        # Dashboard Panel
        panel_rect = pygame.Rect(10, 10, 350, 180)
        pygame.draw.rect(self.screen, (0, 0, 0, 200), panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), panel_rect, 2)

        # Header
        head = self.font.render("AUTOMATED DEFENSE CONTROLLER", True, (0, 255, 255))
        self.screen.blit(head, (20, 20))

        # State
        state_col = (0, 255, 0) if self.computer.state == "MONITORING" else (255, 165, 0)
        if self.computer.state == "FAILED": state_col = (255, 0, 0)

        state_txt = self.font.render(f"SYSTEM STATE: {self.computer.state}", True, state_col)
        self.screen.blit(state_txt, (20, 45))

        # Logs
        for i, msg in enumerate(self.computer.log):
            c = (255, 255, 255)
            if "CRITICAL" in msg or "CONTACT" in msg: c = (255, 50, 50)
            if "ACTION" in msg: c = (50, 200, 255)

            txt = self.font.render(msg, True, c)
            self.screen.blit(txt, (20, 75 + i * 18))

        # Instruction
        if not self.torpedo and not self.game_over:
            ins = self.font.render("Press 'T' to Inject Torpedo Threat", True, (150, 150, 150))
            self.screen.blit(ins, (10, HEIGHT - 30))


if __name__ == "__main__":
    sim = TorpedoSim()
    sim.run()