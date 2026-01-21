import pygame
import math
import random
import numpy as np

# --- Configuration ---
WIDTH, HEIGHT = 1000, 700
FPS = 60

# Colors
COLOR_BG = (20, 20, 25)
COLOR_GRID = (40, 40, 50)
COLOR_TANK_HULL = (60, 100, 60)
COLOR_TANK_TURRET = (80, 120, 80)
COLOR_LASER = (255, 0, 0)
COLOR_SMOKE = (200, 200, 200)
COLOR_UI_BG = (30, 30, 30)
COLOR_TEXT_WARN = (255, 50, 50)
COLOR_TEXT_NORMAL = (0, 255, 0)

# Physics / Logic Constants
TURRET_SLEW_RATE = 5.0  # Degrees per frame
SMOKE_DURATION = 180  # Frames (3 seconds)
SMOKE_DISPERSAL_SPEED = 2.0


class SmokeParticle:
    def __init__(self, x, y, angle_deg):
        self.x = x
        self.y = y
        self.radius = random.randint(10, 20)
        self.life = 255

        # Velocity vector based on deployment angle
        rad = math.radians(angle_deg - 90)  # Adjust for PyGame coord system
        spread = random.uniform(-0.5, 0.5)
        speed = random.uniform(2.0, 4.0)

        self.vx = math.cos(rad + spread) * speed
        self.vy = math.sin(rad + spread) * speed

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.radius += 0.5  # Expand
        self.life -= 2  # Fade
        self.vx *= 0.95  # Drag
        self.vy *= 0.95

    def draw(self, screen):
        if self.life > 0:
            s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            alpha = max(0, min(255, int(self.life)))
            pygame.draw.circle(s, (200, 200, 200, alpha), (self.radius, self.radius), self.radius)
            screen.blit(s, (self.x - self.radius, self.y - self.radius))


class TankSystem:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.hull_angle = 0
        self.turret_angle = 0
        self.target_angle = 0  # Where the FCS wants the turret to be

        # State
        self.lws_active = False  # Laser Warning Receiver state
        self.threat_sector = None
        self.smoke_canisters = 12  # 3 per quadrant
        self.particles = []
        self.warning_timer = 0

    def trigger_lws(self, angle_deg, sector_name):
        """
        Event Handler: Called when a sensor detects a laser.
        """
        self.lws_active = True
        self.threat_sector = sector_name
        self.warning_timer = 60  # Show alert for 1 second

        # 1. Automatic Turret Slew Logic
        self.target_angle = angle_deg

        # 2. Automated Smoke Deployment
        if self.smoke_canisters > 0:
            self.deploy_smoke(angle_deg)
            self.smoke_canisters -= 1

    def deploy_smoke(self, angle):
        # Spawn cloud of particles
        count = 20
        # Eject from turret sides roughly
        # Calculate emitter position on circle
        rad = math.radians(angle - 90)
        ex = self.x + math.cos(rad) * 40
        ey = self.y + math.sin(rad) * 40

        for _ in range(count):
            self.particles.append(SmokeParticle(ex, ey, angle))

    def update(self):
        # Turret Slew Physics (Linear Interpolation with shortest path)
        diff = (self.target_angle - self.turret_angle + 180) % 360 - 180
        if abs(diff) < TURRET_SLEW_RATE:
            self.turret_angle = self.target_angle
        else:
            direction = 1 if diff > 0 else -1
            self.turret_angle += direction * TURRET_SLEW_RATE
            self.turret_angle %= 360

        # Warning Timer
        if self.warning_timer > 0:
            self.warning_timer -= 1
        else:
            self.lws_active = False

        # Smoke Physics
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, screen):
        # Draw Smoke (Under tank? usually over, but for visibility lets draw under barrel, over hull)
        # Actually smoke obscures everything, draw last.
        pass

    def draw_hull(self, screen):
        # Simple Rectangle rotated
        rect_surf = pygame.Surface((60, 100), pygame.SRCALPHA)
        pygame.draw.rect(rect_surf, COLOR_TANK_HULL, (0, 0, 60, 100), border_radius=5)
        # Tracks
        pygame.draw.rect(rect_surf, (30, 30, 30), (0, 0, 10, 100))
        pygame.draw.rect(rect_surf, (30, 30, 30), (50, 0, 10, 100))

        rotated_hull = pygame.transform.rotate(rect_surf, -self.hull_angle)
        rect = rotated_hull.get_rect(center=(self.x, self.y))
        screen.blit(rotated_hull, rect)

    def draw_turret(self, screen):
        # Create Turret Surface
        t_surf = pygame.Surface((100, 100), pygame.SRCALPHA)

        # Main Gun Barrel
        pygame.draw.rect(t_surf, (40, 60, 40), (45, 0, 10, 50))
        # Turret Body
        pygame.draw.circle(t_surf, COLOR_TANK_TURRET, (50, 50), 30)
        # Hatch
        pygame.draw.circle(t_surf, (50, 80, 50), (50, 50), 12)

        # Rotate
        # Pygame rotation is counter-clockwise, 0 is up?
        # Actually 0 is usually Right in math, Up in pygame transform if drawn Up.
        # We drew barrel Up (y=0).
        rotated_turret = pygame.transform.rotate(t_surf, -self.turret_angle)
        rect = rotated_turret.get_rect(center=(self.x, self.y))
        screen.blit(rotated_turret, rect)

    def draw_smoke(self, screen):
        for p in self.particles:
            p.draw(screen)


