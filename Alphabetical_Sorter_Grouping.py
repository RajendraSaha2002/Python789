from collections import defaultdict

def alphabetical_sort_and_group(words):
    # Sort the words alphabetically
    sorted_words = sorted(words, key=lambda x: x.lower())
    # Group words by their starting letter
    grouped = defaultdict(list)
    for word in sorted_words:
        first_letter = word[0].upper()
        grouped[first_letter].append(word)
    # Display the groups
    for letter in sorted(grouped.keys()):
        print(f"{letter}: {', '.join(grouped[letter])}")

if __name__ == "__main__":
    # Example input
    words = [
        "banana", "Apple", "apricot", "blueberry", "cherry",
        "avocado", "Blackberry", "cranberry", "date", "elderberry"
    ]
    alphabetical_sort_and_group(words)