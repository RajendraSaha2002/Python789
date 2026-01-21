import sympy as sp

def differentiate(expr_str, var_str):
    """Symbolically differentiate an expression with respect to a variable."""
    var = sp.symbols(var_str)
    expr = sp.sympify(expr_str)
    derivative = sp.diff(expr, var)
    return derivative

def integrate(expr_str, var_str):
    """Symbolically integrate an expression with respect to a variable."""
    var = sp.symbols(var_str)
    expr = sp.sympify(expr_str)
    integral = sp.integrate(expr, var)
    return integral

def main():
    print("Differentiation & Integration Calculator")
    print("1. Differentiate an expression")
    print("2. Integrate an expression")
    choice = input("Enter your choice (1-2): ")

    expr_str = input("Enter the expression (e.g., x**2 + 3*x + 1): ")
    var_str = input("Enter the variable (e.g., x): ")

    try:
        if choice == '1':
            result = differentiate(expr_str, var_str)
            print(f"Derivative of {expr_str} with respect to {var_str}: {result}")
        elif choice == '2':
            result = integrate(expr_str, var_str)
            print(f"Indefinite integral of {expr_str} with respect to {var_str}: {result} + C")
        else:
            print("Invalid choice. Please select 1 or 2.")
    except Exception as e:
        print("Error:", e)
        print("Fix: Make sure your expression and variable are valid (e.g., x**2, x).")

if __name__ == "__main__":
    main()