import numpy as np
import matplotlib.pyplot as plt
import random


# --- Quantum Physics Engine (NumPy Implementation) ---

class Qubit:
    """
    Represents a single photon in a quantum state.
    We use vector representation (Linear Algebra).
    """

    def __init__(self, state_vector):
        self.state = state_vector  # numpy array [alpha, beta]

    def measure(self, basis):
        """
        Simulates measuring a qubit in a specific basis.
        Basis 'rectilinear' (+): |0> and |1>
        Basis 'diagonal' (X): |+> and |->

        Returns: Measured Bit (0 or 1)
        Side Effect: Collapses the qubit state (Heisenberg Uncertainty).
        """
        # Define measurement operators
        # Rectilinear Basis states
        zero = np.array([1, 0])  # |0>
        one = np.array([0, 1])  # |1>

        # Diagonal Basis states
        plus = np.array([1, 1]) / np.sqrt(2)  # |+>
        minus = np.array([1, -1]) / np.sqrt(2)  # |->

        if basis == '+':
            # Measure in Rectilinear Basis
            prob_0 = np.abs(np.dot(self.state, zero)) ** 2

            if random.random() < prob_0:
                self.state = zero  # Collapse to |0>
                return 0
            else:
                self.state = one  # Collapse to |1>
                return 1

        elif basis == 'X':
            # Measure in Diagonal Basis
            prob_plus = np.abs(np.dot(self.state, plus)) ** 2

            if random.random() < prob_plus:
                self.state = plus  # Collapse to |+>
                return 0
            else:
                self.state = minus  # Collapse to |->
                return 1


class QuantumChannel:
    def __init__(self, eve_present=False):
        self.eve_present = eve_present
        self.intercepted_count = 0

    def transmit(self, qubit):
        """
        Sends a qubit from Alice to Bob.
        If Eve is present, she tries to measure it first.
        """
        if self.eve_present:
            # Eve doesn't know the basis, guesses randomly
            eve_basis = random.choice(['+', 'X'])
            _ = qubit.measure(eve_basis)  # MEASUREMENT COLLAPSES STATE
            self.intercepted_count += 1

        return qubit


# --- The BB84 Actors ---

class Alice:
    def __init__(self, num_bits):
        self.n = num_bits
        self.bits = []
        self.bases = []
        self.qubits = []

    def prepare_qubits(self):
        """Generates random bits and encodes them into qubits."""
        self.bits = np.random.randint(0, 2, self.n)
        self.bases = [random.choice(['+', 'X']) for _ in range(self.n)]
        self.qubits = []

        # Vector Definitions
        state_map = {
            (0, '+'): np.array([1, 0]),  # |0>
            (1, '+'): np.array([0, 1]),  # |1>
            (0, 'X'): np.array([1, 1]) / np.sqrt(2),  # |+>
            (1, 'X'): np.array([1, -1]) / np.sqrt(2)  # |->
        }

        for bit, basis in zip(self.bits, self.bases):
            vec = state_map[(bit, basis)]
            self.qubits.append(Qubit(vec))

        return self.qubits


class Bob:
    def __init__(self, num_bits):
        self.n = num_bits
        self.bases = []
        self.measured_bits = []

    def measure_incoming(self, qubits):
        """Generates random bases and measures incoming photons."""
        self.bases = [random.choice(['+', 'X']) for _ in range(self.n)]
        self.measured_bits = []

        for q, basis in zip(qubits, self.bases):
            bit = q.measure(basis)
            self.measured_bits.append(bit)


# --- Main Simulation ---

