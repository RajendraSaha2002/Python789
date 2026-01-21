import pygame
import math

# --- Configuration ---
WIDTH, HEIGHT = 1000, 800
FPS = 60

# Physics Constants
GRAVITY = 0.5  # Downward force
STIFFNESS = 0.8  # Spring stiffness (k) -> Higher = Harder tissue
DAMPING = 0.95  # Energy loss (friction) -> Lower = More wobble
REST_DISTANCE = 30  # Distance between nodes
TEAR_THRESHOLD = 1000  # Force required to rip tissue automatically (optional)

# Colors
COLOR_BG = (20, 20, 30)
COLOR_TISSUE = (200, 100, 100)
COLOR_SPRING = (150, 70, 70)
COLOR_SCALPEL = (0, 255, 255)  # Cyan
COLOR_FORCEPS = (255, 255, 0)  # Yellow


class Particle:
    def __init__(self, x, y, pinned=False):
        self.x = x
        self.y = y
        self.old_x = x
        self.old_y = y
        self.pinned = pinned
        self.mass = 1.0
        self.forces_x = 0
        self.forces_y = 0

    def apply_force(self, fx, fy):
        self.forces_x += fx
        self.forces_y += fy

    def update(self):
        if self.pinned:
            self.forces_x = 0
            self.forces_y = 0
            return

        # Verlet Integration
        # x_new = 2*x - x_old + a * dt^2
        vx = (self.x - self.old_x) * DAMPING
        vy = (self.y - self.old_y) * DAMPING

        self.old_x = self.x
        self.old_y = self.y

        # Accumulate Gravity
        self.forces_y += GRAVITY

        # Update Position
        self.x += vx + self.forces_x
        self.y += vy + self.forces_y

        # Reset forces
        self.forces_x = 0
        self.forces_y = 0

        # Floor constraint (optional)
        if self.y > HEIGHT - 20:
            self.y = HEIGHT - 20
            self.old_y = self.y + vy * 0.5  # Bounce slightly


class Spring:
    def __init__(self, p1, p2, length):
        self.p1 = p1
        self.p2 = p2
        self.length = length
        self.active = True

    def update(self):
        if not self.active: return

        dx = self.p1.x - self.p2.x
        dy = self.p1.y - self.p2.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist == 0: dist = 0.001

        # Hooke's Law: F = k * (current_length - rest_length)
        diff = (self.length - dist) / dist

        # We apply half the correction to each particle (Relaxation method)
        # This is more stable for cloth/tissue than pure force addition
        offset_x = dx * diff * 0.5 * STIFFNESS
        offset_y = dy * diff * 0.5 * STIFFNESS

        if not self.p1.pinned:
            self.p1.x += offset_x
            self.p1.y += offset_y

        if not self.p2.pinned:
            self.p2.x -= offset_x
            self.p2.y -= offset_y

    def draw(self, screen):
        if self.active:
            pygame.draw.line(screen, COLOR_SPRING, (int(self.p1.x), int(self.p1.y)),
                             (int(self.p2.x), int(self.p2.y)), 2)


class SoftBody:
    def __init__(self, start_x, start_y, rows, cols):
        self.particles = []
        self.springs = []
        self.rows = rows
        self.cols = cols

        # 1. Create Particles Grid
        for r in range(rows):
            for c in range(cols):
                # Pin the top row to simulate hanging tissue
                pinned = (r == 0)
                p = Particle(start_x + c * REST_DISTANCE, start_y + r * REST_DISTANCE, pinned)
                self.particles.append(p)

        # 2. Create Springs (Structural)
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c

                # Connect Right
                if c < cols - 1:
                    self.add_spring(idx, idx + 1)

                # Connect Down
                if r < rows - 1:
                    self.add_spring(idx, idx + cols)

                # Connect Diagonal (Shear springs for stability)
                if r < rows - 1 and c < cols - 1:
                    self.add_spring(idx, idx + cols + 1)
                    self.add_spring(idx + 1, idx + cols)

    def add_spring(self, i1, i2):
        p1 = self.particles[i1]
        p2 = self.particles[i2]
        dist = math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)
        self.springs.append(Spring(p1, p2, dist))

    def update(self):
        # Update Springs (Constraints) multiple times for stiffness stability
        for _ in range(3):
            for s in self.springs:
                s.update()

        # Update Particles (Integration)
        for p in self.particles:
            p.update()

    def draw(self, screen):
        # Draw Springs (Tissue Interior)
        for s in self.springs:
            s.draw(screen)

        # Draw Particles (Nodes)
        for p in self.particles:
            color = (255, 100, 100) if not p.pinned else (100, 100, 255)
            pygame.draw.circle(screen, color, (int(p.x), int(p.y)), 3)

    def cut(self, start_pos, end_pos):
        """ Check if a cut line intersects any spring and disable it. """
        p1 = start_pos
        p2 = end_pos

        for s in self.springs:
            if not s.active: continue

            # Spring segment
            p3 = (s.p1.x, s.p1.y)
            p4 = (s.p2.x, s.p2.y)

            if intersect(p1, p2, p3, p4):
                s.active = False  # CUT!


