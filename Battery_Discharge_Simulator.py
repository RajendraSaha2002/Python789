import pygame
import random
import math
from collections import deque

# --- Constants & Configuration ---
WIDTH, HEIGHT = 1000, 700
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
GREY = (100, 100, 100)
RED = (200, 50, 50)
GREEN = (50, 200, 50)  # Li+ Ions
YELLOW = (255, 255, 0)  # Electrons
BLUE = (50, 50, 200)  # Cathode
DARK_GREY = (50, 50, 50)  # Anode
ORANGE = (255, 165, 0)  # Degradation (SEI)
CYAN = (0, 255, 255)  # Electrolyte

# Physics Constants
MAX_VOLTAGE = 4.2
MIN_VOLTAGE = 3.0
BATTERY_CAPACITY = 100.0  # Arbitrary units (Coulombs equivalent)


# --- Classes ---

class Battery:
    def __init__(self):
        self.charge = BATTERY_CAPACITY
        self.max_capacity = BATTERY_CAPACITY
        self.voltage = MAX_VOLTAGE
        self.resistance = 5.0  # Ohms (Load)
        self.current = 0.0
        self.degradation_mode = False
        self.dead_ions = 0  # Capacity loss

    def update(self, dt):
        # Calculate Voltage based on Charge % (Empirical Li-Ion Curve approximation)
        # Nernst-like behavior: Steep drop at start, plateau, steep drop at end
        soc = self.charge / BATTERY_CAPACITY  # State of Charge (0.0 to 1.0)

        if soc <= 0:
            self.voltage = 0
            self.current = 0
            return

        # Simplified Discharge Curve Formula
        # V ~ E0 - R*I - K/SOC ... simplified to a polynomial for visual smoothness
        self.voltage = 3.0 + (1.0 * soc) - (0.2 * (1 - soc) ** 2) + (0.1 * math.pow(soc, 0.1))

        # Calculate Current: I = V / R
        self.current = self.voltage / self.resistance

        # Drain Battery
        drain_rate = self.current * dt * 0.5  # Scale factor for simulation time
        self.charge -= drain_rate

        # Degradation Logic (SEI Formation)
        if self.degradation_mode and random.random() < 0.01 * self.current:
            self.dead_ions += 1
            self.max_capacity -= 0.1
            if self.charge > self.max_capacity:
                self.charge = self.max_capacity


class Particle:
    def __init__(self, x, y, p_type, destination_x):
        self.x = x
        self.y = y
        self.type = p_type  # 'ion' or 'electron'
        self.dest_x = destination_x
        self.speed = 0
        self.active = True
        self.stuck = False  # For degradation

    def move(self, current_magnitude):
        if self.stuck: return

        # Speed is proportional to current
        self.speed = current_magnitude * 2.0

        dx = self.dest_x - self.x
        dist = abs(dx)

        if dist < 5:
            self.active = False  # Reached destination
        else:
            # Move towards destination
            direction = 1 if dx > 0 else -1

            # Add some "diffusion" jitter (Brownian motion)
            jitter_y = random.uniform(-1, 1)

            self.x += self.speed * direction
            self.y += jitter_y


