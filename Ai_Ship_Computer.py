import time
import sys


def animate_text(text, delay=0.03, new_line=True):
    """Prints text character by character for a 'typing' effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    if new_line:
        print()


def get_ai_response(command):
    """Returns a canned response based on the user's command."""
    command = command.lower()

    # Simple keyword matching
    if "hello" in command or "hi" in command:
        return "Greetings, Captain. All systems are online."
    elif "status" in command:
        return "Hull integrity: 100%. Engine core: Stable. Life support: Optimal."
    elif "nav" in command or "where are we" in command:
        return "We are currently in the Alpha Centauri sector, approaching Proxima b."
    elif "engine" in command:
        return "Warp drive is charged and ready, Captain."
    elif "help" in command:
        return "You can ask me about: [status], [nav], [engine]."
    elif "bye" in command or "quit" in command:
        return "Interface closing. Have a productive day, Captain."
    else:
        return f"I do not compute. Unknown command: '{command}'"


def run_ship_computer():
    """Main loop for the AI ship computer interface."""
    animate_text("...Booting A.S.I. (Artificial Ship Intelligence) 'Helios'...", delay=0.05)
    print("=" * 60)
    animate_text("Helios: Interface active. How can I assist you, Captain?")

    while True:
        try:
            # Get user input
            command = input("\nCaptain > ")

            # Get and print the AI's response
            response = get_ai_response(command)
            animate_text(f"Helios: {response}")

            # Check if the user wants to quit
            if "bye" in command.lower() or "quit" in command.lower():
                break

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\nHelios: Emergency shutdown command received. Goodbye, Captain.")
            break


# --- Main execution ---
if __name__ == "__main__":
    run_ship_computer()
