import pygame
import numpy as np
import random
import math

# --- Configuration ---
WIDTH, HEIGHT = 1200, 800
FPS = 60

# Colors
BLACK = (10, 10, 20)
WHITE = (255, 255, 255)
RED = (255, 50, 50)  # Threat
YELLOW = (255, 200, 50)  # Non-Threat (or Explosion)
GREEN = (50, 255, 50)  # City / Interceptor
CYAN = (0, 255, 255)  # Prediction Line
GREY = (50, 50, 60)

# Physics
GRAVITY = 9.81 * 0.5  # Scaled for screen
DRAG_COEFF = 0.002  # Air resistance
INTERCEPTOR_SPEED = 15.0
ENEMY_SPEED_MIN = 12.0
ENEMY_SPEED_MAX = 18.0

# Game Entities
BATTERY_POS = (WIDTH // 2, HEIGHT - 50)


class City:
    def __init__(self, x, width, name):
        self.rect = pygame.Rect(x, HEIGHT - 40, width, 30)
        self.name = name
        self.active = True

    def draw(self, screen):
        color = GREEN if self.active else GREY
        pygame.draw.rect(screen, color, self.rect)

        # Draw label
        font = pygame.font.SysFont("Arial", 12)
        text = font.render(self.name, True, WHITE)
        screen.blit(text, (self.rect.centerx - text.get_width() // 2, self.rect.y + 5))


class Explosion:
    def __init__(self, x, y):
        self.pos = [x, y]
        self.radius = 5
        self.max_radius = 40
        self.life = 30  # Frames
        self.active = True

    def update(self):
        self.radius += 2
        self.life -= 1
        if self.life <= 0:
            self.active = False

    def draw(self, screen):
        if self.active:
            alpha = int((self.life / 30) * 255)
            s = pygame.Surface((self.max_radius * 2, self.max_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*YELLOW, alpha), (self.max_radius, self.max_radius), self.radius)
            screen.blit(s, (self.pos[0] - self.max_radius, self.pos[1] - self.max_radius))


class Rocket:
    def __init__(self, is_enemy=True, start_pos=(0, 0), target_pos=None):
        self.pos = np.array(start_pos, dtype=float)
        self.is_enemy = is_enemy
        self.active = True
        self.history = []

        if is_enemy:
            # Random Launch Params
            # Launch from sides
            if random.choice([True, False]):
                self.pos = np.array([random.randint(0, 200), HEIGHT - 50], dtype=float)
                target_x = random.randint(WIDTH // 2, WIDTH)
            else:
                self.pos = np.array([random.randint(WIDTH - 200, WIDTH), HEIGHT - 50], dtype=float)
                target_x = random.randint(0, WIDTH // 2)

            # Calculate velocity for a high arc
            dx = target_x - self.pos[0]
            dy = -random.randint(400, 600)  # Peak height proxy
            speed = random.uniform(ENEMY_SPEED_MIN, ENEMY_SPEED_MAX)
            angle = math.atan2(dy, dx) + math.radians(random.uniform(-10, 10))  # Add noise

            # Simple ballistic velocity init
            # Actually, let's just shoot somewhat towards the center with random power
            shoot_angle = math.radians(random.uniform(-70, -30)) if dx > 0 else math.radians(random.uniform(-150, -110))
            self.vel = np.array([math.cos(shoot_angle), math.sin(shoot_angle)]) * speed

            self.is_threat = False
            self.predicted_impact_x = None
            self.intercepted_by = None  # Track if an interceptor is already assigned

        else:
            # Interceptor Logic
            # Aim at the predicted impact point (PIP) initially
            dx = target_pos[0] - self.pos[0]
            dy = target_pos[1] - self.pos[1]
            angle = math.atan2(dy, dx)
            self.vel = np.array([math.cos(angle), math.sin(angle)]) * INTERCEPTOR_SPEED
            self.target_rocket = None  # Will be assigned by radar

    def predict_impact(self):
        """
        Simulate physics forward to find where this rocket lands.
        Returns: x_coordinate of impact.
        """
        sim_pos = self.pos.copy()
        sim_vel = self.vel.copy()

        # Fast forward simulation
        # Limit steps to prevent infinite loops
        for _ in range(500):
            sim_pos += sim_vel
            sim_vel[1] += GRAVITY * 0.1  # Sim gravity
            sim_vel *= (1.0 - DRAG_COEFF)  # Sim drag

            if sim_pos[1] >= HEIGHT - 50:
                return sim_pos[0]
        return sim_pos[0]

    def update(self):
        self.history.append(tuple(self.pos.astype(int)))
        if len(self.history) > 20: self.history.pop(0)

        # Physics
        self.pos += self.vel
        self.vel[1] += GRAVITY * 0.1  # scaled gravity

        # Air Drag
        self.vel *= (1.0 - DRAG_COEFF)

        # Guidance (Interceptors only)
        if not self.is_enemy and self.target_rocket:
            if self.target_rocket.active:
                # Proportional Navigation (simplified)
                # Steer towards target
                target_future_pos = self.target_rocket.pos + self.target_rocket.vel * 5  # Lead the target
                desired_vec = target_future_pos - self.pos
                desired_vec /= np.linalg.norm(desired_vec)

                # Turn speed limit
                current_vec = self.vel / np.linalg.norm(self.vel)
                new_vec = current_vec + (desired_vec - current_vec) * 0.2
                new_vec /= np.linalg.norm(new_vec)

                self.vel = new_vec * INTERCEPTOR_SPEED
            else:
                self.active = False  # Self destruct if target gone

        # Floor Collision
        if self.pos[1] > HEIGHT - 30:
            self.active = False
            return "ground_hit"

        return "flying"

    def draw(self, screen):
        color = RED if self.is_enemy and self.is_threat else (YELLOW if self.is_enemy else GREEN)

        # Draw Trail
        if len(self.history) > 1:
            pygame.draw.lines(screen, color, False, self.history, 1)

        # Draw Head
        pygame.draw.circle(screen, color, self.pos.astype(int), 3)

        # Draw Prediction (Debug view for threats)
        if self.is_enemy and self.is_threat and self.predicted_impact_x is not None:
            pygame.draw.line(screen, GREY, self.pos.astype(int), (int(self.predicted_impact_x), HEIGHT - 40), 1)


class IronDomeSim:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Iron Dome Interception Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)

        # Defended Zones
        self.cities = [
            City(200, 150, "Ashkelon"),
            City(500, 200, "Tel Aviv"),
            City(900, 150, "Haifa")
        ]

        self.rockets = []
        self.interceptors = []
        self.explosions = []

        self.ammo = 20
        self.score_saved = 0
        self.score_failed = 0

    def calculate_intercept_point(self, rocket):
        """
        Solves for the optimal interception point.
        Finds the point on the rocket's predicted path closest to the battery
        that can be reached in time.
        """
        sim_pos = rocket.pos.copy()
        sim_vel = rocket.vel.copy()

        best_time = 0

        # Simulate rocket trajectory forward step by step
        for t in range(1, 300):  # Look 300 frames ahead
            sim_pos += sim_vel
            sim_vel[1] += GRAVITY * 0.1
            sim_vel *= (1.0 - DRAG_COEFF)

            # Distance from battery to this future point
            dist = np.linalg.norm(sim_pos - np.array(BATTERY_POS))

            # Time for interceptor to travel this distance
            t_int = dist / INTERCEPTOR_SPEED

            # If interceptor can get there before the rocket (t_int <= t)
            if t_int <= t:
                return sim_pos

        return rocket.pos  # Fallback (shouldn't happen often)

    def radar_system(self):
        """
        The Brain: Tracks rockets, predicts impact, assesses threat, launches interceptors.
        """
        threats = []

        for r in self.rockets:
            if not r.active: continue

            # 1. Prediction: Where will it land?
            if r.predicted_impact_x is None:
                r.predicted_impact_x = r.predict_impact()

                # 2. Threat Assessment: Is it hitting a city?
                r.is_threat = False
                for city in self.cities:
                    if city.active and city.rect.left < r.predicted_impact_x < city.rect.right:
                        r.is_threat = True
                        break

            # 3. Prioritization List
            if r.is_threat and r.intercepted_by is None:
                # Calculate urgency (distance to ground)
                urgency = HEIGHT - r.pos[1]
                threats.append((urgency, r))

        # Sort threats by urgency (lowest distance to ground first)
        threats.sort(key=lambda x: x[0])

        # 4. Fire Control: Launch Interceptors
        for _, rocket in threats:
            if self.ammo > 0:
                # Calculate lead collision point
                intercept_point = self.calculate_intercept_point(rocket)

                # Launch
                interceptor = Rocket(is_enemy=False, start_pos=BATTERY_POS, target_pos=intercept_point)
                interceptor.target_rocket = rocket

                self.interceptors.append(interceptor)
                self.ammo -= 1
                rocket.intercepted_by = interceptor  # Mark as handled

                # Visual effect for launch
                self.explosions.append(Explosion(BATTERY_POS[0], BATTERY_POS[1]))

    def run(self):
        running = True
        spawn_timer = 0

        while running:
            # --- Events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # Reload
                        self.ammo = 20

            # --- Spawning ---
            spawn_timer += 1
            if spawn_timer > 30:  # Spawn rocket every 0.5s approx
                self.rockets.append(Rocket(is_enemy=True))
                spawn_timer = 0

            # --- Logic ---
            self.radar_system()

            # Update Enemies
            for r in self.rockets:
                if r.active:
                    status = r.update()
                    if status == "ground_hit":
                        self.explosions.append(Explosion(r.pos[0], r.pos[1]))
                        if r.is_threat:
                            self.score_failed += 1
                            # Check city damage
                            for c in self.cities:
                                if c.rect.collidepoint(r.pos[0], r.pos[1]):
                                    c.active = False  # City destroyed

            # Update Interceptors
            for i in self.interceptors:
                if i.active:
                    i.update()
                    # Check collision with target
                    if i.target_rocket and i.target_rocket.active:
                        dist = np.linalg.norm(i.pos - i.target_rocket.pos)
                        if dist < 20:  # Proximity Fuze radius
                            # BOOM
                            self.explosions.append(Explosion(i.target_rocket.pos[0], i.target_rocket.pos[1]))
                            i.target_rocket.active = False
                            i.active = False
                            self.score_saved += 1

            # Update Explosions
            for e in self.explosions:
                e.update()

            # Cleanup
            self.rockets = [r for r in self.rockets if r.active]
            self.interceptors = [i for i in self.interceptors if i.active]
            self.explosions = [e for e in self.explosions if e.active]

            # --- Drawing ---
            self.screen.fill(BLACK)

            # Ground
            pygame.draw.rect(self.screen, (30, 30, 40), (0, HEIGHT - 30, WIDTH, 30))

            # Cities
            for c in self.cities:
                c.draw(self.screen)

            # Battery
            pygame.draw.circle(self.screen, CYAN, BATTERY_POS, 10)
            pygame.draw.circle(self.screen, BLUE := (50, 50, 255), BATTERY_POS, 20, 2)

            # Entities
            for r in self.rockets: r.draw(self.screen)
            for i in self.interceptors: i.draw(self.screen)
            for e in self.explosions: e.draw(self.screen)

            # UI
            ammo_text = self.font.render(f"INTERCEPTORS: {self.ammo} (Press R to Reload)", True, WHITE)
            saved_text = self.font.render(f"THREATS STOPPED: {self.score_saved}", True, GREEN)
            fail_text = self.font.render(f"IMPACTS: {self.score_failed}", True, RED)

            self.screen.blit(ammo_text, (10, 10))
            self.screen.blit(saved_text, (10, 30))
            self.screen.blit(fail_text, (10, 50))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    sim = IronDomeSim()
    sim.run()