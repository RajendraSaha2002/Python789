import pygame
import json
import os

# --- Configuration ---
WIDTH, HEIGHT = 1000, 800
FPS = 60

# Colors
COLOR_BG = (30, 30, 40)
COLOR_PANEL = (50, 50, 60)
COLOR_JET = (100, 100, 120)
COLOR_HP_EMPTY = (150, 150, 150)
COLOR_HP_FULL = (0, 200, 0)
COLOR_HP_ERROR = (200, 0, 0)
COLOR_TEXT = (220, 220, 220)
COLOR_WARNING = (255, 100, 100)

# Weapons Colors
WPN_COLORS = {
    "AAM-Light": (100, 255, 255),  # Cyan
    "AAM-Med": (0, 150, 255),  # Blue
    "AGM": (255, 150, 0),  # Orange
    "Bomb": (255, 50, 50),  # Red
    "Fuel": (150, 150, 150),  # Grey
    "Pod": (200, 0, 255)  # Purple
}


class Hardpoint:
    def __init__(self, data):
        self.id = data['id']
        self.rect = pygame.Rect(data['x'], data['y'], 40, 40)
        self.allowed_types = data['allowed']
        self.limit_kg = data['limit_kg']
        self.desc = data['desc']
        self.weapon = None  # Current weapon object
        self.status_color = COLOR_HP_EMPTY

    def draw(self, surface, font):
        # Draw Slot
        pygame.draw.rect(surface, self.status_color, self.rect, 2)
        pygame.draw.circle(surface, (20, 20, 20), self.rect.center, 5)

        # Label
        lbl = font.render(self.id, True, (150, 150, 150))
        surface.blit(lbl, (self.rect.x, self.rect.y - 15))

        # Attached Weapon
        if self.weapon:
            self.weapon.draw(surface, self.rect.centerx, self.rect.centery)


class WeaponItem:
    def __init__(self, key, data):
        self.key = key
        self.name = data['name']
        self.type = data['type']
        self.weight = data['weight']
        self.role = data['role']  # AA (Air-to-Air), AG (Air-to-Ground), XX (Any)
        self.color = WPN_COLORS.get(self.type, (255, 255, 255))

        # For Armory UI
        self.rect = pygame.Rect(0, 0, 100, 50)
        self.dragging = False

    def draw(self, surface, x, y):
        # Draw a simple shape representing the weapon
        r = pygame.Rect(0, 0, 30, 60)
        r.center = (x, y)
        pygame.draw.rect(surface, self.color, r)
        pygame.draw.rect(surface, (0, 0, 0), r, 1)  # Outline


class ConfiguratorApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("F-16 Loadout Configurator (Crew Chief Mode)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)
        self.font_big = pygame.font.SysFont("Consolas", 20, bold=True)

        self.load_data()

        self.dragged_weapon = None
        self.drag_offset = (0, 0)

        # State
        self.current_mission = "Air-to-Air (CAP)"  # Default
        self.mission_types = ["Air-to-Air (CAP)", "Air-to-Ground (CAS)", "Strike (Deep)"]
        self.message = "System Ready. Select Mission Profile."
        self.message_color = COLOR_TEXT

    def load_data(self):
        try:
            with open("f16_config.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            print("Error: f16_config.json not found.")
            pygame.quit()
            exit()

        self.aircraft_specs = data['aircraft']

        # Create Hardpoints
        self.hardpoints = []
        for hp_data in data['hardpoints']:
            self.hardpoints.append(Hardpoint(hp_data))

        # Create Armory List
        self.armory = []
        x_start = 50
        for key, w_data in data['armory'].items():
            wpn = WeaponItem(key, w_data)
            wpn.rect.topleft = (x_start, 650)
            self.armory.append(wpn)
            x_start += 120

    def draw_jet(self):
        # Simple schematic drawing of an F-16 shape
        cx, cy = 400, 300
        # Fuselage
        pygame.draw.polygon(self.screen, COLOR_JET, [
            (cx, cy - 200), (cx + 30, cy - 50), (cx + 30, cy + 200), (cx - 30, cy + 200), (cx - 30, cy - 50)
        ])
        # Wings
        pygame.draw.polygon(self.screen, COLOR_JET, [
            (cx - 30, cy), (cx - 300, cy + 150), (cx - 300, cy + 200), (cx - 30, cy + 150)
        ])
        pygame.draw.polygon(self.screen, COLOR_JET, [
            (cx + 30, cy), (cx + 300, cy + 150), (cx + 300, cy + 200), (cx + 30, cy + 150)
        ])
        # Stabilizers
        pygame.draw.polygon(self.screen, COLOR_JET, [
            (cx - 30, cy + 180), (cx - 100, cy + 220), (cx - 100, cy + 240), (cx - 30, cy + 220)
        ])
        pygame.draw.polygon(self.screen, COLOR_JET, [
            (cx + 30, cy + 180), (cx + 100, cy + 220), (cx + 100, cy + 240), (cx + 30, cy + 220)
        ])

    def update_weight(self):
        current_load = sum([hp.weapon.weight for hp in self.hardpoints if hp.weapon])
        total_weight = self.aircraft_specs['empty_weight_kg'] + current_load
        max_weight = self.aircraft_specs['max_takeoff_weight_kg']

        return current_load, total_weight, max_weight

    def validate_loadout(self, weapon, hardpoint):
        # 1. Hardware Check (Hardpoint Type)
        if weapon.type not in hardpoint.allowed_types:
            return False, f"Error: {hardpoint.id} cannot mount {weapon.type}."

        # 2. Weight Check (Hardpoint Limit)
        if weapon.weight > hardpoint.limit_kg:
            return False, f"Error: Too Heavy! Limit {hardpoint.limit_kg}kg."

        # 3. Mission Profile Check
        mission_role = "AA" if "Air-to-Air" in self.current_mission else "AG"
        if weapon.role != "XX" and weapon.role != mission_role:
            # Allow some overlap? No, strict rules for training.
            # Example: Can't put Bombs on Air-to-Air mission.
            if mission_role == "AA" and weapon.role == "AG":
                return False, f"Error: Doctrine Violation. No AG weapons on AA mission."

        return True, "Valid"

    def handle_drop(self, mouse_pos):
        dropped_on_hp = False

        for hp in self.hardpoints:
            if hp.rect.collidepoint(mouse_pos):
                dropped_on_hp = True

                # Logic Engine Check
                valid, msg = self.validate_loadout(self.dragged_weapon, hp)

                if valid:
                    hp.weapon = self.dragged_weapon  # Assign (Clone logic simulated)
                    hp.status_color = COLOR_HP_FULL
                    self.message = f"Mounted {self.dragged_weapon.name} on {hp.id}"
                    self.message_color = COLOR_TEXT
                else:
                    self.message = msg
                    self.message_color = COLOR_WARNING
                    hp.status_color = COLOR_HP_ERROR

                break

        if not dropped_on_hp:
            # Check if dropped on armory (delete logic?) or just reset
            pass

    def run(self):
        running = True
        while running:
            mx, my = pygame.mouse.get_pos()

            # --- Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # 1. Check Armory Click
                        for w in self.armory:
                            if w.rect.collidepoint(mx, my):
                                # Start Dragging a COPY
                                import copy
                                self.dragged_weapon = copy.copy(w)
                                self.dragged_weapon.dragging = True
                                break

                        # 2. Check Hardpoint Click (Remove weapon)
                        for hp in self.hardpoints:
                            if hp.rect.collidepoint(mx, my) and hp.weapon:
                                hp.weapon = None
                                hp.status_color = COLOR_HP_EMPTY
                                self.message = f"{hp.id} Cleared."
                                self.message_color = COLOR_TEXT

                        # 3. Check Mission Button
                        btn_rect = pygame.Rect(WIDTH - 250, 20, 230, 40)
                        if btn_rect.collidepoint(mx, my):
                            # Cycle Mission
                            curr_idx = self.mission_types.index(self.current_mission)
                            self.current_mission = self.mission_types[(curr_idx + 1) % len(self.mission_types)]
                            # Reset loadout on mission change? Optionally.
                            self.message = f"Mission Changed: {self.current_mission}"

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.dragged_weapon:
                        self.handle_drop((mx, my))
                        self.dragged_weapon = None

            # --- Logic Updates ---
            load_kg, total_kg, max_kg = self.update_weight()
            weight_ok = total_kg <= max_kg

            # --- Rendering ---
            self.screen.fill(COLOR_BG)

            # Draw Jet
            self.draw_jet()

            # Draw Hardpoints
            for hp in self.hardpoints:
                hp.draw(self.screen, self.font)

            # Draw Armory Panel
            pygame.draw.rect(self.screen, COLOR_PANEL, (0, 600, WIDTH, 200))
            pygame.draw.line(self.screen, (100, 100, 100), (0, 600), (WIDTH, 600), 2)

            for w in self.armory:
                # Draw Box background
                pygame.draw.rect(self.screen, (40, 40, 50), w.rect)
                pygame.draw.rect(self.screen, w.color, (w.rect.x + 5, w.rect.y + 10, 20, 30))

                # Text
                lbl = self.font.render(w.key, True, COLOR_TEXT)
                self.screen.blit(lbl, (w.rect.x + 30, w.rect.y + 5))
                lbl2 = self.font.render(f"{w.weight}kg", True, (150, 150, 150))
                self.screen.blit(lbl2, (w.rect.x + 30, w.rect.y + 25))

            # Draw UI Header
            pygame.draw.rect(self.screen, (20, 20, 25), (0, 0, WIDTH, 80))

            # Mission Selector
            msn_rect = pygame.Rect(WIDTH - 250, 20, 230, 40)
            pygame.draw.rect(self.screen, (50, 50, 100), msn_rect)
            pygame.draw.rect(self.screen, (100, 100, 200), msn_rect, 2)
            msn_txt = self.font_big.render(self.current_mission, True, (255, 255, 255))
            self.screen.blit(msn_txt, (msn_rect.x + 10, msn_rect.y + 10))

            # Status Text
            msg_surf = self.font_big.render(self.message, True, self.message_color)
            self.screen.blit(msg_surf, (20, 20))

            # Weight Meter
            w_col = (0, 255, 0) if weight_ok else (255, 0, 0)
            w_txt = self.font.render(f"Gross Weight: {total_kg} / {max_kg} kg", True, w_col)
            self.screen.blit(w_txt, (20, 50))

            # Draw Dragged Weapon
            if self.dragged_weapon:
                self.dragged_weapon.draw(self.screen, mx, my)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    app = ConfiguratorApp()
    app.run()