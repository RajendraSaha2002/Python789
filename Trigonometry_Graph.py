import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(-2*np.pi, 2*np.pi, 500)
plt.plot(x, np.sin(x), label='sin(x)')
plt.plot(x, np.cos(x), label='cos(x)')
plt.plot(x, np.tan(x), label='tan(x)')
plt.ylim(-2, 2)
plt.title('Trigonometric Functions')
plt.xlabel('x (radians)')
plt.ylabel('y')
plt.legend()
plt.grid(True)
plt.show()