import numpy as np
import matplotlib.pyplot as plt

def f(x): return x**3 - 2*x - 5
def df(x): return 3*x**2 - 2

x_vals = np.linspace(-3, 3, 400)
y_vals = f(x_vals)

x0 = 2.0
iterations = [x0]
for _ in range(5):
    x0 = x0 - f(x0) / df(x0)
    iterations.append(x0)

plt.plot(x_vals, y_vals, label='f(x)')
for i, x_i in enumerate(iterations[:-1]):
    plt.plot([x_i, x_i], [0, f(x_i)], 'r--')
    plt.plot([x_i, iterations[i+1]], [f(x_i), 0], 'g--')
plt.axhline(0, color='black', linewidth=0.5)
plt.title("Newton's Method for Root Finding")
plt.xlabel('x')
plt.ylabel('f(x)')
plt.legend()
plt.grid(True)
plt.show()