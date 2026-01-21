import numpy as np
from scipy.integrate import odeint
from scipy.optimize import minimize
import matplotlib.pyplot as plt

# A -> B -> C
def model(y, t, k1, k2):
    A, B, C = y
    dA = -k1 * A
    dB = k1 * A - k2 * B
    dC = k2 * B
    return [dA, dB, dC]

# Synthetic data generation (replace with real data loading)
true_k1, true_k2 = 0.8, 0.3
t_exp = np.linspace(0, 10, 40)
y0 = [1.0, 0.0, 0.0]
Y_true = odeint(model, y0, t_exp, args=(true_k1, true_k2))
noise = np.random.normal(0, 0.02, Y_true.shape)
Y_obs = Y_true + noise

def loss(params):
    k1, k2 = params
    if k1 < 0 or k2 < 0: return 1e6
    Y_pred = odeint(model, y0, t_exp, args=(k1, k2))
    return np.mean((Y_pred - Y_obs)**2)

res = minimize(loss, x0=[0.5, 0.5])
k1_est, k2_est = res.x
print(f"Estimated k1={k1_est:.3f}, k2={k2_est:.3f}")

Y_fit = odeint(model, y0, t_exp, args=(k1_est, k2_est))
plt.plot(t_exp, Y_obs[:,0], 'o', label='A obs')
plt.plot(t_exp, Y_obs[:,1], 'o', label='B obs')
plt.plot(t_exp, Y_obs[:,2], 'o', label='C obs')
plt.plot(t_exp, Y_fit, '-', label='Model fit')
plt.legend()
plt.xlabel("Time")
plt.ylabel("Concentration")
plt.show()