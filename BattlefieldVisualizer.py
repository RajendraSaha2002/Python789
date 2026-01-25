import pygame
import psycopg2
import math
import sys

# --- CONFIGURATION ---
DB_CONFIG = {
    'dbname': 'glass_battlefield_db',
    'user': 'postgres',
    'password': 'varrie75',  # <--- UPDATE THIS
    'host': 'localhost',
    'port': '5432'
}

# Settings
WIDTH, HEIGHT = 1000, 700
BG_COLOR = (10, 10, 20)
BLUE_COLOR = (50, 200, 255)
RED_COLOR = (255, 50, 50)
JAMMER_COLOR = (255, 0, 0, 50)  # Transparent Red

SNR_THRESHOLD = 2.0  # Minimum ratio to maintain comms


class EWVisualizer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("THE GLASS BATTLEFIELD // EW SIMULATOR")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 14)

        self.units = []
        self.jammers = []

    def fetch_data(self):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()

            # Fetch Units
            cur.execute("SELECT id, callsign, x, y, frequency_mhz, tx_power FROM units")
            self.units = cur.fetchall()

            # Fetch Jammers
            cur.execute("SELECT id, callsign, x, y, target_freq_mhz, jamming_power FROM jammers")
            self.jammers = cur.fetchall()

            conn.close()
        except Exception as e:
            print(f"DB Error: {e}")

    def calculate_snr(self, sender, receiver):
        """Physics engine: Calculates Signal to Noise Ratio."""
        sx, sy, sfreq, spower = sender[2], sender[3], sender[4], sender[5]
        rx, ry = receiver[2], receiver[3]

        # 1. Signal Physics (Inverse Square Law)
        dist = math.sqrt((sx - rx) ** 2 + (sy - ry) ** 2)
        if dist < 1: dist = 1
        signal_strength = spower / (dist ** 2)

        # 2. Noise/Jamming Physics
        noise = 0.0001  # Background thermal noise

        for jammer in self.jammers:
            jx, jy, jfreq, jpower = jammer[2], jammer[3], jammer[4], jammer[5]

            # Jammer only affects if frequency matches
            if jfreq == sfreq:
                j_dist = math.sqrt((jx - rx) ** 2 + (jy - ry) ** 2)
                if j_dist < 1: j_dist = 1

                # Jamming power adds to noise floor
                noise += jpower / (j_dist ** 2)

        return signal_strength / noise

    def draw(self):
        self.screen.fill(BG_COLOR)

        # 1. Draw Jammers (Area of Effect)
        for j in self.jammers:
            jx, jy, freq, pwr = j[2], j[3], j[4], j[5]
            # Visualizing the jamming radius (approximate)
            radius = int(math.sqrt(pwr) * 3)

            # Create a transparent surface for the jammer field
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 0, 0, 40), (radius, radius), radius)
            self.screen.blit(surf, (jx - radius, jy - radius))

            # Draw Core
            pygame.draw.circle(self.screen, RED_COLOR, (jx, jy), 8)
            label = self.font.render(f"JAM: {freq}MHz", True, RED_COLOR)
            self.screen.blit(label, (jx + 10, jy - 10))

        # 2. Draw Comm Links
        # We try to draw lines between all units on the same frequency
        for i, u1 in enumerate(self.units):
            for u2 in self.units[i + 1:]:
                if u1[4] == u2[4]:  # Same Freq
                    snr = self.calculate_snr(u1, u2)

                    start = (u1[2], u1[3])
                    end = (u2[2], u2[3])

                    if snr > SNR_THRESHOLD:
                        # Good Link
                        color = (0, 255, 0)
                        width = 2
                    else:
                        # Jammed Link
                        color = (255, 0, 0)
                        width = 1
                        # Draw broken link symbol
                        mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
                        text = self.font.render("X", True, RED_COLOR)
                        self.screen.blit(text, mid)

                    pygame.draw.line(self.screen, color, start, end, width)

        # 3. Draw Blue Units
        for u in self.units:
            x, y, callsign, freq = u[2], u[3], u[1], u[4]
            pygame.draw.circle(self.screen, BLUE_COLOR, (x, y), 6)
            label = self.font.render(f"{callsign} ({freq}MHz)", True, BLUE_COLOR)
            self.screen.blit(label, (x + 10, y - 10))

        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.fetch_data()
            self.draw()
            self.clock.tick(2)  # Refresh rate (2 FPS is enough for tactical map)


if __name__ == "__main__":
    sim = EWVisualizer()
    sim.run()