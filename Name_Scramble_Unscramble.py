import random

def scramble_name(name):
    name_list = list(name)
    random.shuffle(name_list)
    return ''.join(name_list)

def unscramble_name(scrambled, original):
    # For demonstration, just compare with the original
    return scrambled == ''.join(sorted(original)) and scrambled == ''.join(sorted(scrambled))

if __name__ == "__main__":
    name = input("Enter a name to scramble: ")
    scrambled = scramble_name(name)
    print(f"Scrambled name: {scrambled}")

    guess = input("Try to unscramble the name: ")
    if sorted(guess) == sorted(name):
        print("Correct! You unscrambled the name.")
    else:
        print(f"Sorry, that's not correct. The original name was: {name}")