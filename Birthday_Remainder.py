import datetime

# Sample birthday data (name: "MM-DD")
birthdays = {
    "Alice": "06-19",
    "Bob": "12-25",
    "Charlie": "03-15"
}

def check_birthdays(birthdays):
    today = datetime.datetime.now().strftime("%m-%d")
    found = False
    for name, bday in birthdays.items():
        if bday == today:
            print(f"🎉 Happy Birthday, {name}! Wishing you a fantastic year ahead! 🎂")
            found = True
    if not found:
        print("No birthdays today.")

def add_birthday(birthdays):
    name = input("Enter the person's name: ")
    date = input("Enter their birthday (MM-DD): ")
    birthdays[name] = date
    print(f"Added {name}'s birthday on {date}.")

if __name__ == "__main__":
    while True:
        print("\nBirthday Reminder Menu:")
        print("1. Check today's birthdays")
        print("2. Add a birthday")
        print("3. Show all birthdays")
        print("4. Exit")
        choice = input("Choose an option: ")
        if choice == "1":
            check_birthdays(birthdays)
        elif choice == "2":
            add_birthday(birthdays)
        elif choice == "3":
            for name, date in birthdays.items():
                print(f"{name}: {date}")
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")