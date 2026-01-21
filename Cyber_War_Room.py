import pygame
import random
import math
import time
import numpy as np
from datetime import datetime

# --- Configuration ---
WIDTH, HEIGHT = 1400, 900
FPS = 60

# Colors (Cyberpunk / War Games Palette)
COLOR_BG = (10, 10, 15)
COLOR_GRID = (0, 40, 40)
COLOR_LAND = (20, 20, 30)
COLOR_TEXT_MAIN = (0, 255, 255)
COLOR_TEXT_DIM = (0, 100, 100)
COLOR_PANEL_BG = (0, 0, 0, 200)  # Semi-transparent
COLOR_BORDER_NORMAL = (0, 50, 50)
COLOR_BORDER_ALERT = (255, 0, 0)

# Attack Types & Colors
ATTACK_TYPES = {
    "DDoS": (255, 255, 0),  # Yellow
    "Malware": (255, 0, 0),  # Red
    "Phishing": (0, 150, 255),  # Blue
    "Brute Force": (255, 100, 0),  # Orange
    "Espionage": (200, 0, 255)  # Purple
}

# --- 1. Geolocation Database (Simulated) ---
# Approximate Lat/Lon centers for major cyber players
LOCATIONS = {
    "USA": (37.09, -95.71),
    "China": (35.86, 104.19),
    "Russia": (61.52, 105.31),
    "Germany": (51.16, 10.45),
    "Brazil": (-14.23, -51.92),
    "India": (20.59, 78.96),
    "UK": (55.37, -3.43),
    "Australia": (-25.27, 133.77),
    "Japan": (36.20, 138.25),
    "North Korea": (40.33, 127.51),
    "Iran": (32.42, 53.68),
    "Israel": (31.04, 34.85),
    "France": (46.22, 2.21),
    "Ukraine": (48.37, 31.16)
}


# --- 2. Math & Physics Engine ---

class GeoMath:
    @staticmethod
    def latlon_to_screen(lat, lon, screen_w, screen_h):
        """Simple Equirectangular projection to map coordinates."""
        # Normalize lon from -180/180 to 0/Width
        x = (lon + 180) * (screen_w / 360)
        # Normalize lat from -90/90 to Height/0 (Screen Y is inverted)
        y = (90 - lat) * (screen_h / 180)
        return int(x), int(y)

    @staticmethod
    def bezier_point(t, p0, p1, p2):
        """Quadratic Bezier curve point at t (0.0 to 1.0)."""
        # B(t) = (1-t)^2 P0 + 2(1-t)t P1 + t^2 P2
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        return int(x), int(y)


# --- 3. Entities ---

class AttackEvent:
    def __init__(self, src_country, dst_country, attack_type):
        self.src_name = src_country
        self.dst_name = dst_country
        self.type = attack_type
        self.color = ATTACK_TYPES[attack_type]

        # Coordinates
        slat, slon = LOCATIONS[src_country]
        dlat, dlon = LOCATIONS[dst_country]

        # Apply slight jitter so lines don't perfectly overlap
        slat += random.uniform(-2, 2)
        dlat += random.uniform(-2, 2)

        self.p0 = GeoMath.latlon_to_screen(slat, slon, WIDTH, HEIGHT)
        self.p2 = GeoMath.latlon_to_screen(dlat, dlon, WIDTH, HEIGHT)

        # Calculate Control Point (p1) for the Curve (The Arc)
        # We want the arc to bend towards the "top" of the screen (North)
        # or center, depending on distance.
        mid_x = (self.p0[0] + self.p2[0]) / 2
        mid_y = (self.p0[1] + self.p2[1]) / 2
        dist = math.hypot(self.p2[0] - self.p0[0], self.p2[1] - self.p0[1])

        # Curve height proportional to distance
        curve_height = dist * 0.5
        self.p1 = (mid_x, mid_y - curve_height)

        # Animation State
        self.progress = 0.0
        self.speed = random.uniform(0.005, 0.015)  # Speed of packet
        self.active = True
        self.history = []  # For drawing the trail

    def update(self):
        self.progress += self.speed
        if self.progress >= 1.0:
            self.active = False
            return "IMPACT"

        # Calculate current position
        current_pos = GeoMath.bezier_point(self.progress, self.p0, self.p1, self.p2)
        self.history.append(current_pos)

        # Limit trail length
        if len(self.history) > 20:
            self.history.pop(0)

        return "FLYING"

    def draw(self, surface):
        if len(self.history) < 2: return

        # Draw Trail (Fading)
        if len(self.history) > 2:
            pygame.draw.lines(surface, self.color, False, self.history, 2)

        # Draw Head (The Packet)
        head_pos = self.history[-1]
        pygame.draw.circle(surface, (255, 255, 255), head_pos, 3)

        # Draw "Glow" around head
        s = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, 100), (10, 10), 8)
        surface.blit(s, (head_pos[0] - 10, head_pos[1] - 10))


