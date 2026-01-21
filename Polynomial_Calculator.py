import numpy as np

def add_polynomials(r1, q2):
    """Add two polynomials."""
    return np.polyadd(r1, q2)

def subtract_polynomials(a1, b2):
    """Subtract two polynomials."""
    return np.polysub(a1, b2)

def multiply_polynomials(x1, y2):
    """Multiply two polynomials."""
    return np.polymul(x1, y2)

def find_roots(p):
    """Find roots of a polynomial."""
    return np.roots(p)

def print_polynomial(p):
    """Pretty-print a polynomial."""
    poly = np.poly1d(p)
    print(poly)

if __name__ == "__main__":
    # Example polynomials
    # p(x) = x^2 + 2x + 1
    # q(x) = x + 1
    p1 = [1, 2, 1]
    p2 = [1, 1]

    print("Polynomial p(x):")
    print_polynomial(p1)
    print("Polynomial q(x):")
    print_polynomial(p2)

    print("\nAddition:")
    print_polynomial(add_polynomials(p1, p2))
    print("\nSubtraction:")
    print_polynomial(subtract_polynomials(p1, p2))
    print("\nMultiplication:")
    print_polynomial(multiply_polynomials(p1, p2))
    print("\nRoots of p(x):")
    print(find_roots(p1))