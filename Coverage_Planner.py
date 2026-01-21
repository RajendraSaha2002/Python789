import pygame
import math
import numpy as np

# --- Configuration ---
WIDTH, HEIGHT = 1200, 800
FPS = 60

# Colors
COLOR_BG = (20, 20, 30)  # Dark Terrain
COLOR_MTN = (100, 80, 60)  # Mountain Brown
COLOR_RADAR = (0, 255, 255)  # Cyan Center
COLOR_BEAM = (255, 255, 0)  # Yellow Radar Fan
COLOR_SHADOW = (0, 0, 0)  # Shadow
COLOR_TEXT = (200, 200, 200)

# Raycasting Settings
RAY_COUNT = 360  # Number of rays (resolution)
MAX_DEPTH = 800  # Max radar range


class Obstacle:
    """A Mountain defined by a polygon."""

    def __init__(self, points):
        self.points = points  # List of (x,y) tuples
        # Pre-calculate edges for intersection testing
        self.edges = []
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            self.edges.append((p1, p2))

    def draw(self, screen):
        pygame.draw.polygon(screen, COLOR_MTN, self.points)
        pygame.draw.polygon(screen, (150, 120, 100), self.points, 2)  # Outline


class Radar:
    """A movable radar unit."""

    def __init__(self, x, y):
        self.pos = [x, y]
        self.radius = 15
        self.dragging = False
        self.poly_points = []  # The calculated visibility polygon

    def update_visibility(self, obstacles):
        """
        The Core Raycasting Logic.
        Casts 360 rays. Checks intersection with all mountain edges.
        """
        self.poly_points = [self.pos]  # Start at center

        # Collect all edges from all obstacles + Screen Boundaries
        all_edges = []
        for obs in obstacles:
            all_edges.extend(obs.edges)

        # Add screen borders as edges to stop rays
        w, h = WIDTH, HEIGHT
        all_edges.extend([
            ((0, 0), (w, 0)), ((w, 0), (w, h)), ((w, h), (0, h)), ((0, h), (0, 0))
        ])

        # Cast Rays
        # Optimization: We cast rays at fixed angle intervals.
        # Ideally, we cast at obstacle vertices, but fixed interval is easier for "Fan" look.
        start_angle = 0
        step = 360 / RAY_COUNT

        rx, ry = self.pos

        for i in range(RAY_COUNT):
            angle_deg = start_angle + i * step
            angle_rad = math.radians(angle_deg)

            dx = math.cos(angle_rad)
            dy = math.sin(angle_rad)

            # The Ray vector (normalized)

            closest_dist = MAX_DEPTH
            closest_pt = (rx + dx * MAX_DEPTH, ry + dy * MAX_DEPTH)

            # Check against every wall
            for p1, p2 in all_edges:
                pt = self.get_intersection(rx, ry, dx, dy, p1, p2)
                if pt:
                    dist = math.hypot(pt[0] - rx, pt[1] - ry)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_pt = pt

            self.poly_points.append(closest_pt)

    def get_intersection(self, rx, ry, rdx, rdy, p1, p2):
        """
        Finds intersection between Ray (rx,ry)+t*(rdx,rdy) and Segment p1-p2.
        Standard Vector math.
        """
        x1, y1 = p1
        x2, y2 = p2

        # Segment vector
        sdx = x2 - x1
        sdy = y2 - y1

        # Ray-Segment intersection solver
        # r_px + r_dx * T1 = s_px + s_dx * T2

        mag = rdx * sdy - rdy * sdx
        if mag == 0: return None  # Parallel

        t2 = (rdx * (y1 - ry) + rdy * (rx - x1)) / mag
        t1 = (x1 + sdx * t2 - rx) / rdx if rdx != 0 else (y1 + sdy * t2 - ry) / rdy

        # t1 is distance along ray (must be > 0)
        # t2 is distance along segment (must be 0 <= t2 <= 1)
        if t1 > 0 and 0 <= t2 <= 1:
            return (rx + rdx * t1, ry + rdy * t1)
        return None

    def draw(self, screen):
        # Draw the Visibility Fan
        if len(self.poly_points) > 2:
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(s, (255, 255, 0, 100), self.poly_points)  # Transparent Yellow
            screen.blit(s, (0, 0))

            # Draw Outline
            # pygame.draw.lines(screen, (255, 255, 0), True, self.poly_points, 1)

        # Draw Unit
        pygame.draw.circle(screen, COLOR_RADAR, (int(self.pos[0]), int(self.pos[1])), self.radius)
        pygame.draw.circle(screen, (255, 255, 255), (int(self.pos[0]), int(self.pos[1])), self.radius, 2)


