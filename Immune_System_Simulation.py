import pygame
import numpy as np
import random
from collections import deque

# --- Configuration ---
WIDTH, HEIGHT = 1200, 800
PANEL_WIDTH = 300  # Right side panel for controls/graph
GAME_WIDTH = WIDTH - PANEL_WIDTH
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
RED = (200, 50, 50)  # Bacteria
GREEN = (50, 200, 50)  # Neutrophils (WBC)
GREY = (50, 50, 50)
LIGHT_GREY = (150, 150, 150)
CYAN = (0, 255, 255)
UI_BG = (30, 30, 30)

# Physics
BACTERIA_SIZE = 4
NEUTROPHIL_SIZE = 8
CHEMOTAXIS_RADIUS = 200  # How far WBCs can "smell" bacteria


class Agent:
    def __init__(self, x, y, speed, color, size):
        self.pos = np.array([float(x), float(y)])
        self.vel = np.array([random.uniform(-1, 1), random.uniform(-1, 1)])
        # Normalize velocity
        norm = np.linalg.norm(self.vel)
        if norm > 0:
            self.vel = (self.vel / norm) * speed

        self.speed = speed
        self.color = color
        self.size = size
        self.active = True

    def move(self):
        self.pos += self.vel

        # Bounce off walls
        if self.pos[0] < 0 or self.pos[0] > GAME_WIDTH:
            self.vel[0] *= -1
            self.pos[0] = np.clip(self.pos[0], 0, GAME_WIDTH)
        if self.pos[1] < 0 or self.pos[1] > HEIGHT:
            self.vel[1] *= -1
            self.pos[1] = np.clip(self.pos[1], 0, HEIGHT)

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, self.pos.astype(int), self.size)


class Bacteria(Agent):
    def __init__(self, x, y):
        super().__init__(x, y, speed=1.5, color=RED, size=BACTERIA_SIZE)

    def update(self):
        # Brownian Motion (Jitter)
        jitter = np.array([random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)])
        self.vel += jitter

        # Re-normalize speed
        norm = np.linalg.norm(self.vel)
        if norm > 0:
            self.vel = (self.vel / norm) * self.speed

        self.move()


class Neutrophil(Agent):
    def __init__(self, x, y, speed_mult=1.0):
        super().__init__(x, y, speed=2.0 * speed_mult, color=GREEN, size=NEUTROPHIL_SIZE)
        self.base_speed = 2.0
        self.speed_mult = speed_mult

    def update(self, bacteria_list):
        self.speed = self.base_speed * self.speed_mult

        # Chemotaxis Logic: Find "scent" vector
        # Instead of a heavy grid, we calculate the vector sum to nearby bacteria
        # This mimics moving up a concentration gradient.

        steering = np.array([0.0, 0.0])
        count = 0

        # Simple optimization: Only check a random subset if too many bacteria
        # (keeps FPS high)
        targets = bacteria_list
        if len(targets) > 100:
            targets = random.sample(targets, 50)

        for b in targets:
            dist_vec = b.pos - self.pos
            dist = np.linalg.norm(dist_vec)

            if dist < CHEMOTAXIS_RADIUS and dist > 0:
                # Weight by inverse distance (stronger smell closer to source)
                weight = 1.0 / (dist * dist)
                steering += (dist_vec / dist) * weight
                count += 1

        if count > 0:
            # Steer towards the "scent"
            # Normalize steering vector
            norm = np.linalg.norm(steering)
            if norm > 0:
                steering = (steering / norm) * 0.2  # 0.2 is the turning force (agility)

            self.vel += steering
        else:
            # Wander aimlessly if no scent
            self.vel += np.array([random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)])

        # Cap velocity at max speed
        norm = np.linalg.norm(self.vel)
        if norm > 0:
            self.vel = (self.vel / norm) * self.speed

        self.move()


