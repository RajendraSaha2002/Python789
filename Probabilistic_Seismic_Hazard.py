import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
import matplotlib.colors as mcolors


class SeismicSource:
    def __init__(self, name, distance, m_min, m_max, activity_rate, b_value=None):
        self.name = name
        self.r = distance  # Fixed distance to site (km) for simplification
        self.m_min = m_min
        self.m_max = m_max
        self.rate = activity_rate  # Annual rate of M > m_min
        self.b_value = b_value

        # If no b-value provided, estimate it from a synthetic catalog using MLE
        if self.b_value is None:
            self.b_value = self.estimate_b_value_mle()

        self.beta = self.b_value * np.log(10)

    def estimate_b_value_mle(self):
        """Estimates Gutenberg-Richter b-value using Aki-Utsu Maximum Likelihood Estimation."""
        np.random.seed(42)
        # Generate synthetic catalog representing decades of observation
        true_b = 1.0
        synthetic_mags = np.random.exponential(scale=1 / (true_b * np.log(10)), size=2000) + self.m_min
        synthetic_mags = synthetic_mags[synthetic_mags <= self.m_max]

        # Aki-Utsu MLE formula for b-value
        mean_mag = np.mean(synthetic_mags)
        b_mle = (1.0 / (mean_mag - self.m_min)) * np.log10(np.exp(1))
        return b_mle

    def pdf_m(self, m):
        """Truncated Exponential Probability Density Function for Magnitude."""
        # Ensure we only calculate for m within bounds, else 0
        valid = (m >= self.m_min) & (m <= self.m_max)
        pdf = np.zeros_like(m)
        num = self.beta * np.exp(-self.beta * (m[valid] - self.m_min))
        den = 1.0 - np.exp(-self.beta * (self.m_max - self.m_min))
        pdf[valid] = num / den
        return pdf


# ====================================================================
# 2. GROUND MOTION PREDICTION EQUATION (GMPE)
# ====================================================================
class SimplifiedGMPE:
    def __init__(self):
        # Synthetic attenuation coefficients for periods: PGA (0.0s), Sa(0.2s), Sa(1.0s)
        # Functional form: ln(IM) = c1 + c2*M + c3*ln(sqrt(R^2 + h^2))
        self.coeffs = {
            0.0: {'c1': -1.6, 'c2': 0.85, 'c3': -1.1, 'h': 6.0, 'sigma': 0.60},
            0.2: {'c1': -1.0, 'c2': 0.90, 'c3': -1.0, 'h': 6.0, 'sigma': 0.65},
            1.0: {'c1': -2.8, 'c2': 1.05, 'c3': -0.9, 'h': 8.0, 'sigma': 0.70}
        }

    def evaluate(self, m, r, period):
        """Returns the median ln(IM) and standard deviation (sigma) for given M, R, T."""
        c = self.coeffs[period]
        median_ln_im = c['c1'] + c['c2'] * m + c['c3'] * np.log(np.sqrt(r ** 2 + c['h'] ** 2))
        return median_ln_im, c['sigma']


