def is_prime(n):
    """Check if a number is prime."""
    if n <= 1:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5)+1, 2):
        if n % i == 0:
            return False
    return True

def generate_primes(start, end):
    """Generate a list of prime numbers in a given range."""
    primes = []
    for NUM in range(start, end + 1):
        if is_prime(NUM):
            primes.append(NUM)
    return primes

# Example usage:
if __name__ == "__main__":
    num = int(input("Enter a number to check if it is prime: "))
    if is_prime(num):
        print(f"{num} is a prime number.")
    else:
        print(f"{num} is not a prime number.")

    start_range = int(input("Enter start of range for prime generation: "))
    end_range = int(input("Enter end of range for prime generation: "))
    print(f"Prime numbers between {start_range} and {end_range}:")
    print(generate_primes(start_range, end_range))