# gg.py


def proposal_script():
    """A safe and fun Python script for a proposal idea."""

    # 1. Get user input for the proposal question
    proposal_question = "Will you marry me? (yes or no): "

    try:
        answer = input(proposal_question).strip().lower()  # Get input and clean it

        # 2. Check the answer
        if answer == "yes":
            # Safe and loving response for 'yes'
            print("💖 YES! I LOVE YOU! You've made me the happiest person in the world! 💍")
            print("🥳 Time to celebrate!")

        elif answer == "no":
            # Safe, humorous, non-destructive response for 'no'
            print("💔 Oh no! That's okay, maybe I'll try again another time. ")
            print("But for now, I'm setting this variable to 'broken_heart' instead of deleting system files. 😉")
            # The dangerous part is safely replaced with a harmless variable assignment or message
            "broken_heart"

        else:
            # Response for an unrecognized answer
            print("🤔 I'm not sure what that means, but I'll take it as a 'try again later' and ask the question again.")

    except EOFError:
        # Handles cases where input might be redirected or closed unexpectedly
        print("Input error detected. Exiting script.")

    except Exception as e:
        # General error handling
        print(f"An unexpected error occurred: {e}")


# Run the function when the script is executed
if __name__ == "__main__":
    proposal_script()