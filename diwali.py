import pygame
import sys
import time

# Initialize pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Diwali Wishes & Cyber Safety")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 223, 0)
CYBER_BLUE = (0, 176, 240)

# Fonts
font_big = pygame.font.Font(pygame.font.get_default_font(), 36)
font_small = pygame.font.Font(pygame.font.get_default_font(), 24)

# Messages
messages = [
    "✨ Wishing You a Bright and Joyous Diwali! ✨",
    "🌟 May Your Life Be Filled with Light and Happiness! 🌟",
    "🎆 Let's Celebrate Safely in the Real and Cyber World! 🎆",
    "🔒 Stay Safe Online: Use Strong Passwords and 2FA 🔐",
    "🎇 Avoid Clicking on Suspicious Links - Think Before You Click! 🎇",
    "🪔 Spread Love, Light, and Cyber Awareness This Diwali! 🪔"
]

# Helper function to display text
def display_text(text, y_offset, color):
    text_surface = font_big.render(text, True, color)
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + y_offset))
    screen.blit(text_surface, text_rect)

# Main function
def main():
    clock = pygame.time.Clock()
    running = True
    message_index = 0
    animation_counter = 0

    while running:
        screen.fill(BLACK)

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Display current message
        if message_index < len(messages):
            color = YELLOW if animation_counter % 20 < 10 else CYBER_BLUE
            display_text(messages[message_index], 0, color)
            animation_counter += 1

            # Change message every 3 seconds
            if animation_counter > 60:
                animation_counter = 0
                message_index += 1
        else:
            # End of animation
            display_text("🎉 Happy Diwali & Stay Cyber Safe! 🎉", 0, WHITE)

        # Update the display
        pygame.display.flip()
        clock.tick(20)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()