def simulate_bb84(num_bits=100, eve_present=False):
    print(f"\n--- SIMULATION START (Eve Present: {eve_present}) ---")

    # 1. Setup
    channel = QuantumChannel(eve_present)
    alice = Alice(num_bits)
    bob = Bob(num_bits)

    # 2. Alice prepares qubits
    print(f"Alice: Generating {num_bits} qubits...")
    qubits_to_send = alice.prepare_qubits()

    # 3. Transmission (Quantum Channel)
    print("Channel: Transmitting photons...")
    received_qubits = []
    for q in qubits_to_send:
        # Pass through channel (Eve might touch it)
        received_qubits.append(channel.transmit(q))

    # 4. Bob measures
    print("Bob: Measuring incoming photons...")
    bob.measure_incoming(received_qubits)

    # 5. Sifting Phase (Public Discussion)
    # Alice and Bob publicly tell each other which BASIS they used (but not the bit value).
    # They keep bits where the bases matched.
    print("Network: Sifting keys (discarding basis mismatches)...")

    sifted_key_alice = []
    sifted_key_bob = []
    match_indices = []

    for i in range(num_bits):
        if alice.bases[i] == bob.bases[i]:
            sifted_key_alice.append(alice.bits[i])
            sifted_key_bob.append(bob.measured_bits[i])
            match_indices.append(i)

    # 6. Error Check (QBER Calculation)
    # In real life, they reveal a subset of the key to check errors.
    # Here we check the whole sifted key for simulation purposes.

    if len(sifted_key_alice) == 0:
        print("Error: No bases matched (Simulation too short).")
        return

    errors = 0
    for a, b in zip(sifted_key_alice, sifted_key_bob):
        if a != b:
            errors += 1

    qber = errors / len(sifted_key_alice)

    # --- Reporting ---
    print("\n--- RESULTS ---")
    print(f"Total Bits Sent: {num_bits}")
    print(f"Sifted Key Length: {len(sifted_key_alice)} (approx 50% of total)")
    print(f"Bit Errors Found: {errors}")
    print(f"QBER (Quantum Bit Error Rate): {qber:.2%}")

    if qber > 0.15:  # Threshold is usually around 11-15%
        print("\n[!] CRITICAL ALERT: Eavesdropper Detected!")
        print("[!] CONNECTION ABORTED. Key is compromised.")
        print("[!] Physics Explanation: Eve measured the qubits, collapsing their wavefunctions")
        print("    and altering the states before Bob received them.")
    else:
        print("\n[OK] Connection Secure.")
        print(f"[OK] Final Shared Key (First 10 bits): {sifted_key_alice[:10]}...")

    # --- Visualization ---
    visualize_results(alice, bob, match_indices, qber, eve_present)


def visualize_results(alice, bob, match_indices, qber, eve_present):
    fig, ax = plt.subplots(figsize=(12, 6))

    # Only show first 30 bits for clarity
    limit = 30
    indices = np.arange(limit)

    # Plot Alice's Bases
    # 1 = +, 0 = X for visualization
    a_bases_num = [1 if b == '+' else 0 for b in alice.bases[:limit]]
    b_bases_num = [1 if b == '+' else 0 for b in bob.bases[:limit]]

    # Draw Grid
    ax.set_ylim(-1, 5)
    ax.set_xlim(-1, limit)
    ax.set_yticks([])
    ax.set_xticks(indices)

    # Row 1: Alice's Bits
    for i in indices:
        color = 'green' if i in match_indices else 'gray'
        ax.text(i, 4, str(alice.bits[i]), ha='center', color='black', fontsize=12)
        ax.text(i, 3.5, alice.bases[i], ha='center', color=color, fontweight='bold')

    ax.text(-1.5, 4, "Alice Bit:", ha='right', fontweight='bold')
    ax.text(-1.5, 3.5, "Alice Basis:", ha='right', fontweight='bold')

    # Row 2: Transmission
    ax.text(limit / 2, 2.5, "--- QUANTUM CHANNEL ---", ha='center', color='blue', alpha=0.5)
    if eve_present:
        ax.text(limit / 2, 2.2, "⚠️ EVE INTERCEPTING ⚠️", ha='center', color='red', fontweight='bold')

    # Row 3: Bob's Data
    for i in indices:
        # Check for Error in Sifted Key
        is_match = i in match_indices
        is_error = is_match and (alice.bits[i] != bob.measured_bits[i])

        basis_color = 'green' if is_match else 'gray'
        bit_color = 'red' if is_error else 'black'
        weight = 'bold' if is_error else 'normal'

        ax.text(i, 1.5, bob.bases[i], ha='center', color=basis_color, fontweight='bold')
        ax.text(i, 1, str(bob.measured_bits[i]), ha='center', color=bit_color, fontsize=12, fontweight=weight)

    ax.text(-1.5, 1.5, "Bob Basis:", ha='right', fontweight='bold')
    ax.text(-1.5, 1, "Bob Measure:", ha='right', fontweight='bold')

    # Key Status
    status_color = 'red' if qber > 0.15 else 'green'
    status_text = f"QBER: {qber:.1%} (SECURE)" if qber <= 0.15 else f"QBER: {qber:.1%} (COMPROMISED)"

    ax.text(limit / 2, -0.5, status_text, ha='center', color='white', fontsize=14,
            bbox=dict(facecolor=status_color, alpha=0.8, pad=10))

    ax.set_title("BB84 Protocol Visualization (First 30 Qubits)")
    ax.axis('off')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    print("Welcome to Strategic Command QKD Simulator.")
    print("1. Run Secure Simulation")
    print("2. Run Compromised Simulation (Eve Present)")

    choice = input("Select Scenario (1/2): ")

    if choice == '2':
        simulate_bb84(num_bits=100, eve_present=True)
    else:
        simulate_bb84(num_bits=100, eve_present=False)