import math

def solve_linear(p, q):
    """Solve a linear equation of the form ax + b = 0."""
    if p == 0:
        return "No solution (a cannot be zero for a linear equation)."
    x = -q / p
    return f"The solution to {p}x + {q} = 0 is x = {x}"

def solve_quadratic(p, q, r):
    """Solve a quadratic equation of the form ax^2 + bx + c = 0."""
    if p == 0:
        return solve_linear(q, r)
    discriminant = q ** 2 - 4 * p * r
    if discriminant > 0:
        root1 = (-q + math.sqrt(discriminant)) / (2 * p)
        root2 = (-q - math.sqrt(discriminant)) / (2 * p)
        return f"The solutions to {p}x^2 + {q}x + {r} = 0 are x = {root1} and x = {root2}"
    elif discriminant == 0:
        root = -q / (2 * p)
        return f"The solution to {p}x^2 + {q}x + {r} = 0 is x = {root}"
    else:
        real_part = -q / (2 * p)
        imag_part = math.sqrt(-discriminant) / (2 * p)
        return (f"The solutions to {p}x^2 + {q}x + {r} = 0 are "
                f"x = {real_part} + {imag_part}i and x = {real_part} - {imag_part}i")

# Example usage:
if __name__ == "__main__":
    print("Equation Solver")
    print("1. Solve Linear Equation (ax + b = 0)")
    print("2. Solve Quadratic Equation (ax^2 + bx + c = 0)")
    choice = input("Enter choice (1 or 2): ")
    if choice == '1':
        a = float(input("Enter coefficient a: "))
        b = float(input("Enter coefficient b: "))
        print(solve_linear(a, b))
    elif choice == '2':
        a = float(input("Enter coefficient a: "))
        b = float(input("Enter coefficient b: "))
        c = float(input("Enter coefficient c: "))
        print(solve_quadratic(a, b, c))
    else:
        print("Invalid choice.")