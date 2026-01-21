import matplotlib.pyplot as plt

def add_complex(a, b):
    return a + b

def subtract_complex(a, b):
    return a - b

def multiply_complex(a, b):
    return a * b

def divide_complex(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b

def plot_complex_numbers(numbers):
    plt.figure(figsize=(6,6))
    for num in numbers:
        plt.plot(num.real, num.imag, 'o', label=str(num))
    plt.axhline(0, color='grey', linewidth=0.5)
    plt.axvline(0, color='grey', linewidth=0.5)
    plt.xlabel('Real')
    plt.ylabel('Imaginary')
    plt.title('Complex Numbers on the Complex Plane')
    plt.grid(True)
    plt.legend()
    plt.show()

if __name__ == "__main__":
    print("Complex Number Calculator")
    print("Enter complex numbers in the format a+bj (e.g., 2+3j)")
    c1_str = input("Enter first complex number: ")
    c2_str = input("Enter second complex number: ")
    try:
        c1 = complex(c1_str)
        c2 = complex(c2_str)
    except Exception as e:
        print("Error: Please enter valid complex numbers (e.g., 1+2j, -3-4j).")
        print("Exception:", e)  # Line 39: Exception shown here
        exit(1)

    print(f"\nAddition: {c1} + {c2} = {add_complex(c1, c2)}")
    print(f"Subtraction: {c1} - {c2} = {subtract_complex(c1, c2)}")
    print(f"Multiplication: {c1} * {c2} = {multiply_complex(c1, c2)}")
    try:
        print(f"Division: {c1} / {c2} = {divide_complex(c1, c2)}")
    except ValueError as ve:
        print("Division Error:", ve)

    print("\nPlotting both numbers on the complex plane...")
    plot_complex_numbers([c1, c2, add_complex(c1, c2), subtract_complex(c1, c2), multiply_complex(c1, c2)])