class CountryNode:
    def __init__(self, name, lat, lon):
        self.name = name
        self.pos = GeoMath.latlon_to_screen(lat, lon, WIDTH, HEIGHT)
        self.hits_taken = 0
        self.attacks_launched = 0
        self.flash_timer = 0  # Visual hit indicator

    def register_hit(self):
        self.hits_taken += 1
        self.flash_timer = 20  # Flash for 20 frames

    def draw(self, surface, font):
        # Base Dot
        col = COLOR_TEXT_DIM
        radius = 3

        # Flash effect
        if self.flash_timer > 0:
            col = (255, 0, 0)
            radius = 6 + (self.flash_timer / 4)  # Pulse out
            self.flash_timer -= 1

            # Draw impact rings
            pygame.draw.circle(surface, (255, 0, 0), self.pos, int(radius * 2), 1)

        pygame.draw.circle(surface, col, self.pos, int(radius))

        # Draw Name label only if busy
        if self.hits_taken > 5 or self.flash_timer > 0:
            lbl = font.render(self.name[:3], True, col)
            surface.blit(lbl, (self.pos[0] + 8, self.pos[1] - 8))


# --- 4. Main Application ---

class WarRoomDisplay:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("GLOBAL CYBER THREAT MAP // DEFCON MONITOR")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)
        self.font_big = pygame.font.SysFont("Consolas", 24, bold=True)
        self.font_huge = pygame.font.SysFont("Impact", 60)

        # Logic State
        self.attacks = []
        self.nodes = {name: CountryNode(name, lat, lon) for name, (lat, lon) in LOCATIONS.items()}

        # Stats
        self.total_attacks = 0
        self.active_threats = 0
        self.defcon = 5
        self.log = []  # Recent events text

        # Alarm State
        self.alarm_active = False
        self.alarm_flash_state = False
        self.alarm_timer = 0

    def generate_threat(self):
        # Weighted random generation to simulate geopolitics
        src = random.choice(list(LOCATIONS.keys()))
        dst = random.choice(list(LOCATIONS.keys()))

        # Don't attack self
        while src == dst:
            dst = random.choice(list(LOCATIONS.keys()))

        atype = random.choice(list(ATTACK_TYPES.keys()))

        # Create Attack Object
        attack = AttackEvent(src, dst, atype)
        self.attacks.append(attack)

        # Update Stats
        self.nodes[src].attacks_launched += 1
        self.total_attacks += 1

        # Log
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(0, f"[{ts}] {src} -> {dst} : {atype.upper()}")
        if len(self.log) > 15: self.log.pop()

    def update_defcon(self):
        # DEFCON Logic based on Active Threats count
        count = len(self.attacks)
        self.active_threats = count

        if count > 100:
            self.defcon = 1
        elif count > 70:
            self.defcon = 2
        elif count > 40:
            self.defcon = 3
        elif count > 20:
            self.defcon = 4
        else:
            self.defcon = 5

        self.alarm_active = (self.defcon <= 2)

    def draw_map_grid(self):
        # Draw simple lat/lon grid lines for "Digital World" look
        self.screen.fill(COLOR_BG)
        for x in range(0, WIDTH, 50):
            color = COLOR_GRID
            # Draw Equator/Meridian brighter
            if abs(x - WIDTH / 2) < 25: color = (0, 80, 80)
            pygame.draw.line(self.screen, color, (x, 0), (x, HEIGHT), 1)

        for y in range(0, HEIGHT, 50):
            color = COLOR_GRID
            if abs(y - HEIGHT / 2) < 25: color = (0, 80, 80)
            pygame.draw.line(self.screen, color, (0, y), (WIDTH, y), 1)

    def draw_hud(self):
        # --- Left Panel: Statistics ---
        panel_rect = pygame.Rect(20, 20, 300, HEIGHT - 40)
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill(COLOR_PANEL_BG)
        self.screen.blit(s, panel_rect)
        pygame.draw.rect(self.screen, COLOR_BORDER_NORMAL, panel_rect, 2)

        # Header
        y_offset = 40
        title = self.font_big.render("CYBER COMMAND", True, COLOR_TEXT_MAIN)
        self.screen.blit(title, (40, y_offset))
        y_offset += 40

        # Global Counters
        stats = [
            f"TOTAL EVENTS: {self.total_attacks}",
            f"ACTIVE THREATS: {self.active_threats}",
            f"SERVERS DOWN: {int(self.total_attacks * 0.12)}"
        ]
        for line in stats:
            t = self.font.render(line, True, (200, 200, 200))
            self.screen.blit(t, (40, y_offset))
            y_offset += 25

        y_offset += 20
        # Threat Log
        self.screen.blit(self.font_big.render("LIVE FEED", True, COLOR_TEXT_MAIN), (40, y_offset))
        y_offset += 30
        for msg in self.log:
            # Color code based on type in text
            col = (150, 150, 150)
            if "MALWARE" in msg:
                col = ATTACK_TYPES["Malware"]
            elif "DDOS" in msg:
                col = ATTACK_TYPES["DDoS"]

            t = self.font.render(msg, True, col)
            self.screen.blit(t, (40, y_offset))
            y_offset += 20

        # --- Top Right: DEFCON ---
        defcon_colors = {
            1: (255, 0, 0), 2: (255, 100, 0), 3: (255, 255, 0),
            4: (0, 255, 0), 5: (0, 100, 255)
        }
        dc_col = defcon_colors[self.defcon]

        dc_text = self.font_huge.render(f"DEFCON {self.defcon}", True, dc_col)
        self.screen.blit(dc_text, (WIDTH - 300, 30))

        # Legend
        lx = WIDTH - 200
        ly = HEIGHT - 200
        for k, v in ATTACK_TYPES.items():
            pygame.draw.rect(self.screen, v, (lx, ly, 10, 10))
            t = self.font.render(k, True, (200, 200, 200))
            self.screen.blit(t, (lx + 20, ly - 2))
            ly += 20

        # --- ALARM OVERLAY ---
        if self.alarm_active:
            self.alarm_timer += 1
            if self.alarm_timer % 30 < 15:  # Flash every 0.5s
                # Red Border
                pygame.draw.rect(self.screen, (255, 0, 0), (0, 0, WIDTH, HEIGHT), 20)
                # Alert Text
                alrt = self.font_huge.render("CRITICAL NETWORK LOAD", True, (255, 0, 0))
                rect = alrt.get_rect(center=(WIDTH // 2, 100))
                self.screen.blit(alrt, rect)

    def run(self):
        running = True
        spawn_rate = 0.95  # Probability threshold (starts slow)

        while running:
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Surge Simulation
                        spawn_rate = 0.5  # Much faster spawning

            # 1. Spawn Logic
            # Slowly increase traffic over time naturally, or burst
            if random.random() > spawn_rate:
                self.generate_threat()

            # 2. Update Logic
            for attack in self.attacks[:]:
                res = attack.update()
                if res == "IMPACT":
                    self.nodes[attack.dst_name].register_hit()
                    self.attacks.remove(attack)

            self.update_defcon()

            # 3. Draw
            self.draw_map_grid()

            # Draw Connections (Arcs)
            for attack in self.attacks:
                attack.draw(self.screen)

            # Draw Nodes (Countries)
            for node in self.nodes.values():
                node.draw(self.screen, self.font)

            self.draw_hud()

            pygame.display.flip()
            self.clock.tick(FPS)

            # Dynamic Difficulty
            # If user holds SPACE, spawn_rate stays low (surge).
            # Otherwise, drift back to normal to prevent infinite clog
            if spawn_rate < 0.90:
                spawn_rate += 0.001

        pygame.quit()


if __name__ == "__main__":
    app = WarRoomDisplay()
    app.run()