def factorial(n):
    """Calculate the factorial of a number n (n!)."""
    if n < 0:
        return "Factorial not defined for negative numbers."
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n+1):
        result *= i
    return result

def fibonacci(n):
    """Generate Fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    sequence = [0]
    if n == 1:
        return sequence
    sequence.append(1)
    for i in range(2, n):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

# Example usage:
if __name__ == "__main__":
    num = int(input("Enter a number for factorial calculation: "))
    print(f"Factorial of {num} is: {factorial(num)}")

    terms = int(input("Enter number of terms for Fibonacci sequence: "))
    print(f"Fibonacci sequence up to {terms} terms: {fibonacci(terms)}")