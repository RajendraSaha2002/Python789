import sys
import numpy as np
from scipy.optimize import brentq
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QComboBox,
                             QFrame, QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPalette, QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


# --- Chemistry Engine ---

class Acid:
    def __init__(self, name, pkas, concentration, volume_ml):
        self.name = name
        self.pkas = np.array(pkas)
        self.kas = 10 ** (-self.pkas)
        self.ca_init = concentration  # Molar
        self.va_init = volume_ml  # mL

    def alpha_values(self, h_conc):
        """Calculates fractional composition of acid species at given [H+]."""
        # Denominator D = [H+]^n + K1[H+]^(n-1) + K1K2[H+]^(n-2) ...
        # For a triprotic acid H3A:
        # D = h^3 + k1*h^2 + k1*k2*h + k1*k2*k3

        h = h_conc
        n = len(self.kas)

        # Terms for the denominator
        terms = [h ** n]
        current_k_product = 1.0
        for i, k in enumerate(self.kas):
            current_k_product *= k
            power_of_h = n - (i + 1)
            terms.append(current_k_product * (h ** power_of_h))

        D = sum(terms)

        # Alphas: alpha_j is the fraction of species losing j protons
        # alpha_0 = [H3A]/C = h^3 / D
        # alpha_1 = [H2A-]/C = k1*h^2 / D
        # ...
        alphas = []
        current_k_product = 1.0
        for i in range(n + 1):
            power_of_h = n - i
            numerator = current_k_product * (h ** power_of_h)
            alphas.append(numerator / D)
            if i < n:
                current_k_product *= self.kas[i]

        return np.array(alphas)

    def charge_contribution(self, h_conc, total_conc):
        """Returns the total negative charge concentration from the acid anions."""
        alphas = self.alpha_values(h_conc)
        charge = 0
        # Species 0 (H3A) has charge 0
        # Species 1 (H2A-) has charge -1
        # Species 2 (HA2-) has charge -2
        # etc.
        for i, alpha in enumerate(alphas):
            charge += alpha * (-i)
        return charge * total_conc


class TitrationSimulation:
    def __init__(self):
        # Base: NaOH (Strong Base)
        self.cb = 0.1  # Molar Concentration of Base

        # Acids Database
        self.acids = {
            "HCl (Strong)": Acid("Hydrochloric Acid", [-7], 0.1, 25.0),  # pKa -7 effectively strong
            "Acetic Acid (Weak)": Acid("Acetic Acid", [4.76], 0.1, 25.0),
            "Phosphoric Acid (Polyprotic)": Acid("Phosphoric Acid", [2.15, 7.20, 12.35], 0.1, 25.0)
        }
        self.current_acid = self.acids["Acetic Acid (Weak)"]
        self.vb_added = 0.0  # mL

    def solve_ph(self):
        """Solves the Charge Balance Equation to find pH."""
        kw = 1.0e-14

        # Dilution factors
        total_vol = self.current_acid.va_init + self.vb_added
        ca_curr = self.current_acid.ca_init * self.current_acid.va_init / total_vol
        cb_curr = self.cb * self.vb_added / total_vol

        # Sodium concentration [Na+] comes from NaOH
        na_conc = cb_curr

        # Charge Balance Error Function: sum of charges = 0
        # [H+] - [OH-] + [Na+] + [Anions] = 0
        def charge_balance(ph):
            h = 10 ** (-ph)
            oh = kw / h
            acid_charge = self.current_acid.charge_contribution(h, ca_curr)
            return h - oh + na_conc + acid_charge

        # Find root (pH) between 0 and 14
        try:
            # brentq is a robust root finding algorithm
            ph_solution = brentq(charge_balance, 0.0, 14.0)
        except ValueError:
            ph_solution = 7.0  # Fallback

        return ph_solution


# --- GUI Components ---

class BeakerWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedSize(150, 200)
        self.setStyleSheet("background-color: white; border: 2px solid #555; border-radius: 0px 0px 10px 10px;")
        self.ph = 7.0

    def update_color(self, ph):
        """Phenolphthalein Indicator Simulation."""
        # Range: Clear (pH < 8.2) -> Pink (pH > 10.0)
        self.ph = ph

        start_ph = 8.0
        end_ph = 10.0

        # RGB Values
        color_clear = np.array([250, 250, 255])  # Almost white
        color_pink = np.array([255, 0, 127])  # Deep Pink

        if ph <= start_ph:
            rgb = color_clear
        elif ph >= end_ph:
            rgb = color_pink
        else:
            # Linear Interpolation
            t = (ph - start_ph) / (end_ph - start_ph)
            rgb = (1 - t) * color_clear + t * color_pink

        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgb({int(rgb[0])}, {int(rgb[1])}, {int(rgb[2])});
                border: 3px solid #444;
                border-top: none;
                border-radius: 15px;
            }}
        """)


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        fig.tight_layout()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Digital Titration Lab")
        self.setGeometry(100, 100, 1000, 600)

        self.sim = TitrationSimulation()
        self.history_vol = []
        self.history_ph = []

        self.setup_ui()
        self.reset_simulation()

    def setup_ui(self):
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- LEFT PANEL (Controls & Beaker) ---
        left_panel = QGroupBox("Lab Bench")
        left_layout = QVBoxLayout(left_panel)

        # Acid Selector
        left_layout.addWidget(QLabel("Select Analyte (Acid):"))
        self.acid_combo = QComboBox()
        self.acid_combo.addItems(self.sim.acids.keys())
        self.acid_combo.setCurrentText("Acetic Acid (Weak)")
        self.acid_combo.currentTextChanged.connect(self.change_acid)
        left_layout.addWidget(self.acid_combo)

        left_layout.addSpacing(20)

        # Beaker Visualization
        beaker_container = QWidget()
        beaker_layout = QHBoxLayout(beaker_container)
        self.beaker = BeakerWidget()
        beaker_layout.addStretch()
        beaker_layout.addWidget(self.beaker)
        beaker_layout.addStretch()
        left_layout.addWidget(beaker_container)

        left_layout.addSpacing(20)

        # Info Labels
        self.lbl_vol = QLabel("Titrant Added: 0.00 mL")
        self.lbl_vol.setFont(QFont("Arial", 12))
        left_layout.addWidget(self.lbl_vol)

        self.lbl_ph = QLabel("pH: 0.00")
        self.lbl_ph.setFont(QFont("Arial", 14, QFont.Bold))
        left_layout.addWidget(self.lbl_ph)

        # Controls
        btn_drop = QPushButton("+ Add Drop (0.1 mL)")
        btn_drop.setStyleSheet("background-color: #ddddff; padding: 10px; font-weight: bold;")
        btn_drop.clicked.connect(lambda: self.add_titrant(0.1))
        left_layout.addWidget(btn_drop)

        btn_stream = QPushButton("++ Stream (1.0 mL)")
        btn_stream.clicked.connect(lambda: self.add_titrant(1.0))
        left_layout.addWidget(btn_stream)

        left_layout.addStretch()

        btn_reset = QPushButton("Reset Experiment")
        btn_reset.setStyleSheet("background-color: #ffdddd; padding: 5px;")
        btn_reset.clicked.connect(self.reset_simulation)
        left_layout.addWidget(btn_reset)

        # Options
        self.chk_deriv = QCheckBox("Show Derivative (dpH/dV)")
        self.chk_deriv.stateChanged.connect(self.update_plot)
        left_layout.addWidget(self.chk_deriv)

        # --- RIGHT PANEL (Graph) ---
        right_panel = QGroupBox("Titration Curve")
        right_layout = QVBoxLayout(right_panel)
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        right_layout.addWidget(self.canvas)

        # Add panels to main layout
        main_layout.addWidget(left_panel, 30)
        main_layout.addWidget(right_panel, 70)

    def change_acid(self, text):
        self.sim.current_acid = self.sim.acids[text]
        self.reset_simulation()

    def reset_simulation(self):
        self.sim.vb_added = 0.0
        self.history_vol = [0.0]
        self.history_ph = [self.sim.solve_ph()]
        self.update_interface()

    def add_titrant(self, amount):
        self.sim.vb_added += amount

        # Chemistry Calculation
        new_ph = self.sim.solve_ph()

        # Update History
        self.history_vol.append(self.sim.vb_added)
        self.history_ph.append(new_ph)

        self.update_interface()

    def update_interface(self):
        # Update Labels
        current_ph = self.history_ph[-1]
        self.lbl_vol.setText(f"Titrant Added: {self.sim.vb_added:.2f} mL")
        self.lbl_ph.setText(f"pH: {current_ph:.2f}")

        # Update Beaker Color
        self.beaker.update_color(current_ph)

        # Update Plot
        self.update_plot()

    def update_plot(self):
        self.canvas.axes.cla()

        # Plot pH Curve
        vols = np.array(self.history_vol)
        phs = np.array(self.history_ph)

        self.canvas.axes.plot(vols, phs, 'b.-', label='pH', linewidth=1.5, markersize=8)
        self.canvas.axes.set_xlabel('Volume NaOH (mL)')
        self.canvas.axes.set_ylabel('pH', color='b')
        self.canvas.axes.tick_params(axis='y', labelcolor='b')
        self.canvas.axes.set_ylim(0, 14)
        self.canvas.axes.grid(True, alpha=0.3)

        # Plot Derivative if checked
        if self.chk_deriv.isChecked() and len(vols) > 1:
            # Calculate dpH/dV
            # Use central difference or simple difference
            d_ph = np.diff(phs)
            d_v = np.diff(vols)
            # Avoid division by zero
            with np.errstate(divide='ignore', invalid='ignore'):
                deriv = d_ph / d_v

            # Midpoints for plotting derivative
            v_mid = (vols[:-1] + vols[1:]) / 2

            ax2 = self.canvas.axes.twinx()
            ax2.fill_between(v_mid, deriv, color='orange', alpha=0.3, label='dpH/dV')
            ax2.plot(v_mid, deriv, 'r--', label='dpH/dV', alpha=0.6)
            ax2.set_ylabel('Derivative (dpH/dV)', color='r')
            ax2.tick_params(axis='y', labelcolor='r')
            ax2.set_ylim(0, max(np.max(deriv) * 1.1, 1))

        self.canvas.axes.set_title(f"Titration: {self.sim.current_acid.name} vs NaOH")
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Optional: Set a nice dark theme or fusion style
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())