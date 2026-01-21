def delta_to_star(R1, R2, R3):
    """
    Converts Delta (Pi) resistors to Star (T)
    R1, R2, R3 are the sides of the Delta triangle.
    """
    R_sum = R1 + R2 + R3

    # The Transformation Formulas
    Ra = (R1 * R2) / R_sum
    Rb = (R2 * R3) / R_sum
    Rc = (R3 * R1) / R_sum

    return Ra, Rb, Rc


# --- INPUT YOUR VALUES HERE ---
# Example: Three 30 Ohm resistors in Delta
R1_val = 30
R2_val = 30
R3_val = 30

# Calculate
Ra, Rb, Rc = delta_to_star(R1_val, R2_val, R3_val)

# Output Results
print(f"--- Delta to Star Conversion ---")
print(f"Input Delta: R1={R1_val}, R2={R2_val}, R3={R3_val} Ohms")
print(f"Output Star: Ra={Ra:.2f}, Rb={Rb:.2f}, Rc={Rc:.2f} Ohms")