class CoveragePlanner:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("360° Sector Coverage Planner (S-400 Deployment)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 16)
        self.large_font = pygame.font.SysFont("Consolas", 24, bold=True)

        # Create Map
        self.radars = [Radar(200, 400)]  # Start with one

        # Create Mountains (Polygons)
        self.obstacles = [
            Obstacle([(600, 200), (800, 250), (750, 500), (550, 450)]),  # Central Peak
            Obstacle([(100, 100), (300, 100), (300, 200), (100, 200)]),  # NW Plateau
            Obstacle([(900, 600), (1100, 600), (1000, 750)])  # SE Peak
        ]

        self.coverage_pct = 0.0

        # Drawing Mode State
        self.drawing_mode = False
        self.new_poly_points = []

    def calculate_coverage(self):
        """
        Calculates the % of the screen covered by radar.
        Uses a separate surface mask to handle overlapping transparencies.
        """
        mask = pygame.Surface((WIDTH, HEIGHT))
        mask.fill((0, 0, 0))  # Black = Uncovered

        for r in self.radars:
            if len(r.poly_points) > 2:
                # Draw white polygons on mask
                pygame.draw.polygon(mask, (255, 255, 255), r.poly_points)

        # Subtract Obstacle areas (radars can't see 'inside' a mountain even if on top)
        for obs in self.obstacles:
            pygame.draw.polygon(mask, (0, 0, 0), obs.points)

        # Count pixels
        # pygame.surfarray is fast enough for this resolution if done efficiently
        # We only take the red channel since it's grayscale
        pixels = pygame.surfarray.pixels2d(mask)
        non_zero = np.count_nonzero(pixels)

        total_pixels = WIDTH * HEIGHT
        self.coverage_pct = (non_zero / total_pixels) * 100

    def run(self):
        running = True
        calc_timer = 0

        while running:
            mx, my = pygame.mouse.get_pos()

            # --- Events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # Input Handling
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left Click
                        if self.drawing_mode:
                            self.new_poly_points.append((mx, my))
                        else:
                            # Check radar drag
                            for r in self.radars:
                                if math.hypot(mx - r.pos[0], my - r.pos[1]) < r.radius:
                                    r.dragging = True
                                    break

                    elif event.button == 3:  # Right Click
                        if self.drawing_mode:
                            # Finish Mountain
                            if len(self.new_poly_points) > 2:
                                self.obstacles.append(Obstacle(self.new_poly_points))
                            self.new_poly_points = []
                            self.drawing_mode = False
                        else:
                            # Place new Radar
                            self.radars.append(Radar(mx, my))

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        for r in self.radars: r.dragging = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m:  # Toggle Mountain Maker
                        self.drawing_mode = not self.drawing_mode
                        self.new_poly_points = []
                    elif event.key == pygame.K_c:  # Clear Radars
                        self.radars = [Radar(100, 100)]

            # --- Update ---
            for r in self.radars:
                if r.dragging:
                    r.pos = [mx, my]
                # Recalculate rays
                # (Ideally only do this if pos changed, but current CPU handles 60fps fine)
                r.update_visibility(self.obstacles)

            # Update coverage calc periodically (expensive operation)
            calc_timer += 1
            if calc_timer > 10:  # Every 10 frames
                self.calculate_coverage()
                calc_timer = 0

            # --- Draw ---
            self.screen.fill(COLOR_BG)

            # Draw Mountains
            for obs in self.obstacles:
                obs.draw(self.screen)

            # Draw Radars (and their fans)
            for r in self.radars:
                r.draw(self.screen)

            # Draw Polygon in progress
            if self.drawing_mode and len(self.new_poly_points) > 0:
                pts = self.new_poly_points + [(mx, my)]
                if len(pts) > 1:
                    pygame.draw.lines(self.screen, (255, 255, 255), False, pts, 2)

            # --- UI Overlay ---
            # Header
            header_rect = pygame.Rect(0, 0, WIDTH, 50)
            pygame.draw.rect(self.screen, (30, 30, 40), header_rect)
            pygame.draw.line(self.screen, (100, 100, 100), (0, 50), (WIDTH, 50))

            # Controls Text
            controls = [
                "L-Click Drag: Move Radar",
                "R-Click: Place New Radar",
                "'M' Key: Draw Mountain Mode",
                "'C' Key: Clear Radars"
            ]
            for i, txt in enumerate(controls):
                s = self.font.render(txt, True, COLOR_TEXT)
                self.screen.blit(s, (10 + i * 220, 15))

            # Metric Box
            box_rect = pygame.Rect(WIDTH - 220, HEIGHT - 80, 200, 60)
            pygame.draw.rect(self.screen, (0, 0, 0), box_rect)
            pygame.draw.rect(self.screen, COLOR_RADAR, box_rect, 2)

            score_color = (255, 50, 50)  # Red
            if self.coverage_pct > 50: score_color = (255, 200, 0)  # Yellow
            if self.coverage_pct > 80: score_color = (50, 255, 50)  # Green

            score_txt = self.large_font.render(f"COVERAGE: {self.coverage_pct:.1f}%", True, score_color)
            label_txt = self.font.render("SECTOR GAP ANALYSIS", True, (150, 150, 150))

            self.screen.blit(label_txt, (box_rect.x + 20, box_rect.y + 10))
            self.screen.blit(score_txt, (box_rect.x + 20, box_rect.y + 30))

            # Drawing Mode Indicator
            if self.drawing_mode:
                ind_txt = self.large_font.render("MOUNTAIN BUILDER ACTIVE", True, (255, 100, 100))
                self.screen.blit(ind_txt, (WIDTH // 2 - 150, HEIGHT - 50))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    sim = CoveragePlanner()
    sim.run()