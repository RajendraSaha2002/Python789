def name_length_analyzer(names):
    print("Name Length Analysis:")
    for name in names:
        print(f"{name}: {len(name)} characters")
    lengths = [len(name) for name in names]
    print("\nStatistics:")
    print(f"Total names: {len(names)}")
    print(f"Shortest name: {min(names, key=len)} ({min(lengths)} characters)")
    print(f"Longest name: {max(names, key=len)} ({max(lengths)} characters)")
    print(f"Average length: {sum(lengths)/len(lengths):.2f} characters")

if __name__ == "__main__":
    # Example list; you can replace this with input() or file reading
    names = ["Alice", "Bob", "Catherine", "David", "Eve"]
    name_length_analyzer(names)