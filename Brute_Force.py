import itertools
import string
import time

# Target password for a local educational simulation
target_password = "ab12"

# Characters to try: lowercase letters and digits
characters = string.ascii_lowercase + string.digits

attempts = 0
start_time = time.time()

print("[+] Starting Brute Force Simulation...")

found = False

# Try passwords from length 1 to 4
for length in range(1, 5):
    for combination in itertools.product(characters, repeat=length):
        guess = "".join(combination)
        attempts += 1

        # Show progress every 10000 attempts
        if attempts % 10000 == 0:
            print(
                f"[-] Attempts: {attempts} | "
                f"Current guess: {guess}"
            )

        # Compare against the known local test password
        if guess == target_password:
            end_time = time.time()

            print("\n[+] Password Found:", guess)
            print("[+] Attempts:", attempts)
            print(
                "[+] Time Taken:",
                round(end_time - start_time, 2),
                "sec"
            )

            found = True
            break

    if found:
        break

if not found:
    print("[-] Password not found in the given length range.")