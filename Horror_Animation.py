import time
import random
import sys


def animate_text(text, delay=0.05, new_line=True):
    """Prints text character by character for a 'typing' effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    if new_line:
        print()


def clear_screen():
    """Clears the console screen."""
    # For Windows
    if sys.platform.startswith('win'):
        import os
        os.system('cls')
    # For macOS and Linux
    else:
        import os
        os.system('clear')


def generate_horror_animation():
    """Generates a text-based horror animation scene."""

    clear_screen()
    print("=" * 60)
    animate_text("  Initializing Nightmare Protocol...", delay=0.08)
    print("=" * 60)
    time.sleep(1.5)

    clear_screen()
    animate_text("... You awaken in a cold sweat. The digital clock flickers.", delay=0.06)
    time.sleep(1)

    # Scene 1: The Room
    clear_screen()
    print("\n")
    animate_text("Your eyes adjust to the oppressive darkness of your room.", delay=0.06)
    print("     ______")
    print("    |      |")
    print("    | [ ]  |  <- Your Bed")
    print("    |______|")
    print("    |      |")
    print("____|______|____")
    animate_text("The silence is... unnatural.", delay=0.08)
    time.sleep(2)

    # Scene 2: The Sound
    clear_screen()
    animate_text("A faint SCRAPE echoes from the hallway.", delay=0.07)
    time.sleep(1)
    animate_text("You hold your breath. It sounds like fingernails on wood.", delay=0.07)
    print("          _")
    print("       _ / \\ _")
    print("     |_________|  <- Doorway")
    print("       |  _  |")
    print("       | | | |")
    print("       |_|_|_|")
    time.sleep(2)

    # Scene 3: The Shadow (or lack thereof)
    clear_screen()
    animate_text("A shadow... no, a lack of shadow, seems to deepen at the edge of the door.", delay=0.07)
    time.sleep(1.5)

    # Introduce a 'creature' or 'presence'
    clear_screen()
    entity_name = random.choice(["The Watcher", "The Silent One", "The Grinner", "It"])
    animate_text(
        f"Then, a pair of {random.choice(['pinprick red', 'pale white', 'bottomless black'])} eyes emerge from the gloom.",
        delay=0.08)
    time.sleep(1.5)

    # ASCII art for eyes
    clear_screen()
    print("\n\n\n")
    print("        .   .   ")
    print("       (o) (o) ")  # Simple eyes
    print("\n\n\n")
    animate_text(f"They stare. Unblinking. {entity_name} is here.", delay=0.1)
    time.sleep(2)

    # Final jump scare / realization
    clear_screen()
    animate_text("You try to scream, but no sound escapes your throat.", delay=0.08)
    time.sleep(1)
    animate_text("The bedroom door slowly, agonizingly, begins to creak open...", delay=0.1)

    # Animated door opening
    for i in range(5):
        clear_screen()
        door_open_level = " " * (i * 2) + " "
        print(f"      _______")
        print(f"     |       |")
        print(f"     |   {door_open_level}\\_")  # Opening door effect
        print(f"     |_______|")
        print("\n" * 3)
        time.sleep(0.5)

    clear_screen()
    print("\n\n\n")
    print("        _ _ _ _")
    print("       |_|_|_|_| ")  # Fully open with something inside
    print("       |       |")
    print("       |_______|")
    print("\n\n\n")
    animate_text(f"\n...And then, you realize:", delay=0.1)
    time.sleep(1)
    animate_text("YOU ARE THE MONSTER.", delay=0.2, new_line=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
    time.sleep(2)  # Hold the final line

    clear_screen()
    print("=" * 60)
    animate_text("  E N D   O F   N I G H T M A R E  ", delay=0.08)
    print("=" * 60)
    time.sleep(1)
    print("\n...Until next time.\n")


# --- Main execution ---
if __name__ == "__main__":
    generate_horror_animation()
