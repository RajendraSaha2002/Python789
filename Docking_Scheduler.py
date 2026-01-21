import pygame
import random
import time

# --- Configuration ---
WIDTH, HEIGHT = 1100, 700
FPS = 60

# Colors
COLOR_BG = (30, 40, 50)  # Ocean Dark
COLOR_LAND = (50, 50, 60)  # Concrete Dock
COLOR_PIER_FREE = (46, 204, 113)
COLOR_PIER_BUSY = (231, 76, 60)
COLOR_PIER_RESTRICTED = (241, 196, 15)  # Yellow/Orange for specialized
COLOR_TEXT = (255, 255, 255)

# Logistics Constraints
TOTAL_FUEL_TRUCKS = 2


class ShipType:
    CARRIER = "Aircraft Carrier (CVN)"
    SUB = "Nuclear Sub (SSN)"
    DESTROYER = "Destroyer (DDG)"
    FRIGATE = "Frigate (FFG)"
    DAMAGED = "Damaged Cruiser (CG)"


class Ship:
    def __init__(self, name, s_type, needs_fuel=False):
        self.name = name
        self.type = s_type
        self.needs_fuel = needs_fuel
        self.assigned_pier = None
        self.error_msg = ""

        # Visual properties
        self.rect = pygame.Rect(0, 0, 140, 40)
        self.target_pos = None

        # Set color based on type
        if s_type == ShipType.CARRIER:
            self.color = (100, 100, 120)  # Huge Grey
            self.rect.width = 180
            self.rect.height = 50
        elif s_type == ShipType.SUB:
            self.color = (20, 20, 20)  # Black
        elif s_type == ShipType.DAMAGED:
            self.color = (200, 100, 100)  # Red-ish
        else:
            self.color = (150, 150, 150)  # Standard Grey

    def draw(self, screen, font):
        # Move animation
        if self.target_pos:
            dx = self.target_pos[0] - self.rect.x
            dy = self.target_pos[1] - self.rect.y
            self.rect.x += dx * 0.1
            self.rect.y += dy * 0.1

        pygame.draw.rect(screen, self.color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 2, border_radius=10)

        # Labels
        lbl = font.render(self.name, True, COLOR_TEXT)
        type_lbl = font.render(self.type.split()[0], True, (200, 200, 200))
        screen.blit(lbl, (self.rect.x + 10, self.rect.y + 5))
        screen.blit(type_lbl, (self.rect.x + 10, self.rect.y + 20))

        if self.needs_fuel:
            pygame.draw.circle(screen, (255, 165, 0), (self.rect.right - 10, self.rect.top + 10), 5)


class Pier:
    def __init__(self, p_id, p_type, x, y):
        self.id = p_id
        self.type = p_type  # "Standard", "Deep Draft", "High Security", "Drydock"
        self.rect = pygame.Rect(x, y, 220, 80)
        self.ship = None

    def draw(self, screen, font):
        # Color based on type/status
        if self.ship:
            col = COLOR_PIER_BUSY
        elif self.type == "Standard":
            col = COLOR_PIER_FREE
        else:
            col = COLOR_PIER_RESTRICTED

        # Draw Dock
        pygame.draw.rect(screen, col, self.rect, border_radius=5)
        # Water cutout visual
        pygame.draw.rect(screen, COLOR_BG, (self.rect.x + 10, self.rect.y + 10, 200, 60), border_radius=15)

        # Label
        lbl = font.render(f"{self.id}: {self.type}", True, (200, 200, 200))
        screen.blit(lbl, (self.rect.x, self.rect.y - 20))


class SchedulerApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Naval Base Logistics Scheduler")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)
        self.font_big = pygame.font.SysFont("Consolas", 20, bold=True)

        # Define Base Layout (Piers)
        self.piers = [
            Pier("P-1", "Deep Draft", 700, 100),  # For Carriers
            Pier("P-2", "High Security", 700, 220),  # For Subs
            Pier("P-3", "Drydock", 700, 340),  # For Repairs
            Pier("P-4", "Standard", 700, 460),  # General
            Pier("P-5", "Standard", 700, 580)  # General
        ]

        # Define Incoming Queue
        self.queue = [
            Ship("USS Gerald Ford", ShipType.CARRIER, needs_fuel=True),
            Ship("USS Virginia", ShipType.SUB),
            Ship("USS Fitzgerald", ShipType.DAMAGED),
            Ship("USS Arleigh Burke", ShipType.DESTROYER, needs_fuel=True),
            Ship("USS Perry", ShipType.FRIGATE, needs_fuel=True)  # Will cause fuel conflict
        ]

        # Position ships in queue area
        for i, s in enumerate(self.queue):
            s.rect.x = 50
            s.rect.y = 100 + i * 80
            s.target_pos = (s.rect.x, s.rect.y)

        self.messages = []  # Log messages

    def assign_ships(self):
        """THE ALGORITHM: Matches ships to piers based on constraints."""
        self.log("Starting Auto-Scheduler...")

        # Reset Piers
        for p in self.piers: p.ship = None
        unassigned = []

        # Logic Loop
        for ship in self.queue:
            assigned = False

            # Constraint 1: Carriers need Deep Draft
            if ship.type == ShipType.CARRIER:
                target_pier = self.find_pier("Deep Draft")
                if target_pier:
                    self.dock_ship(ship, target_pier)
                    assigned = True

            # Constraint 2: Subs need Security
            elif ship.type == ShipType.SUB:
                target_pier = self.find_pier("High Security")
                if target_pier:
                    self.dock_ship(ship, target_pier)
                    assigned = True

            # Constraint 3: Damaged needs Drydock
            elif ship.type == ShipType.DAMAGED:
                target_pier = self.find_pier("Drydock")
                if target_pier:
                    self.dock_ship(ship, target_pier)
                    assigned = True

            # Constraint 4: Destroyers/Frigates go to Standard (or specialized if empty)
            else:
                # Try standard first
                target_pier = self.find_pier("Standard")
                if not target_pier:
                    # Fallback to Deep Draft if empty? (Optimization logic)
                    target_pier = self.find_pier("Deep Draft")

                if target_pier:
                    self.dock_ship(ship, target_pier)
                    assigned = True

            if not assigned:
                ship.error_msg = "NO SUITABLE BERTH"
                ship.target_pos = (350, ship.rect.y)  # Move to "Holding Pattern" middle
                unassigned.append(ship)
                self.log(f"CONFLICT: {ship.name} ({ship.type}) could not dock.")

        self.check_fuel_conflict()

    def find_pier(self, p_type):
        """Helper to find first empty pier of specific type."""
        for p in self.piers:
            if p.type == p_type and p.ship is None:
                return p
        return None

    def dock_ship(self, ship, pier):
        pier.ship = ship
        ship.assigned_pier = pier
        # Update ship visual target to inside the pier
        ship.target_pos = (pier.rect.x + 20, pier.rect.y + 15)
        self.log(f"Assigned {ship.name} -> {pier.id}")

    def check_fuel_conflict(self):
        """Checks if we have enough fuel trucks for docked ships."""
        fuel_demand = 0
        ships_needing_fuel = []

        for p in self.piers:
            if p.ship and p.ship.needs_fuel:
                fuel_demand += 1
                ships_needing_fuel.append(p.ship.name)

        if fuel_demand > TOTAL_FUEL_TRUCKS:
            self.log(f"LOGISTICS ERROR: Fuel Demand ({fuel_demand}) > Supply ({TOTAL_FUEL_TRUCKS})")
            self.log(f"Affected: {', '.join(ships_needing_fuel)}")
            self.log("SUGGESTION: Reschedule refueling for " + ships_needing_fuel[-1])
        else:
            self.log(f"Fuel Logistics OK. Trucks in use: {fuel_demand}/{TOTAL_FUEL_TRUCKS}")

    def log(self, msg):
        print(msg)
        self.messages.append(msg)
        if len(self.messages) > 8:
            self.messages.pop(0)

    def run(self):
        running = True
        while running:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Click Logic (Simple buttons)
                    mx, my = pygame.mouse.get_pos()
                    if 450 < mx < 650 and 50 < my < 100:  # Schedule Button
                        self.assign_ships()
                    elif 450 < mx < 650 and 120 < my < 170:  # Reset
                        self.__init__()  # Quick hack reset for demo

            # Draw
            self.screen.fill(COLOR_BG)

            # Draw Land Area
            pygame.draw.rect(self.screen, COLOR_LAND, (600, 0, 500, HEIGHT))

            # Draw Piers
            for p in self.piers:
                p.draw(self.screen, self.font)

            # Draw Ships
            for s in self.queue:
                s.draw(self.screen, self.font)
                if s.error_msg:
                    err = self.font.render(s.error_msg, True, (255, 50, 50))
                    self.screen.blit(err, (s.rect.x, s.rect.bottom + 2))

            # UI Buttons
            pygame.draw.rect(self.screen, (0, 150, 200), (450, 50, 200, 50), border_radius=5)
            btn_txt = self.font_big.render("AUTO-SCHEDULE", True, COLOR_TEXT)
            self.screen.blit(btn_txt, (470, 65))

            pygame.draw.rect(self.screen, (150, 50, 50), (450, 120, 200, 50), border_radius=5)
            rst_txt = self.font_big.render("RESET SCENARIO", True, COLOR_TEXT)
            self.screen.blit(rst_txt, (465, 135))

            # Logistics Info
            fuel_txt = self.font_big.render(f"FUEL TRUCKS: {TOTAL_FUEL_TRUCKS}", True, (255, 200, 0))
            self.screen.blit(fuel_txt, (50, 30))

            # Log Console
            log_bg = pygame.Rect(50, 550, 550, 140)
            pygame.draw.rect(self.screen, (10, 10, 10), log_bg)
            pygame.draw.rect(self.screen, (100, 100, 100), log_bg, 2)

            for i, msg in enumerate(self.messages):
                col = (255, 100, 100) if "ERROR" in msg or "CONFLICT" in msg else (100, 255, 100)
                txt = self.font.render(msg, True, col)
                self.screen.blit(txt, (60, 560 + i * 15))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    app = SchedulerApp()
    app.run()