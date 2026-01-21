# Function to print a truth table
def check_gate(gate_name):
    print(f"--- {gate_name.upper()} GATE ---")
    print(" A | B | Output")
    print("---|---|-------")

    inputs = [(0, 0), (0, 1), (1, 0), (1, 1)]

    for A, B in inputs:
        if gate_name == "AND":
            out = A & B
        elif gate_name == "OR":
            out = A | B
        elif gate_name == "XOR":
            out = A ^ B
        elif gate_name == "NAND":
            out = int(not (A & B))  # 'not' gives True/False, int converts to 1/0

        print(f" {A} | {B} |   {out}")
    print("\n")


# Run the checks
check_gate("AND")
check_gate("XOR")
check_gate("NAND")