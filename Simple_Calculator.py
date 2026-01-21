# calculator.py

def add(x, y): return x + y
def sub(x, y): return x - y
def mul(x, y): return x * y
def div(x, y): return x / y

print("Select operation: + - * /")
choice = input("Enter choice: ")

a = float(input("Enter first number: "))
b = float(input("Enter second number: "))

if choice == '+':
    print("Result:", add(a, b))
elif choice == '-':
    print("Result:", sub(a, b))
elif choice == '*':
    print("Result:", mul(a, b))
elif choice == '/':
    print("Result:", div(a, b))
else:
    print("Invalid operation")
