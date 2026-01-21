import math

def factorial(n):
    """Return factorial of n."""
    if n < 0:
        raise ValueError("n must be non-negative.")
    return math.factorial(n)

def combination(n, r):
    """Calculate nCr (combinations)."""
    if n < 0 or r < 0 or r > n:
        raise ValueError("Invalid values: n must be >= r >= 0.")
    return factorial(n) // (factorial(r) * factorial(n - r))

def permutation(n, r):
    """Calculate nPr (permutations)."""
    if n < 0 or r < 0 or r > n:
        raise ValueError("Invalid values: n must be >= r >= 0.")
    return factorial(n) // factorial(n - r)

def simple_probability(favorable, possible):
    """Calculate simple probability."""
    if possible == 0:
        raise ValueError("Total possible outcomes cannot be zero.")
    return favorable / possible

def main():
    print("Probability Calculator")
    print("1. Simple Probability (favorable/possible)")
    print("2. Combinations (nCr)")
    print("3. Permutations (nPr)")
    choice = input("Enter your choice (1-3): ")

    try:
        if choice == '1':
            favorable = int(input("Enter number of favorable outcomes: "))
            possible = int(input("Enter total possible outcomes: "))
            prob = simple_probability(favorable, possible)
            print(f"Probability = {prob:.4f}")
        elif choice == '2':
            n = int(input("Enter n (total items): "))
            r = int(input("Enter r (items chosen): "))
            print(f"Combinations (nCr) = {combination(n, r)}")
        elif choice == '3':
            n = int(input("Enter n (total items): "))
            r = int(input("Enter r (items chosen): "))
            print(f"Permutations (nPr) = {permutation(n, r)}")
        else:
            print("Invalid choice. Please select 1, 2, or 3.")
    except ValueError as e:
        print("Error:", e)
        print("Fix: Please enter valid non-negative integers and ensure n >= r >= 0.")

if __name__ == "__main__":
    main()