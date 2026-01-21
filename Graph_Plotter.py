import matplotlib.pyplot as plt
import numpy as np

def plot_function(func, x_range, title):
    """Plot a mathematical function over a range."""
    x = np.linspace(x_range[0], x_range[1], 400)
    y = func(x)
    plt.plot(x, y)
    plt.title(title)
    plt.xlabel('x')
    plt.ylabel('y')
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    print("Graph Plotter")
    print("1. Sine")
    print("2. Cosine")
    print("3. Exponential")
    choice = input("Choose a function to plot (1/2/3): ")

    if choice == '1':
        plot_function(np.sin, (-2 * np.pi, 2 * np.pi), "y = sin(x)")
    elif choice == '2':
        plot_function(np.cos, (-2 * np.pi, 2 * np.pi), "y = cos(x)")
    elif choice == '3':
        plot_function(np.exp, (-2, 2), "y = exp(x)")
    else:
        print("Invalid choice.")