import pygame
import random
import math

# --- Configuration ---
WIDTH, HEIGHT = 1000, 700
FPS = 60

# Colors
BLACK = (10, 10, 20)
WHITE = (255, 255, 255)
RED = (255, 50, 50)  # Threat
GREEN = (50, 255, 50)  # Ready Launcher / Active Intercept
YELLOW = (255, 200, 50)  # Reloading / Low Ammo
GREY = (80, 80, 80)  # Empty / Offline
BLUE = (50, 150, 255)  # Interceptor Trail

# Constants
RELOAD_TIME = 180  # Frames (3 seconds)
AMMO_CAPACITY = 8


class Launcher:
    def __init__(self, id, x, y, ammo=AMMO_CAPACITY):
        self.id = id
        self.pos = (x, y)
        self.ammo = ammo
        self.max_ammo = AMMO_CAPACITY
        self.status = "READY"  # READY, RELOADING, EMPTY
        self.reload_timer = 0

        # Visuals
        self.color = GREEN
        self.rect = pygame.Rect(x - 20, y - 40, 40, 40)

    def fire(self):
        if self.status != "READY": return False

        self.ammo -= 1

        if self.ammo <= 0:
            self.status = "EMPTY"
            self.color = GREY
        elif self.ammo <= 2:
            self.color = YELLOW  # Low ammo warning

        return True

    def start_reload(self):
        if self.status == "RELOADING": return
        self.status = "RELOADING"
        self.reload_timer = RELOAD_TIME
        self.color = YELLOW

    def update(self):
        if self.status == "RELOADING":
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.status = "READY"
                self.ammo = self.max_ammo
                self.color = GREEN

    def draw(self, screen, font):
        # Draw Truck Body
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, WHITE, self.rect, 2)  # Outline

        # Draw Launcher Tubes
        # Visual representation of ammo count
        for i in range(self.max_ammo):
            bx = self.rect.x + (i % 4) * 10
            by = self.rect.y - 10 - (i // 4) * 10
            col = GREEN if i < self.ammo else GREY
            pygame.draw.rect(screen, col, (bx + 2, by + 2, 6, 8))

        # Status Text
        label = f"ID: {self.id}"
        stat = f"{self.status}"
        if self.status == "RELOADING":
            stat += f" ({self.reload_timer // 60}s)"

        t1 = font.render(label, True, WHITE)
        t2 = font.render(stat, True, self.color)

        screen.blit(t1, (self.rect.x, self.rect.bottom + 5))
        screen.blit(t2, (self.rect.x - 10, self.rect.bottom + 20))


class Threat:
    def __init__(self):
        self.pos = [random.randint(50, WIDTH - 50), -20]
        self.target = [random.randint(50, WIDTH - 50), HEIGHT]

        # Calculate velocity vector
        dx = self.target[0] - self.pos[0]
        dy = self.target[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        speed = random.uniform(1.5, 3.0)

        self.vel = [dx / dist * speed, dy / dist * speed]
        self.assigned_launcher = None  # Which truck is killing this?
        self.active = True
        self.intercept_progress = 0.0  # 0.0 to 1.0

    def update(self):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]

        # If engaged, animate the interceptor flying towards it
        if self.assigned_launcher:
            self.intercept_progress += 0.02
            if self.intercept_progress >= 1.0:
                self.active = False  # Boom
                return "DESTROYED"

        if self.pos[1] > HEIGHT - 50:
            self.active = False
            return "IMPACT"

        return "FLYING"

    def draw(self, screen):
        # Draw Threat
        if self.active:
            pygame.draw.circle(screen, RED, (int(self.pos[0]), int(self.pos[1])), 5)

            # Draw Interceptor Line if engaged
            if self.assigned_launcher:
                start = self.assigned_launcher.pos
                end = self.pos

                # Lerp for missile head
                t = self.intercept_progress
                mx = start[0] + (end[0] - start[0]) * t
                my = start[1] + (end[1] - start[1]) * t

                pygame.draw.line(screen, BLUE, start, (mx, my), 2)
                pygame.draw.circle(screen, WHITE, (int(mx), int(my)), 3)


class AllocationSystem:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Interceptor Resource Allocation Logic")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)

        # Deploy Launchers
        self.launchers = [
            Launcher("A", 200, HEIGHT - 100),
            Launcher("B", 500, HEIGHT - 100, ammo=4),  # Start with less ammo to force logic
            Launcher("C", 800, HEIGHT - 100)
        ]

        self.threats = []
        self.intercepts = 0
        self.leaks = 0

    def assign_launcher(self, threat):
        """
        THE CORE ALGORITHM (Greedy Strategy)
        1. Find all launchers that are READY and have AMMO.
        2. Calculate distance to threat for each.
        3. Assign to the CLOSEST one.
        """
        candidates = []

        for launcher in self.launchers:
            if launcher.status == "READY" and launcher.ammo > 0:
                # Calculate Distance Squared (faster than sqrt)
                dist_sq = (launcher.pos[0] - threat.pos[0]) ** 2 + (launcher.pos[1] - threat.pos[1]) ** 2
                candidates.append((dist_sq, launcher))

        if not candidates:
            return None  # No solution found (Critical Failure)

        # Sort by distance (lowest first)
        candidates.sort(key=lambda x: x[0])

        # Pick the best
        best_launcher = candidates[0][1]
        return best_launcher

    def run(self):
        running = True
        spawn_timer = 0

        while running:
            # --- Events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    # Manual Reload Controls
                    if event.key == pygame.K_1: self.launchers[0].start_reload()
                    if event.key == pygame.K_2: self.launchers[1].start_reload()
                    if event.key == pygame.K_3: self.launchers[2].start_reload()

            # --- Spawning ---
            spawn_timer += 1
            if spawn_timer > 60:  # Every 1 second roughly
                t = Threat()
                self.threats.append(t)

                # Immediate Assignment Logic
                chosen = self.assign_launcher(t)
                if chosen:
                    chosen.fire()
                    t.assigned_launcher = chosen
                else:
                    print("WARNING: THREAT LEAKED - NO ASSETS AVAILABLE")

                spawn_timer = 0

            # --- Update ---
            for l in self.launchers:
                l.update()

            for t in self.threats:
                res = t.update()
                if res == "DESTROYED":
                    self.intercepts += 1
                elif res == "IMPACT":
                    self.leaks += 1

            # Cleanup
            self.threats = [t for t in self.threats if t.active]

            # --- Draw ---
            self.screen.fill(BLACK)

            # Ground
            pygame.draw.rect(self.screen, (30, 30, 30), (0, HEIGHT - 100, WIDTH, 100))

            for l in self.launchers:
                l.draw(self.screen, self.font)

            for t in self.threats:
                t.draw(self.screen)

            # UI Overlay
            ui_text = [
                f"INTERCEPTS: {self.intercepts}",
                f"LEAKS: {self.leaks}",
                "",
                "CONTROLS:",
                "[1] Reload Truck A",
                "[2] Reload Truck B",
                "[3] Reload Truck C"
            ]

            for i, line in enumerate(ui_text):
                c = RED if "LEAKS" in line and self.leaks > 0 else WHITE
                s = self.font.render(line, True, c)
                self.screen.blit(s, (10, 10 + i * 20))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    sim = AllocationSystem()
    sim.run()