def intersect(p1, p2, p3, p4):
    """ Helper: Line segment intersection test. """

    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


# --- Main Interaction ---

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Soft-Tissue Surgical Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    # Create Tissue
    tissue = SoftBody(300, 100, 20, 15)

    # Tool State
    selected_particle = None
    mouse_prev = (0, 0)

    # Modes: 'forceps' (Drag) or 'scalpel' (Cut)
    tool_mode = 'forceps'

    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        mouse_curr = (mx, my)

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    tool_mode = 'forceps'
                elif event.key == pygame.K_2:
                    tool_mode = 'scalpel'
                elif event.key == pygame.K_r:
                    tissue = SoftBody(300, 100, 20, 15)  # Reset

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left Click
                    if tool_mode == 'forceps':
                        # Find nearest particle
                        min_dist = 50
                        closest = None
                        for p in tissue.particles:
                            d = math.hypot(p.x - mx, p.y - my)
                            if d < min_dist:
                                min_dist = d
                                closest = p
                        selected_particle = closest

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    selected_particle = None

        # --- Physics Updates ---

        # Handle Dragging (Forceps)
        if selected_particle and tool_mode == 'forceps':
            # Move particle towards mouse (Elastic interaction)
            # Instead of hard-setting position, we act like a strong spring
            dx = mx - selected_particle.x
            dy = my - selected_particle.y
            selected_particle.x += dx * 0.5  # Follow mouse tightly
            selected_particle.y += dy * 0.5
            # Zero out velocity to prevent orbiting
            selected_particle.old_x = selected_particle.x
            selected_particle.old_y = selected_particle.y

        # Handle Cutting (Scalpel)
        if pygame.mouse.get_pressed()[0] and tool_mode == 'scalpel':
            # Cut logic: Check intersection between last frame mouse and current frame mouse
            tissue.cut(mouse_prev, mouse_curr)

        tissue.update()

        # --- Rendering ---
        screen.fill(COLOR_BG)

        # Draw Tissue
        tissue.draw(screen)

        # Draw Tool
        if tool_mode == 'forceps':
            cursor_color = COLOR_FORCEPS
            pygame.draw.circle(screen, cursor_color, (mx, my), 8, 2)
            if selected_particle:
                pygame.draw.line(screen, cursor_color, (mx, my),
                                 (selected_particle.x, selected_particle.y), 1)
        else:
            cursor_color = COLOR_SCALPEL
            pygame.draw.line(screen, cursor_color, (mx, my - 10), (mx, my + 10), 2)
            # Draw trail if cutting
            if pygame.mouse.get_pressed()[0]:
                pygame.draw.line(screen, (255, 0, 0), mouse_prev, mouse_curr, 3)

        # UI Instructions
        text_mode = font.render(f"Tool: {tool_mode.upper()} (Press 1/2 to switch)", True, cursor_color)
        text_ctrl = font.render("Controls: Left Click to Drag/Cut | 'R' to Reset", True, (200, 200, 200))
        screen.blit(text_mode, (10, 10))
        screen.blit(text_ctrl, (10, 35))

        pygame.display.flip()
        mouse_prev = mouse_curr
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()