class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, initial, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.val = initial
        self.label = label
        self.handle_rect = pygame.Rect(x, y - 5, 10, h + 10)
        self.dragging = False
        self.update_handle()

    def update_handle(self):
        ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        self.handle_rect.centerx = self.rect.x + (self.rect.width * ratio)

    def draw(self, screen, font):
        label_surf = font.render(f"{self.label}: {self.val:.2f}", True, WHITE)
        screen.blit(label_surf, (self.rect.x, self.rect.y - 25))
        pygame.draw.rect(screen, GREY, self.rect)
        pygame.draw.rect(screen, CYAN, self.handle_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_rect.inflate(20, 20).collidepoint(event.pos):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                new_x = max(self.rect.x, min(event.pos[0], self.rect.right))
                ratio = (new_x - self.rect.x) / self.rect.width
                self.val = self.min_val + (ratio * (self.max_val - self.min_val))
                self.update_handle()


class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("The Micro-Battlefield: Immune Response ABM")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16)

        self.bacteria = []
        self.neutrophils = []

        # Initial Population
        for _ in range(50):
            self.spawn_bacteria()
        for _ in range(5):
            self.spawn_neutrophil()

        # UI
        self.infection_rate_slider = Slider(GAME_WIDTH + 20, 50, 200, 10, 0.0, 0.2, 0.05, "Infection Rate")
        self.immune_speed_slider = Slider(GAME_WIDTH + 20, 120, 200, 10, 0.5, 3.0, 1.0, "Immune Speed")

        # Graph Data
        self.history_bac = deque(maxlen=200)
        self.history_neu = deque(maxlen=200)
        self.frame_count = 0

    def spawn_bacteria(self):
        # Spawn at random edges or random spots
        x = random.randint(10, GAME_WIDTH - 10)
        y = random.randint(10, HEIGHT - 10)
        self.bacteria.append(Bacteria(x, y))

    def spawn_neutrophil(self):
        x = random.randint(10, GAME_WIDTH - 10)
        y = random.randint(10, HEIGHT - 10)
        self.neutrophils.append(Neutrophil(x, y))

    def check_collisions(self):
        # Grid-based collision or simple distance check
        # For simplicity and N < 1000, simple distance check is okay-ish,
        # but let's optimize slightly by checking only close ones.
        # Actually, standard N^2 check is too slow for Python.
        # We will iterate backwards to allow deletion.

        # Optimization: Neutrophils consume.
        # Check every neutrophil against every bacteria is expensive.
        # Let's just check bacteria against neutrophils.

        dead_bacteria = []

        for b in self.bacteria:
            for n in self.neutrophils:
                # Squared Euclidean distance check (faster than sqrt)
                dist_sq = (b.pos[0] - n.pos[0]) ** 2 + (b.pos[1] - n.pos[1]) ** 2
                # Collision radius = sum of radii
                col_dist = (b.size + n.size) ** 2

                if dist_sq < col_dist:
                    b.active = False
                    break  # Eaten by one, don't check others

        # Remove eaten bacteria
        self.bacteria = [b for b in self.bacteria if b.active]

    def draw_graph(self):
        graph_rect = pygame.Rect(GAME_WIDTH + 20, 400, 260, 150)
        pygame.draw.rect(self.screen, BLACK, graph_rect)
        pygame.draw.rect(self.screen, GREY, graph_rect, 1)

        if len(self.history_bac) < 2:
            return

        # Normalize data to fit box
        max_pop = max(100, max(self.history_bac), max(self.history_neu))

        def get_points(history):
            points = []
            for i, val in enumerate(history):
                x = graph_rect.x + (i / len(history)) * graph_rect.width
                y = graph_rect.bottom - (val / max_pop) * graph_rect.height
                points.append((x, y))
            return points

        if len(self.history_bac) > 1:
            pygame.draw.lines(self.screen, RED, False, get_points(self.history_bac), 2)
        if len(self.history_neu) > 1:
            pygame.draw.lines(self.screen, GREEN, False, get_points(self.history_neu), 2)

        # Legend
        self.screen.blit(self.font.render("Bacteria", True, RED), (graph_rect.x, graph_rect.y - 20))
        self.screen.blit(self.font.render("Neutrophils", True, GREEN), (graph_rect.x + 100, graph_rect.y - 20))
        self.screen.blit(self.font.render(f"Max Pop: {max_pop}", True, WHITE), (graph_rect.x, graph_rect.bottom + 5))

    def run(self):
        running = True
        while running:
            # 1. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Click on game area to spawn WBC manually
                    if event.pos[0] < GAME_WIDTH:
                        self.neutrophils.append(Neutrophil(event.pos[0], event.pos[1]))

                self.infection_rate_slider.handle_event(event)
                self.immune_speed_slider.handle_event(event)

            # 2. Logic Update
            # Spawning Bacteria
            infection_chance = self.infection_rate_slider.val
            if random.random() < infection_chance:
                self.spawn_bacteria()

            # Spawning Immune Response (Triggered by bacteria count)
            # If bacteria count is high, body recruits more neutrophils
            recruitment_chance = len(self.bacteria) * 0.0005
            if random.random() < recruitment_chance:
                self.spawn_neutrophil()

            # Move Bacteria
            for b in self.bacteria:
                b.update()

            # Move Neutrophils
            speed_val = self.immune_speed_slider.val
            for n in self.neutrophils:
                n.speed_mult = speed_val
                n.update(self.bacteria)

            self.check_collisions()

            # Update Graph Data
            self.frame_count += 1
            if self.frame_count % 10 == 0:
                self.history_bac.append(len(self.bacteria))
                self.history_neu.append(len(self.neutrophils))

            # 3. Drawing
            self.screen.fill(BLACK)

            # Draw UI Panel
            pygame.draw.rect(self.screen, UI_BG, (GAME_WIDTH, 0, PANEL_WIDTH, HEIGHT))
            pygame.draw.line(self.screen, GREY, (GAME_WIDTH, 0), (GAME_WIDTH, HEIGHT), 2)

            # Draw Agents
            for b in self.bacteria:
                b.draw(self.screen)
            for n in self.neutrophils:
                n.draw(self.screen)

            # Draw UI Elements
            self.infection_rate_slider.draw(self.screen, self.font)
            self.immune_speed_slider.draw(self.screen, self.font)
            self.draw_graph()

            # Stats
            stats = [
                f"Bacteria: {len(self.bacteria)}",
                f"Neutrophils: {len(self.neutrophils)}",
                "Left Click: Spawn Neutrophil"
            ]
            for i, line in enumerate(stats):
                s = self.font.render(line, True, WHITE)
                self.screen.blit(s, (GAME_WIDTH + 20, 250 + i * 25))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    sim = Simulation()
    sim.run()