class SensorButton:
    def __init__(self, label, angle, x, y, w, h):
        self.label = label
        self.angle = angle
        self.rect = pygame.Rect(x, y, w, h)
        self.color = (50, 50, 50)
        self.hover = False

    def draw(self, screen):
        col = (100, 100, 100) if self.hover else self.color
        pygame.draw.rect(screen, col, self.rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=5)

        # Draw Arrow indicator
        cx, cy = self.rect.center
        rad = math.radians(self.angle - 90)
        end_x = cx + math.cos(rad) * 20
        end_y = cy + math.sin(rad) * 20
        pygame.draw.line(screen, (255, 0, 0), (cx, cy), (end_x, end_y), 3)

        # Label
        font = pygame.font.SysFont("Arial", 12, bold=True)
        text = font.render(self.label, True, (255, 255, 255))
        screen.blit(text, (self.rect.x + 5, self.rect.y + 5))


class LWSApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Laser Warning System (LWS) & Automated Defense")
        self.clock = pygame.time.Clock()
        self.font_ui = pygame.font.SysFont("Consolas", 16)
        self.font_alert = pygame.font.SysFont("Arial", 40, bold=True)

        self.tank = TankSystem(WIDTH // 2, HEIGHT // 2)

        # Define Sensors (Buttons)
        self.buttons = [
            SensorButton("FRONT (0°)", 0, 50, 200, 120, 60),
            SensorButton("RIGHT (90°)", 90, WIDTH - 170, 300, 120, 60),
            SensorButton("REAR (180°)", 180, 50, 400, 120, 60),
            SensorButton("LEFT (270°)", 270, 50, 300, 120, 60)
        ]

        # Move Front button to top center ish
        self.buttons[0].rect.centerx = WIDTH // 2
        self.buttons[0].rect.y = 50

        # Rear button to bottom center
        self.buttons[2].rect.centerx = WIDTH // 2
        self.buttons[2].rect.y = HEIGHT - 110

    def draw_laser_beam(self, angle):
        """Visualizes the incoming laser threat."""
        cx, cy = self.tank.x, self.tank.y
        rad = math.radians(angle - 90)

        # Start far away
        start_x = cx + math.cos(rad) * 600
        start_y = cy + math.sin(rad) * 600

        # End at tank
        end_x = cx
        end_y = cy

        # Draw pulsing beam
        width = random.randint(2, 5)
        pygame.draw.line(self.screen, COLOR_LASER, (start_x, start_y), (end_x, end_y), width)

        # Flash effect at impact
        pygame.draw.circle(self.screen, (255, 255, 255), (int(cx), int(cy)), 30)

    def draw_ui(self):
        # Dashboard Panel
        pygame.draw.rect(self.screen, COLOR_UI_BG, (0, 0, 250, 150))
        pygame.draw.rect(self.screen, (100, 100, 100), (0, 0, 250, 150), 2)

        # Status Text
        title = self.font_ui.render("COMMANDER'S DISPLAY", True, (200, 200, 200))
        self.screen.blit(title, (10, 10))

        turret_status = f"TURRET AZ: {int(self.tank.turret_angle)}°"
        t_col = (255, 255, 0) if abs(self.tank.turret_angle - self.tank.target_angle) > 1 else (0, 255, 0)
        ts_surf = self.font_ui.render(turret_status, True, t_col)
        self.screen.blit(ts_surf, (10, 40))

        ammo_status = f"SMOKE CANISTERS: {self.tank.smoke_canisters}"
        as_surf = self.font_ui.render(ammo_status, True, (255, 255, 255))
        self.screen.blit(as_surf, (10, 65))

        # Buttons
        for btn in self.buttons:
            btn.draw(self.screen)

        # Alert Overlay
        if self.tank.lws_active:
            # Flashing red border
            if pygame.time.get_ticks() % 500 < 250:
                pygame.draw.rect(self.screen, (255, 0, 0), (0, 0, WIDTH, HEIGHT), 20)

            alert_text = f"WARNING: LASER DETECTED ({self.tank.threat_sector})"
            txt_surf = self.font_alert.render(alert_text, True, COLOR_TEXT_WARN)
            rect = txt_surf.get_rect(center=(WIDTH // 2, HEIGHT - 50))

            # Background for text
            bg_rect = rect.inflate(20, 10)
            pygame.draw.rect(self.screen, (0, 0, 0), bg_rect)
            pygame.draw.rect(self.screen, (255, 0, 0), bg_rect, 2)
            self.screen.blit(txt_surf, rect)

            # Draw Audio Cue Visual
            freq_text = "AUDIO: HIGH PITCH" if self.tank.threat_sector == "FRONT" else "AUDIO: LOW PITCH"
            aud_surf = self.font_ui.render(freq_text, True, (0, 255, 255))
            self.screen.blit(aud_surf, (10, 120))

    def run(self):
        running = True
        while running:
            mx, my = pygame.mouse.get_pos()

            # --- Events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        for btn in self.buttons:
                            if btn.rect.collidepoint(mx, my):
                                self.tank.trigger_lws(btn.angle, btn.label.split()[0])

                elif event.type == pygame.KEYDOWN:
                    # Keyboard shortcuts
                    if event.key == pygame.K_UP: self.tank.trigger_lws(0, "FRONT")
                    if event.key == pygame.K_RIGHT: self.tank.trigger_lws(90, "RIGHT")
                    if event.key == pygame.K_DOWN: self.tank.trigger_lws(180, "REAR")
                    if event.key == pygame.K_LEFT: self.tank.trigger_lws(270, "LEFT")

            # Update Button Hover
            for btn in self.buttons:
                btn.hover = btn.rect.collidepoint(mx, my)

            # --- Logic ---
            self.tank.update()

            # --- Draw ---
            self.screen.fill(COLOR_BG)

            # Draw Grid
            for x in range(0, WIDTH, 50):
                pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, HEIGHT))
            for y in range(0, HEIGHT, 50):
                pygame.draw.line(self.screen, COLOR_GRID, (0, y), (WIDTH, y))

            # Draw Laser if active
            if self.tank.lws_active:
                self.draw_laser_beam(self.tank.target_angle)

            self.tank.draw_hull(self.screen)
            self.tank.draw_turret(self.screen)
            self.tank.draw_smoke(self.screen)

            self.draw_ui()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    app = LWSApp()
    app.run()