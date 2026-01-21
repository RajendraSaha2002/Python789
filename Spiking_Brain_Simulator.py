import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QSlider, QPushButton, QGroupBox, QGridLayout)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg


# --- Physics Engine: Hodgkin-Huxley Model ---

class HodgkinHuxleyNeuron:
    def __init__(self):
        # State Variables
        self.V = -65.0  # Membrane Potential (mV)
        self.m = 0.05  # Sodium activation gating variable
        self.h = 0.6  # Sodium inactivation gating variable
        self.n = 0.32  # Potassium activation gating variable

        # Parameters (Standard Squid Giant Axon)
        self.C_m = 1.0  # Membrane Capacitance (uF/cm^2)

        # Max Conductances (mS/cm^2)
        self.g_Na_max = 120.0
        self.g_K_max = 36.0
        self.g_L = 0.3

        # Reversal Potentials (mV)
        self.E_Na = 50.0
        self.E_K = -77.0
        self.E_L = -54.387

        # Simulation Controls
        self.I_inj = 0.0  # Injected Current (uA/cm^2)
        self.dt = 0.05  # Time step (ms)
        self.anesthesia_factor = 1.0  # Multiplier for g_Na (0.0 to 1.0)

    def alpha_n(self, V): return 0.01 * (V + 55) / (1 - np.exp(-(V + 55) / 10)) if V != -55 else 0.1

    def beta_n(self, V):  return 0.125 * np.exp(-(V + 65) / 80)

    def alpha_m(self, V): return 0.1 * (V + 40) / (1 - np.exp(-(V + 40) / 10)) if V != -40 else 1.0

    def beta_m(self, V):  return 4.0 * np.exp(-(V + 65) / 18)

    def alpha_h(self, V): return 0.07 * np.exp(-(V + 65) / 20)

    def beta_h(self, V):  return 1.0 / (1 + np.exp(-(V + 35) / 10))

    def update(self):
        # 1. Calculate Currents
        # Real g_Na is modulated by the "Anesthesia" slider
        g_Na_val = self.g_Na_max * self.anesthesia_factor

        I_Na = g_Na_val * (self.m ** 3) * self.h * (self.V - self.E_Na)
        I_K = self.g_K_max * (self.n ** 4) * (self.V - self.E_K)
        I_L = self.g_L * (self.V - self.E_L)

        # 2. Calculate Derivatives (Hodgkin-Huxley Equations)
        dVdt = (self.I_inj - I_Na - I_K - I_L) / self.C_m

        dndt = self.alpha_n(self.V) * (1 - self.n) - self.beta_n(self.V) * self.n
        dmdt = self.alpha_m(self.V) * (1 - self.m) - self.beta_m(self.V) * self.m
        dhdt = self.alpha_h(self.V) * (1 - self.h) - self.beta_h(self.V) * self.h

        # 3. Euler Integration (Update State)
        self.V += dVdt * self.dt
        self.n += dndt * self.dt
        self.m += dmdt * self.dt
        self.h += dhdt * self.dt

        return self.V, dVdt


# --- GUI Application ---

class NeuralSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Spiking Brain: Hodgkin-Huxley Simulator")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #121212; color: #EEEEEE;")

        self.neuron = HodgkinHuxleyNeuron()

        # Data Buffers for Plotting
        self.history_size = 1000
        self.ptr = 0
        self.time_data = np.linspace(-self.history_size * self.neuron.dt, 0, self.history_size)
        self.voltage_data = np.full(self.history_size, -65.0)
        self.dvdt_data = np.zeros(self.history_size)

        self.setup_ui()

        # Simulation Timer (Runs at 60 FPS approx)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(15)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # --- TOP ROW: Visualizations ---
        plots_layout = QHBoxLayout()

        # 1. Voltage Trace (Time Domain)
        self.plot_voltage = pg.PlotWidget(title="Membrane Potential (V)")
        self.plot_voltage.setLabel('left', "Voltage (mV)")
        self.plot_voltage.setLabel('bottom', "Time (ms)")
        self.plot_voltage.setYRange(-90, 50)
        self.plot_voltage.showGrid(x=True, y=True, alpha=0.3)
        self.curve_voltage = self.plot_voltage.plot(pen=pg.mkPen('c', width=2))

        # Threshold line
        line = pg.InfiniteLine(angle=0, pos=-55, pen=pg.mkPen('r', style=Qt.DashLine))
        self.plot_voltage.addItem(line)

        plots_layout.addWidget(self.plot_voltage, 2)

        # 2. Phase Plane (V vs dV/dt)
        self.plot_phase = pg.PlotWidget(title="Phase Plane Analysis")
        self.plot_phase.setLabel('left', "dV/dt (V/s)")
        self.plot_phase.setLabel('bottom', "Voltage (mV)")
        self.plot_phase.showGrid(x=True, y=True, alpha=0.3)
        self.curve_phase = self.plot_phase.plot(pen=pg.mkPen('m', width=2))

        plots_layout.addWidget(self.plot_phase, 1)

        layout.addLayout(plots_layout, 2)

        # --- BOTTOM ROW: Controls ---
        controls_group = QGroupBox("Experiment Controls")
        controls_layout = QGridLayout()

        # Current Injection Slider
        self.lbl_current = QLabel("Injected Current (I_inj): 0.0 uA")
        self.slider_current = QSlider(Qt.Horizontal)
        self.slider_current.setRange(0, 500)  # 0 to 50.0 uA
        self.slider_current.setValue(0)
        self.slider_current.valueChanged.connect(self.update_params)

        controls_layout.addWidget(self.lbl_current, 0, 0)
        controls_layout.addWidget(self.slider_current, 1, 0)

        # "Anesthesia" Slider (Sodium Block)
        self.lbl_anesthesia = QLabel("Sodium Channel Block (Anesthesia): 0%")
        self.slider_anesthesia = QSlider(Qt.Horizontal)
        self.slider_anesthesia.setRange(0, 100)  # 0 to 100% block
        self.slider_anesthesia.setValue(0)
        self.slider_anesthesia.valueChanged.connect(self.update_params)

        controls_layout.addWidget(self.lbl_anesthesia, 0, 1)
        controls_layout.addWidget(self.slider_anesthesia, 1, 1)

        # "ZAP" Button
        self.btn_zap = QPushButton("⚡ ZAP! (Pulse)")
        self.btn_zap.setStyleSheet("""
            QPushButton { background-color: #D32F2F; color: white; font-weight: bold; font-size: 14px; padding: 15px; border-radius: 5px; }
            QPushButton:pressed { background-color: #B71C1C; }
        """)
        self.btn_zap.pressed.connect(self.zap_start)
        self.btn_zap.released.connect(self.zap_end)

        controls_layout.addWidget(self.btn_zap, 0, 2, 2, 1)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group, 1)

    def update_params(self):
        # Update Current
        val_i = self.slider_current.value() / 10.0
        self.neuron.I_inj = val_i
        self.lbl_current.setText(f"Injected Current (I_inj): {val_i:.1f} uA")

        # Update Anesthesia (100% slider = 0 conductance)
        val_a = self.slider_anesthesia.value()
        factor = 1.0 - (val_a / 100.0)
        self.neuron.anesthesia_factor = factor
        self.lbl_anesthesia.setText(f"Sodium Channel Block (Anesthesia): {val_a}%")

    def zap_start(self):
        # Add massive current
        self.neuron.I_inj += 20.0

    def zap_end(self):
        # Remove massive current (return to slider value)
        self.update_params()

    def update_simulation(self):
        # Perform multiple physics steps per frame for stability/speed
        steps_per_frame = 10

        for _ in range(steps_per_frame):
            v, dv = self.neuron.update()

            # Update buffers
            self.voltage_data[:-1] = self.voltage_data[1:]
            self.voltage_data[-1] = v

            self.dvdt_data[:-1] = self.dvdt_data[1:]
            self.dvdt_data[-1] = dv

        # Update Plots
        self.curve_voltage.setData(self.voltage_data)

        # Phase plane: Plot last N points to trace the cycle
        trace_len = 200
        self.curve_phase.setData(self.voltage_data[-trace_len:], self.dvdt_data[-trace_len:])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NeuralSimulator()
    window.show()
    sys.exit(app.exec_())