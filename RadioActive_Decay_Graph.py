import numpy as np
import matplotlib.pyplot as plt

N0 = 1000    # initial amount
half_life = 5 # half-life in seconds
t = np.linspace(0, 30, 300)
N = N0 * np.exp(-np.log(2) * t / half_life)

plt.plot(t, N)
plt.title('Radioactive Decay')
plt.xlabel('Time (s)')
plt.ylabel('Remaining Nuclei')
plt.grid(True)
plt.show()