# ====================================================================
# 3. PSHA ENGINE (INTEGRATION & LOGIC TREE)
# ====================================================================
class PSHAEngine:
    def __init__(self, sources, gmpe):
        self.sources = sources
        self.gmpe = gmpe
        # Log-spaced Intensity Measure levels (g)
        self.im_levels = np.logspace(np.log10(0.001), np.log10(3.0), 50)

    def compute_hazard_integral(self, source, period, m_max_override=None):
        """Computes the annual rate of exceedance for a single source."""
        rates = np.zeros_like(self.im_levels)
        m_max = m_max_override if m_max_override else source.m_max

        # Discretize magnitude integration space
        m_bins = np.linspace(source.m_min, m_max, 100)
        dm = m_bins[1] - m_bins[0]

        # PSHA Poisson Integral
        # lambda(IM > x) = Rate * Sum [ P(IM > x | M, R) * f(M) * dm ]
        for i, im in enumerate(self.im_levels):
            exceedance_prob_sum = 0.0
            for m in m_bins:
                mu_ln_im, sigma = self.gmpe.evaluate(m, source.r, period)

                # Probability of exceedance using standard normal CDF survival function
                epsilon = (np.log(im) - mu_ln_im) / sigma
                p_exceed = 1.0 - norm.cdf(epsilon)

                # PDF of magnitude
                f_m = source.pdf_m(np.array([m]))[0]

                exceedance_prob_sum += p_exceed * f_m * dm

            rates[i] = source.rate * exceedance_prob_sum

        return rates

    def run_logic_tree(self, period):
        """Runs the hazard integral through an Epistemic Logic Tree."""
        # Logic tree branches for Source 1 (Fault A) Maximum Magnitude uncertainty
        # Branch 1: Mmax = 7.0 (Weight 60%), Branch 2: Mmax = 7.5 (Weight 40%)
        m_max_branches = [7.0, 7.5]
        weights = [0.6, 0.4]

        total_rates_weighted = np.zeros_like(self.im_levels)
        branch_curves = []

        for m_max, weight in zip(m_max_branches, weights):
            branch_total = np.zeros_like(self.im_levels)
            for src in self.sources:
                if src.name == "Fault A (Crustal)":
                    branch_total += self.compute_hazard_integral(src, period, m_max_override=m_max)
                else:
                    branch_total += self.compute_hazard_integral(src, period)

            branch_curves.append(branch_total)
            total_rates_weighted += weight * branch_total

        return total_rates_weighted, branch_curves

    def compute_uhs(self, return_periods):
        """Extracts Uniform Hazard Spectra (UHS) for specified return periods."""
        periods = [0.0, 0.2, 1.0]
        uhs = {rp: [] for rp in return_periods}

        for t in periods:
            rates, _ = self.run_logic_tree(t)
            # Avoid log(0)
            rates[rates == 0] = 1e-20

            for rp in return_periods:
                target_rate = 1.0 / rp
                # Interpolate in log-log space (Requires monotonically increasing x, so we reverse arrays)
                im_log = np.interp(np.log(target_rate), np.log(rates[::-1]), np.log(self.im_levels[::-1]))
                uhs[rp].append(np.exp(im_log))

        return periods, uhs

    def deaggregate(self, target_im, period):
        """Performs M-R-Epsilon deaggregation at a specific IM level."""
        m_bins = np.linspace(5.0, 8.0, 15)
        r_bins = np.array([10, 20, 30, 40, 50, 60, 80, 100])

        deagg_matrix = np.zeros((len(m_bins) - 1, len(r_bins) - 1))
        epsilon_matrix = np.zeros((len(m_bins) - 1, len(r_bins) - 1))
        total_rate = 0.0

        for i in range(len(m_bins) - 1):
            for j in range(len(r_bins) - 1):
                m_center = (m_bins[i] + m_bins[i + 1]) / 2.0
                r_center = (r_bins[j] + r_bins[j + 1]) / 2.0

                bin_rate = 0.0
                eps_weighted = 0.0

                for src in self.sources:
                    # Check if source falls in this Distance bin
                    if r_bins[j] <= src.r < r_bins[j + 1]:
                        if m_bins[i] >= src.m_min and m_bins[i + 1] <= src.m_max:
                            mu, sigma = self.gmpe.evaluate(m_center, src.r, period)
                            epsilon = (np.log(target_im) - mu) / sigma
                            p_exceed = 1.0 - norm.cdf(epsilon)

                            # PDF contribution (simplified bin mass)
                            f_m = src.pdf_m(np.array([m_center]))[0]
                            dm = m_bins[i + 1] - m_bins[i]

                            contrib = src.rate * p_exceed * f_m * dm
                            bin_rate += contrib
                            eps_weighted += contrib * epsilon

                deagg_matrix[i, j] = bin_rate
                if bin_rate > 0:
                    epsilon_matrix[i, j] = eps_weighted / bin_rate
                total_rate += bin_rate

        # Convert to percentage
        if total_rate > 0:
            deagg_matrix = (deagg_matrix / total_rate) * 100.0

        return m_bins, r_bins, deagg_matrix, epsilon_matrix


