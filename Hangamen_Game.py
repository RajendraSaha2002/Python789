import random
import time


def choose_word():
    """
    Returns a random word for the game.
    """
    word_list = [
        "python", "programming", "algorithm", "computer", "keyboard",
        "function", "variable", "dictionary", "developer", "learning",
        "coding", "software", "hardware", "database", "internet",
        "network", "security", "application", "interface", "framework"
    ]
    return random.choice(word_list).upper()


def display_hangman(tries):
    """
    Returns the hangman ASCII art based on remaining tries.
    """
    stages = [  # Final state: head, torso, both arms, and both legs
        """
           --------
           |      |
           |      O
           |     \\|/
           |      |
           |     / \\
           -
        """,
        # Head, torso, both arms, and one leg
        """
           --------
           |      |
           |      O
           |     \\|/
           |      |
           |     / 
           -
        """,
        # Head, torso, and both arms
        """
           --------
           |      |
           |      O
           |     \\|/
           |      |
           |      
           -
        """,
        # Head, torso, and one arm
        """
           --------
           |      |
           |      O
           |     \\|
           |      |
           |     
           -
        """,
        # Head and torso
        """
           --------
           |      |
           |      O
           |      |
           |      |
           |     
           -
        """,
        # Head
        """
           --------
           |      |
           |      O
           |    
           |      
           |     
           -
        """,
        # Initial empty state
        """
           --------
           |      |
           |      
           |    
           |      
           |     
           -
        """
    ]
    return stages[tries]


def play_hangman():
    """
    Main function to play the Hangman game.
    """
    print("\n===== WELCOME TO HANGMAN =====")
    print("Try to guess the word! You have 6 tries.")

    word = choose_word()
    word_completion = "_" * len(word)  # Initially, all letters are hidden
    guessed = False
    guessed_letters = []
    guessed_words = []
    tries = 6

    print(display_hangman(tries))
    print(f"Word: {' '.join(word_completion)}")

    while not guessed and tries > 0:
        guess = input("\nPlease guess a letter or word: ").upper()

        # If the guess is a single letter
        if len(guess) == 1 and guess.isalpha():
            if guess in guessed_letters:
                print(f"You already guessed the letter {guess}")
            elif guess not in word:
                print(f"{guess} is not in the word.")
                tries -= 1
                guessed_letters.append(guess)
            else:
                print(f"Good job! {guess} is in the word!")
                guessed_letters.append(guess)

                # Update the word_completion with the guessed letter
                word_as_list = list(word_completion)
                for i, letter in enumerate(word):
                    if letter == guess:
                        word_as_list[i] = guess
                word_completion = "".join(word_as_list)

                # Check if the word is completely guessed
                if "_" not in word_completion:
                    guessed = True

        # If the guess is a word of the correct length
        elif len(guess) == len(word) and guess.isalpha():
            if guess in guessed_words:
                print(f"You already guessed the word {guess}")
            elif guess != word:
                print(f"{guess} is not the word.")
                tries -= 1
                guessed_words.append(guess)
            else:
                guessed = True
                word_completion = word

        # Invalid guess
        else:
            print("Not a valid guess.")

        # Display current state
        print(display_hangman(tries))
        print(f"Word: {' '.join(word_completion)}")
        print(f"Letters guessed: {', '.join(guessed_letters)}")

    # Game conclusion
    if guessed:
        print(f"\nCongratulations! You guessed the word: {word}")
    else:
        print(f"\nSorry, you ran out of tries. The word was: {word}")


def main():
    """
    Main function to run the game with replay option.
    """
    play_hangman()

    while True:
        play_again = input("\nDo you want to play again? (Y/N): ").upper()
        if play_again == 'Y':
            play_hangman()
        else:
            print("Thanks for playing!")
            break


if __name__ == "__main__":
    main()