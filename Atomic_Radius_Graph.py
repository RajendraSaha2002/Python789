import matplotlib.pyplot as plt

atomic_numbers = list(range(1, 21))
atomic_radii = [53, 31, 167, 112, 87, 49, 40, 38, 36, 33, 152, 186, 190, 145, 184, 219, 265, 304, 299, 320]  # in pm

plt.plot(atomic_numbers, atomic_radii, marker='o')
plt.title('Atomic Radius vs. Atomic Number (Z=1-20)')
plt.xlabel('Atomic Number')
plt.ylabel('Atomic Radius (pm)')
plt.grid(True)
plt.show()