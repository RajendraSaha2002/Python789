import datetime
import time


def run_time_machine():
    """
    A fun text-based time machine simulator that calculates a
    new date and time based on user input.
    """

    print("=" * 40)
    print("  Welcome to the Python Time Machine!  ")
    print("=" * 40)
    print("\nInitializing flux capacitor...")
    time.sleep(1)  # A brief pause for dramatic effect
    print("Powering up temporal displacement circuits...")
    time.sleep(1)
    print("\nTime circuits... ON.")

    # Get the current time
    current_time = datetime.datetime.now()
    print(f"\nCurrent Date and Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        # Ask for destination: past or future
        direction = input("\nDo you want to travel to the (past) or (future)? ").strip().lower()
        if direction not in ['past', 'future']:
            print("Invalid direction. Please type 'past' or 'future'.")
            continue

        # Get the amount of time to travel
        try:
            print("\nEnter your travel vector (how far to travel):")
            years = int(input("  - Years: "))
            days = int(input("  - Days:  "))
            hours = int(input("  - Hours: "))

            # Create a timedelta object
            # Note: timedelta doesn't have a 'years' argument,
            # so we'll approximate it or add days manually.
            # A simpler way is to just use days and hours.
            # For simplicity, we'll calculate total days.
            total_days_to_travel = (years * 365) + days

            time_delta = datetime.timedelta(days=total_days_to_travel, hours=hours)

            # Calculate the destination time
            if direction == 'past':
                destination_time = current_time - time_delta
                print(f"\n...Traveling BACK {years} years, {days} days, and {hours} hours...")
            else:  # direction == 'future'
                destination_time = current_time + time_delta
                print(f"\n...Traveling FORWARD {years} years, {days} days, and {hours} hours...")

            # Simulate the travel time
            time.sleep(2)
            print("\n...BZZT... ZAP... WHOOSH!...")
            time.sleep(1)

            # Announce arrival
            print("\n" + "=" * 40)
            print("         A R R I V A L         ")
            print("=" * 40)
            print(f"\nYou have arrived at:")
            print(f"{destination_time.strftime('%A, %B %d, %Y at %I:%M %p')}")

            break  # Exit the loop after successful travel

        except ValueError:
            print("\nInvalid input. Please enter whole numbers for time.")
        except OverflowError:
            print("\nThat's too far to travel! The time circuits are overloaded. Try a smaller number.")


# --- Main execution ---
if __name__ == "__main__":
    run_time_machine()
