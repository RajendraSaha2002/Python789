import pygame
import numpy as np
import random

# --- Configuration & Physics Constants ---
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
GRID_SIZE = 80  # N x N lattice
CELL_SIZE = 8  # Pixel size of each atom
MARGIN = 200  # Right side margin for UI

# Simulation Speeds
STEPS_PER_FRAME = 2000  # Kinetic Monte Carlo steps per render cycle

# Species IDs
EMPTY = 0
CO = 1
OXYGEN = 2

# Colors
COLOR_BG = (30, 30, 30)
COLOR_GRID_BG = (255, 255, 255)  # Empty = White
COLOR_CO = (50, 100, 255)  # CO = Blue
COLOR_O = (255, 50, 50)  # O = Red
COLOR_REACTION = (50, 255, 50)  # CO2 Leaving = Green Flash
COLOR_TEXT = (200, 200, 200)


class CatalystSimulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Kinetic Monte Carlo: CO Oxidation on Platinum Surface")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.title_font = pygame.font.SysFont("Arial", 22, bold=True)

        # The Grid: 0=Empty, 1=CO, 2=O
        self.grid = np.zeros((GRID_SIZE, GRID_SIZE), dtype=int)

        # Simulation State
        self.y_co = 0.50  # Partial pressure of CO (Mole Fraction)
        self.running = True
        self.reaction_count = 0
        self.reactions_this_frame = []  # List of (x,y) coords to flash green
        self.total_steps = 0
        self.total_reactions = 0

        # Neighborhood offsets (Up, Down, Left, Right)
        self.neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def get_random_neighbor(self, x, y):
        """Pick a random neighbor with Periodic Boundary Conditions."""
        dx, dy = random.choice(self.neighbors)
        nx = (x + dx) % GRID_SIZE
        ny = (y + dy) % GRID_SIZE
        return nx, ny

    def check_reaction(self, x, y, species_type):
        """
        Check if the newly adsorbed species at (x,y) can react with a neighbor.
        Mechanism: CO(s) + O(s) -> CO2(g) + 2 Empty Sites
        """
        # Shuffle neighbors to check randomly
        random.shuffle(self.neighbors)

        target_species = OXYGEN if species_type == CO else CO

        for dx, dy in self.neighbors:
            nx = (x + dx) % GRID_SIZE
            ny = (y + dy) % GRID_SIZE

            if self.grid[nx, ny] == target_species:
                # REACTION OCCURRED!
                # 1. Desorb both (turn to empty)
                self.grid[x, y] = EMPTY
                self.grid[nx, ny] = EMPTY

                # 2. Record stats
                self.reaction_count += 1
                self.reactions_this_frame.append((x, y))
                self.reactions_this_frame.append((nx, ny))
                return True  # Reacted

        return False  # No reaction found

    def kmc_step(self):
        """
        Perform one Monte Carlo step.
        Ziff-Gulari-Barshad (ZGB) Model Logic.
        """
        # 1. Select a random site on the surface
        rx = random.randint(0, GRID_SIZE - 1)
        ry = random.randint(0, GRID_SIZE - 1)

        # 2. Determine which molecule tries to land based on Partial Pressure
        # y_co is the probability that the impinging molecule is CO
        if random.random() < self.y_co:
            # === ATTEMPT CO ADSORPTION ===
            # CO requires 1 empty site
            if self.grid[rx, ry] == EMPTY:
                self.grid[rx, ry] = CO
                # Check for immediate reaction with neighbors
                self.check_reaction(rx, ry, CO)

        else:
            # === ATTEMPT O2 ADSORPTION ===
            # O2 requires 2 adjacent empty sites to dissociate into 2O
            if self.grid[rx, ry] == EMPTY:
                # Pick a random neighbor for the second oxygen atom
                nx, ny = self.get_random_neighbor(rx, ry)

                if self.grid[nx, ny] == EMPTY:
                    # Successful O2 adsorption (dissociative)
                    self.grid[rx, ry] = OXYGEN
                    self.grid[nx, ny] = OXYGEN

                    # Check reaction for first O atom
                    if not self.check_reaction(rx, ry, OXYGEN):
                        # If first didn't react (and vanish), check second O atom
                        # (Note: if first reacted, the site (rx,ry) is now empty,
                        # but (nx,ny) is still O, so we check it)
                        pass

                        # Check reaction for second O atom (if it's still there)
                    if self.grid[nx, ny] == OXYGEN:
                        self.check_reaction(nx, ny, OXYGEN)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            self.y_co = min(1.0, self.y_co + 0.005)
        if keys[pygame.K_DOWN]:
            self.y_co = max(0.0, self.y_co - 0.005)

        # Reset board
        if keys[pygame.K_r]:
            self.grid.fill(EMPTY)
            self.total_reactions = 0
            self.total_steps = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def draw_ui(self):
        # Draw Sidebar
        ui_x = WINDOW_WIDTH - MARGIN + 10
        y_offset = 20

        def draw_text(text, color=COLOR_TEXT, font=self.font):
            nonlocal y_offset
            img = font.render(text, True, color)
            self.screen.blit(img, (ui_x, y_offset))
            y_offset += 25

        draw_text("Controls", color=(255, 255, 0), font=self.title_font)
        draw_text("UP/DOWN: Adjust CO %")
        draw_text("R: Reset Grid")
        y_offset += 10

        draw_text("Simulation Stats", color=(255, 255, 0), font=self.title_font)
        draw_text(f"CO Partial Pressure: {self.y_co:.3f}")
        draw_text(f"O2 Partial Pressure: {1.0 - self.y_co:.3f}")
        y_offset += 10

        # Calculate coverage
        total_cells = GRID_SIZE * GRID_SIZE
        co_cov = np.sum(self.grid == CO) / total_cells
        o_cov = np.sum(self.grid == OXYGEN) / total_cells

        draw_text(f"CO Coverage: {co_cov * 100:.1f}%", COLOR_CO)
        draw_text(f"O Coverage: {o_cov * 100:.1f}%", COLOR_O)

        # Calculate Rate (Reaction Probability per step)
        rate = 0
        if self.total_steps > 0:
            rate = self.reaction_count / STEPS_PER_FRAME
        draw_text(f"Reaction Rate: {rate:.4f}", COLOR_REACTION)

        y_offset += 20
        draw_text("Legend", color=(255, 255, 0), font=self.title_font)
        pygame.draw.rect(self.screen, COLOR_GRID_BG, (ui_x, y_offset, 15, 15))
        draw_text("  Empty Site")
        pygame.draw.rect(self.screen, COLOR_CO, (ui_x, y_offset, 15, 15))
        draw_text("  CO Molecule")
        pygame.draw.rect(self.screen, COLOR_O, (ui_x, y_offset, 15, 15))
        draw_text("  Oxygen Atom")
        pygame.draw.rect(self.screen, COLOR_REACTION, (ui_x, y_offset, 15, 15))
        draw_text("  CO2 formation")

        # Poisoning warning
        if co_cov > 0.90:
            y_offset += 20
            draw_text("WARNING: POISONED!", (255, 0, 0), self.title_font)
            draw_text("Catalyst surface is saturated", (255, 100, 100))
            draw_text("with CO. O2 cannot land.", (255, 100, 100))

    def run(self):
        while self.running:
            self.handle_input()

            # Reset frame stats
            self.reaction_count = 0
            self.reactions_this_frame = []

            # Run Physics Steps (KMC Loop)
            for _ in range(STEPS_PER_FRAME):
                self.kmc_step()

            self.total_steps += STEPS_PER_FRAME
            self.total_reactions += self.reaction_count

            # --- Drawing ---
            self.screen.fill(COLOR_BG)

            # Lock surface for pixel manipulation (faster than drawing rects)
            # Create a surface for the grid
            grid_surf = pygame.Surface((GRID_SIZE * CELL_SIZE, GRID_SIZE * CELL_SIZE))
            grid_surf.fill(COLOR_GRID_BG)  # Default White

            # We can use numpy masking to draw faster if needed,
            # but simple rect iteration is fine for this grid size.

            # Draw CO (Blue)
            co_indices = np.where(self.grid == CO)
            for x, y in zip(*co_indices):
                pygame.draw.rect(grid_surf, COLOR_CO,
                                 (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))

            # Draw Oxygen (Red)
            o_indices = np.where(self.grid == OXYGEN)
            for x, y in zip(*o_indices):
                pygame.draw.rect(grid_surf, COLOR_O,
                                 (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))

            # Draw Reactions (Green Flash)
            for rx, ry in self.reactions_this_frame:
                pygame.draw.rect(grid_surf, COLOR_REACTION,
                                 (rx * CELL_SIZE, ry * CELL_SIZE, CELL_SIZE, CELL_SIZE))

            # Blit grid to main screen
            self.screen.blit(grid_surf, (20, 20))

            # Draw UI
            self.draw_ui()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    sim = CatalystSimulation()
    sim.run()