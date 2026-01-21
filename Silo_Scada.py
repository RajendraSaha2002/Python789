import pygame
import sys
import math

# --- CONFIGURATION ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BG_COLOR = (30, 30, 30)
TEXT_COLOR = (0, 255, 0)
WARNING_COLOR = (255, 165, 0)
ALARM_COLOR = (255, 0, 0)


# --- SYSTEM STATE ---
class SystemState:
    def __init__(self):
        self.temperature = 22.0
        self.main_power = True
        self.generator_on = False
        self.ac1_active = False
        self.ac2_active = False
        self.alarm_active = False
        self.fan_angle = 0

    def update_logic(self):
        # 1. Power Logic
        if not self.main_power:
            self.generator_on = True
        else:
            self.generator_on = False

        # Power available if Main is ON or Generator is ON
        power_available = self.main_power or self.generator_on

        # 2. Temperature Logic (Automated Reaction)
        if power_available:
            if self.temperature > 25.0:
                self.ac1_active = True
            else:
                self.ac1_active = False

            if self.temperature > 30.0:
                self.ac2_active = True
                self.alarm_active = True
            else:
                self.ac2_active = False
                self.alarm_active = False
        else:
            # No power at all (rare case if generator fails)
            self.ac1_active = False
            self.ac2_active = False

        # 3. Simulate Temperature Physics
        # Natural heat buildup
        self.temperature += 0.02

        # Cooling effect
        if self.ac1_active:
            self.temperature -= 0.04
        if self.ac2_active:
            self.temperature -= 0.06  # Stronger cooling


# --- VISUAL COMPONENTS ---
def draw_fan(screen, x, y, size, active, angle):
    """Draws a fan that spins if active."""
    # Draw housing
    pygame.draw.circle(screen, (100, 100, 100), (x, y), size, 4)

    # Calculate blade positions based on angle
    if active:
        color = (0, 255, 255)  # Cyan when spinning
    else:
        color = (50, 50, 50)  # Dark gray when off

    # 3 Blades
    for i in range(3):
        blade_angle = angle + (i * 120)
        rad = math.radians(blade_angle)
        end_x = x + math.cos(rad) * (size - 5)
        end_y = y + math.sin(rad) * (size - 5)
        pygame.draw.line(screen, color, (x, y), (end_x, end_y), 8)


def draw_led(screen, x, y, label, active, color_on=(0, 255, 0)):
    """Draws a status light."""
    color = color_on if active else (50, 0, 0)
    pygame.draw.circle(screen, color, (x, y), 10)

    font = pygame.font.Font(None, 24)
    text = font.render(label, True, (200, 200, 200))
    screen.blit(text, (x + 20, y - 8))


# --- MAIN LOOP ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Silo Environmental Control System (SCADA)")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 48)
    small_font = pygame.font.Font(None, 28)

    state = SystemState()

    while True:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    state.main_power = not state.main_power  # Toggle Power Cut
                elif event.key == pygame.K_UP:
                    state.temperature += 5.0  # Test Heat Spike
                elif event.key == pygame.K_DOWN:
                    state.temperature -= 5.0  # Test Cooling

        # 2. Update Logic
        state.update_logic()

        # Update Fan Animation
        if state.ac1_active: state.fan_angle += 10
        if state.ac2_active: state.fan_angle += 20  # Spins faster

        # 3. Drawing
        screen.fill(BG_COLOR)

        # -- UI Header --
        header_text = font.render("MISSILE SILO COOLING", True, (200, 200, 200))
        screen.blit(header_text, (20, 20))

        controls_text = small_font.render("[SPACE] Toggle Power | [UP/DOWN] Adjust Temp", True, (100, 100, 100))
        screen.blit(controls_text, (20, 70))

        # -- Temperature Display --
        temp_color = TEXT_COLOR
        if state.temperature > 25: temp_color = WARNING_COLOR
        if state.temperature > 30: temp_color = ALARM_COLOR

        temp_text = font.render(f"TEMP: {state.temperature:.1f}°C", True, temp_color)
        screen.blit(temp_text, (SCREEN_WIDTH // 2 - 100, 150))

        # -- Alarm Visual --
        if state.alarm_active:
            if (pygame.time.get_ticks() // 500) % 2 == 0:  # Blink effect
                pygame.draw.rect(screen, ALARM_COLOR, (0, 0, SCREEN_WIDTH, 10))
                pygame.draw.rect(screen, ALARM_COLOR, (0, SCREEN_HEIGHT - 10, SCREEN_WIDTH, 10))
                alert_text = font.render("!!! CRITICAL TEMP ALERT !!!", True, ALARM_COLOR)
                screen.blit(alert_text, (SCREEN_WIDTH // 2 - 220, 100))

        # -- Fans (AC Units) --
        # AC 1
        draw_fan(screen, 200, 350, 60, state.ac1_active, state.fan_angle)
        ac1_label = small_font.render("AC COMPRESSOR 1", True, (0, 255, 255) if state.ac1_active else (100, 100, 100))
        screen.blit(ac1_label, (110, 430))

        # AC 2
        draw_fan(screen, 600, 350, 60, state.ac2_active, state.fan_angle)
        ac2_label = small_font.render("AC COMPRESSOR 2", True, (0, 255, 255) if state.ac2_active else (100, 100, 100))
        screen.blit(ac2_label, (510, 430))

        # -- Power Status Panel --
        panel_x = 20
        panel_y = 500
        pygame.draw.rect(screen, (20, 20, 20), (panel_x, panel_y, 760, 80))
        pygame.draw.rect(screen, (100, 100, 100), (panel_x, panel_y, 760, 80), 2)

        draw_led(screen, panel_x + 30, panel_y + 30, "MAIN POWER GRID", state.main_power, (0, 255, 0))

        # Generator is RED if off, YELLOW if running (Emergency Power)
        gen_color = (255, 255, 0) if state.generator_on else (50, 0, 0)
        draw_led(screen, panel_x + 300, panel_y + 30, "DIESEL GENERATOR", state.generator_on, (255, 255, 0))

        # Logic status
        if not state.main_power and not state.generator_on:
            pwr_text = "SYSTEM BLACKOUT"
            pwr_color = (255, 0, 0)
        elif not state.main_power and state.generator_on:
            pwr_text = "EMERGENCY POWER ACTIVE"
            pwr_color = (255, 165, 0)
        else:
            pwr_text = "GRID ONLINE"
            pwr_color = (0, 255, 0)

        screen.blit(small_font.render(pwr_text, True, pwr_color), (panel_x + 550, panel_y + 25))

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()