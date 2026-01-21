import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 2*np.pi, 100)
y = np.sin(x)
plt.plot(x, y, label='sin(x)')
plt.fill_between(x, 0, y, where=(y>0), color='skyblue', alpha=0.5)
plt.title('Area Under sin(x) Curve')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True)
plt.show()