class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, initial_val, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial_val
        self.label = label
        self.handle_rect = pygame.Rect(x, y - 5, 20, h + 10)
        self.dragging = False
        self.update_handle()

    def update_handle(self):
        ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        self.handle_rect.centerx = self.rect.x + (self.rect.width * ratio)

    def draw(self, screen, font):
        # Draw Label
        text = font.render(f"{self.label}: {self.val:.1f} Ohms", True, WHITE)
        screen.blit(text, (self.rect.x, self.rect.y - 25))

        # Draw Line
        pygame.draw.rect(screen, GREY, self.rect)
        # Draw Handle
        pygame.draw.rect(screen, RED, self.handle_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_rect.collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                new_x = max(self.rect.x, min(event.pos[0], self.rect.right))
                ratio = (new_x - self.rect.x) / self.rect.width
                self.val = self.min_val + (ratio * (self.max_val - self.min_val))
                self.update_handle()


# --- Main Simulation ---

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Li-Ion Battery Discharge Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 16)
    title_font = pygame.font.SysFont("Arial", 24, bold=True)

    # Setup Battery
    battery = Battery()

    # UI Elements
    resistance_slider = Slider(50, 600, 300, 10, 1.0, 20.0, 5.0, "Load Resistance")

    # Toggle Button for Degradation
    deg_btn_rect = pygame.Rect(400, 580, 200, 40)

    # Particle Systems
    ions = []
    electrons = []

    # Graph Data
    graph_data = deque(maxlen=300)  # Store (time, voltage)
    time_counter = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta time in seconds

        # --- Input Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if deg_btn_rect.collidepoint(event.pos):
                    battery.degradation_mode = not battery.degradation_mode

            resistance_slider.handle_event(event)

        # Update Battery Physics
        battery.resistance = resistance_slider.val
        battery.update(dt)

        # --- Particle Spawning & Logic ---
        # Spawn rate depends on current
        spawn_chance = battery.current * 0.2

        # 1. Li+ Ions (Internal: Anode -> Cathode)
        # Anode area: x=100-300, y=200-400
        # Cathode area: x=700-900, y=200-400
        if battery.charge > 0:
            if random.random() < spawn_chance:
                # Spawn Ion in Anode
                start_y = random.randint(220, 380)
                ions.append(Particle(random.randint(150, 250), start_y, 'ion', 750))

            if random.random() < spawn_chance:
                # Spawn Electron in Wire (Top)
                # Wire path: 200 -> 800 (Left to right)
                electrons.append(Particle(200, 100, 'electron', 800))

        # Move Particles
        for p in ions:
            if not p.stuck:
                # If degradation is on, small chance to get stuck in Electrolyte (SEI)
                if battery.degradation_mode and 400 < p.x < 600:
                    if random.random() < 0.02:
                        p.stuck = True

            p.move(battery.current)

        for p in electrons:
            p.move(battery.current)

        # Cleanup inactive particles
        ions = [p for p in ions if p.active or p.stuck]
        electrons = [p for p in electrons if p.active]

        # --- Graphing Logic ---
        time_counter += 1
        if time_counter % 5 == 0:
            graph_data.append(battery.voltage)

        # --- Drawing ---
        screen.fill(BLACK)

        # 1. Draw Structure
        # Wire
        pygame.draw.line(screen, GREY, (200, 200), (200, 100), 4)  # Anode Up
        pygame.draw.line(screen, GREY, (200, 100), (800, 100), 4)  # Top Wire
        pygame.draw.line(screen, GREY, (800, 100), (800, 200), 4)  # Cathode Down

        # Load (Resistor symbol approximation)
        pygame.draw.circle(screen, WHITE, (500, 100), 20)
        # Glow based on current
        glow_radius = int(battery.current * 10)
        if glow_radius > 0:
            surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 200, 100), (glow_radius, glow_radius), glow_radius)
            screen.blit(surf, (500 - glow_radius, 100 - glow_radius))

        # Battery Container
        pygame.draw.rect(screen, GREY, (80, 180, 840, 240), 2)

        # Anode (Graphite - Left)
        anode_rect = pygame.Rect(100, 200, 200, 200)
        pygame.draw.rect(screen, DARK_GREY, anode_rect)
        anode_label = font.render("Anode (Graphite) (-)", True, WHITE)
        screen.blit(anode_label, (120, 410))

        # Cathode (LCO - Right)
        cathode_rect = pygame.Rect(700, 200, 200, 200)
        pygame.draw.rect(screen, BLUE, cathode_rect)
        cathode_label = font.render("Cathode (LiCoO2) (+)", True, WHITE)
        screen.blit(cathode_label, (720, 410))

        # Electrolyte (Middle)
        elec_rect = pygame.Rect(300, 200, 400, 200)
        s = pygame.Surface((400, 200))
        s.set_alpha(50)
        s.fill(CYAN)
        screen.blit(s, (300, 200))
        elec_label = font.render("Electrolyte / Separator", True, CYAN)
        screen.blit(elec_label, (420, 185))

        # 2. Draw Particles
        for p in ions:
            color = GREEN if not p.stuck else ORANGE
            pygame.draw.circle(screen, color, (int(p.x), int(p.y)), 4)

        for p in electrons:
            pygame.draw.circle(screen, YELLOW, (int(p.x), int(p.y)), 3)

        # 3. Draw UI & Stats
        title = title_font.render("Li-Ion Discharge Simulation", True, WHITE)
        screen.blit(title, (50, 20))

        stats = [
            f"Voltage: {battery.voltage:.2f} V",
            f"Current: {battery.current:.2f} A",
            f"SoC: {(battery.charge / BATTERY_CAPACITY) * 100:.1f} %"
        ]

        for i, line in enumerate(stats):
            t = font.render(line, True, WHITE)
            screen.blit(t, (50, 60 + i * 25))

        resistance_slider.draw(screen, font)

        # Degradation Button
        btn_color = RED if battery.degradation_mode else GREY
        pygame.draw.rect(screen, btn_color, deg_btn_rect)
        btn_text = font.render(f"Aging Mode: {'ON' if battery.degradation_mode else 'OFF'}", True, WHITE)
        screen.blit(btn_text, (deg_btn_rect.x + 20, deg_btn_rect.y + 10))
        if battery.degradation_mode:
            dead_text = font.render(f"Dead Ions (SEI): {battery.dead_ions}", True, ORANGE)
            screen.blit(dead_text, (deg_btn_rect.x, deg_btn_rect.y + 45))

        # 4. Draw Graph (Bottom Right)
        graph_rect = pygame.Rect(650, 500, 300, 150)
        pygame.draw.rect(screen, (30, 30, 30), graph_rect)
        pygame.draw.rect(screen, WHITE, graph_rect, 1)

        if len(graph_data) > 1:
            points = []
            for i, val in enumerate(graph_data):
                # Scale x to width
                x = graph_rect.x + (i * (graph_rect.width / len(graph_data)))
                # Scale y to voltage (0 to 4.5V)
                y = graph_rect.bottom - ((val / 4.5) * graph_rect.height)
                points.append((x, y))
            pygame.draw.lines(screen, RED, False, points, 2)

        # Graph Labels
        screen.blit(font.render("4.2V", True, GREY), (graph_rect.right + 5, graph_rect.top))
        screen.blit(font.render("3.0V", True, GREY), (graph_rect.right + 5, graph_rect.bottom - 40))
        screen.blit(font.render("0.0V", True, GREY), (graph_rect.right + 5, graph_rect.bottom))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()