# ====================================================================
# 4. VISUALIZATION DASHBOARD
# ====================================================================
def plot_psha_dashboard():
    # 1. Initialization
    sources = [
        SeismicSource("Fault A (Crustal)", distance=15.0, m_min=5.0, m_max=7.5, activity_rate=0.05),
        SeismicSource("Fault B (Subduction)", distance=60.0, m_min=5.0, m_max=8.2, activity_rate=0.10),
        SeismicSource("Background Grid", distance=35.0, m_min=5.0, m_max=6.5, activity_rate=0.20)
    ]
    gmpe = SimplifiedGMPE()
    engine = PSHAEngine(sources, gmpe)

    plt.style.use('seaborn-v0_8-darkgrid')
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('Probabilistic Seismic Hazard Analysis (PSHA) Framework', fontsize=18, fontweight='bold', y=0.96)

    # --- Panel 1: Source Gutenberg-Richter Recurrence ---
    ax1 = fig.add_subplot(231)
    m_range = np.linspace(5.0, 7.5, 50)
    for src in sources:
        # N(M) = rate * P(m > M)
        beta = src.beta
        # Cumulative probability
        cum_prob = (np.exp(-beta * (m_range - src.m_min)) - np.exp(-beta * (src.m_max - src.m_min))) / \
                   (1 - np.exp(-beta * (src.m_max - src.m_min)))
        cum_prob[m_range > src.m_max] = 0
        ax1.semilogy(m_range, src.rate * cum_prob, label=f"{src.name} (b={src.b_value:.2f})")

    ax1.set_title("1. Source Recurrence (Gutenberg-Richter)")
    ax1.set_xlabel("Magnitude (Mw)")
    ax1.set_ylabel("Annual Rate of Exceedance, N(M)")
    ax1.set_ylim([1e-4, 1.0])
    ax1.legend(fontsize=8)

    # --- Panel 2: Ground Motion Prediction Equation (GMPE) ---
    ax2 = fig.add_subplot(232)
    distances = np.logspace(0, 2.5, 50)
    mags_to_plot = [5.5, 6.5, 7.5]
    colors = ['#61afef', '#e5c07b', '#e06c75']
    for m, col in zip(mags_to_plot, colors):
        pga_medians = [np.exp(gmpe.evaluate(m, r, 0.0)[0]) for r in distances]
        ax2.loglog(distances, pga_medians, label=f"Mw = {m}", color=col, linewidth=2)

    ax2.set_title("2. GMPE Attenuation (Median PGA)")
    ax2.set_xlabel("Distance (km)")
    ax2.set_ylabel("Median PGA (g)")
    ax2.legend()

    # --- Panel 3: Epistemic Logic Tree Sensitivity ---
    ax3 = fig.add_subplot(233)
    mean_hazard, branches = engine.run_logic_tree(0.0)
    ax3.loglog(engine.im_levels, branches[0], '--', color='grey', label="Branch 1: Mmax=7.0 (60%)")
    ax3.loglog(engine.im_levels, branches[1], '-.', color='grey', label="Branch 2: Mmax=7.5 (40%)")
    ax3.loglog(engine.im_levels, mean_hazard, 'k-', linewidth=2, label="Weighted Mean Hazard")

    ax3.set_title("3. Epistemic Uncertainty (Logic Tree)")
    ax3.set_xlabel("Peak Ground Acceleration (g)")
    ax3.set_ylabel("Annual Exceedance Rate (λ)")
    ax3.set_ylim([1e-5, 1e-1])
    ax3.legend(fontsize=8)

    # --- Panel 4: Hazard Curves (Multiple Periods) ---
    ax4 = fig.add_subplot(234)
    periods = {0.0: ('PGA', '#e06c75'), 0.2: ('Sa(0.2s)', '#61afef'), 1.0: ('Sa(1.0s)', '#98c379')}
    for t, (lbl, col) in periods.items():
        rates, _ = engine.run_logic_tree(t)
        ax4.loglog(engine.im_levels, rates, label=lbl, color=col, linewidth=2)

    # 475-year return period reference line (10% in 50 years)
    ax4.axhline(1 / 475, color='black', linestyle=':', label="Tr = 475 yr")
    ax4.set_title("4. Integrated Hazard Curves")
    ax4.set_xlabel("Spectral Acceleration (g)")
    ax4.set_ylabel("Annual Exceedance Rate (λ)")
    ax4.set_ylim([1e-5, 1e-1])
    ax4.legend(fontsize=8)

    # --- Panel 5: Uniform Hazard Spectra (UHS) ---
    ax5 = fig.add_subplot(235)
    t_vals, uhs_data = engine.compute_uhs([475, 2475])

    ax5.plot(t_vals, uhs_data[475], 'o-', color='#e5c07b', linewidth=2, label='10% in 50 yrs (Tr=475)')
    ax5.plot(t_vals, uhs_data[2475], 's-', color='#e06c75', linewidth=2, label='2% in 50 yrs (Tr=2475)')
    ax5.set_title("5. Uniform Hazard Spectra (UHS)")
    ax5.set_xlabel("Spectral Period (s)")
    ax5.set_ylabel("Spectral Acceleration (g)")
    ax5.legend(fontsize=8)
    # Ensure x-axis ticks align with our defined periods
    ax5.set_xticks([0.0, 0.2, 1.0])
    ax5.set_xticklabels(['PGA', '0.2', '1.0'])

    # --- Panel 6: M-R-Epsilon Deaggregation (3D Bar Chart) ---
    ax6 = fig.add_subplot(236, projection='3d')
    # Target IM corresponding roughly to PGA for Tr=475
    target_im = np.exp(np.interp(np.log(1 / 475), np.log(mean_hazard[::-1]), np.log(engine.im_levels[::-1])))
    m_bins, r_bins, deagg, eps = engine.deaggregate(target_im, 0.0)

    # Plotting setup for 3D Bars
    xpos, ypos = np.meshgrid(m_bins[:-1], r_bins[:-1], indexing="ij")
    xpos = xpos.ravel()
    ypos = ypos.ravel()
    zpos = 0
    dx = (m_bins[1] - m_bins[0]) * 0.8
    dy = (r_bins[1] - r_bins[0]) * 0.8
    dz = deagg.ravel()

    # Color mapping based on Epsilon (standard deviations from median)
    eps_flat = eps.ravel()
    norm_eps = mcolors.Normalize(vmin=-1, vmax=2.5)
    cmap = cm.viridis
    colors = cmap(norm_eps(eps_flat))

    ax6.bar3d(xpos, ypos, zpos, dx, dy, dz, color=colors, alpha=0.9, zsort='average')

    # Create a colorbar axis manually for the 3D plot
    cbar_ax = fig.add_axes([0.91, 0.15, 0.015, 0.25])
    sm = cm.ScalarMappable(cmap=cmap, norm=norm_eps)
    sm.set_array([])
    fig.colorbar(sm, cax=cbar_ax, label='Mean Epsilon (ε)')

    ax6.set_title(f"6. Deaggregation (PGA = {target_im:.2f}g, Tr=475)")
    ax6.set_xlabel('Magnitude (Mw)')
    ax6.set_ylabel('Distance (km)')
    ax6.set_zlabel('Contribution (%)')
    ax6.view_init(elev=30, azim=-125)

    plt.tight_layout(rect=[0, 0, 0.9, 1])  # Leave room for 3D colorbar
    plt.subplots_adjust(top=0.92)
    plt.show()


if __name__ == "__main__":
    plot_psha_dashboard()