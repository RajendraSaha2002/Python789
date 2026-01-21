def story_generator():
    print("Welcome to the Personalized Story Generator!")
    name = input("Enter your name: ")
    place = input("Name a place you like: ")
    animal = input("What's your favorite animal? ")
    hobby = input("What's your favorite hobby? ")
    friend = input("Enter a friend's name: ")
    emotion = input("How are you feeling today? ")

    story = f"""
    Once upon a time, {name} went to {place} with their best friend {friend}.
    While exploring, they found a magical {animal} that could talk!
    The {animal} invited them to join in a fun session of {hobby}.
    Everyone laughed and had a wonderful time, feeling very {emotion}.
    It was a day to remember!
    """

    print("\nHere is your personalized story:")
    print(story)

if __name__ == "__main__":
    story_generator()
    