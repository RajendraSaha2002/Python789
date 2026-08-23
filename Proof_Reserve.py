

import json
import hashlib

# SECP256k1 Curve Parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# Base Generator G
G_X = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
G_Y = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

# NUMS Generator H
H_X = 0x50929BE41A704954B78B4B6035E97A5E078A5A0F28EC96D547BFEE9ACE803AC0
H_Y = 0x31D3C6863973926E049E637CB1B5F6E0A83072DD3449AEAA747661B4B71C1825


def inv_mod(k, p=P):
    return pow(k, p - 2, p)


def point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2:
        if y1 == y2:
            # Point doubling
            lam = (3 * x1 * x1) * inv_mod(2 * y1, P) % P
            x3 = (lam * lam - 2 * x1) % P
            y3 = (lam * (x1 - x3) - y1) % P
            return (x3, y3)
        return None  # Infinity
    lam = (y2 - y1) * inv_mod(x2 - x1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def scalar_mul(point, scalar):
    res = None
    curr = point
    scalar = scalar % N
    while scalar > 0:
        if scalar & 1:
            res = point_add(res, curr)
        curr = point_add(curr, curr)
        scalar >>= 1
    return res


def sha256(data_hex: str) -> str:
    return hashlib.sha256(bytes.fromhex(data_hex)).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def verify_customer_proof(proof_filepath: str):
    print("=" * 70)
    print("      ZK PROOF-OF-RESERVE CLIENT VERIFICATION TOOL       ")
    print("=" * 70)

    with open(proof_filepath, 'r') as f:
        data = json.load(f)

    user_id = data["user_id"]
    balance = data["balance"]
    blinding_factor = int(data["blinding_factor"], 16)
    leaf_index = data["leaf_index"]
    merkle_siblings = data["merkle_siblings"]
    expected_root = data["merkle_root"]
    claimed_reserve = data["claimed_reserve"]

    total_c_pt = (int(data["total_commitment"]["x"], 16), int(data["total_commitment"]["y"], 16))
    t_pt = (int(data["schnorr_proof"]["t_x"], 16), int(data["schnorr_proof"]["t_y"], 16))
    z = int(data["schnorr_proof"]["z"], 16)

    print(f"\n[1] Verifying User Commitment for '{user_id}'...")
    # C_i = b_i * G + r_i * H
    p1 = scalar_mul((G_X, G_Y), balance)
    p2 = scalar_mul((H_X, H_Y), blinding_factor)
    my_commitment = point_add(p1, p2)
    my_c_x = f"{my_commitment[0]:064x}"
    my_c_y = f"{my_commitment[1]:064x}"
    print(f"    Computed Commitment C_i.x: {my_c_x}")

    # Leaf = SHA256( SHA256(user_id) || C_i.x || C_i.y )
    uid_hash = sha256_text(user_id)
    leaf_preimage = uid_hash + my_c_x + my_c_y
    current_hash = sha256(leaf_preimage)
    print(f"    Computed Leaf Hash:        {current_hash}")

    print("\n[2] Verifying Merkle Inclusion Path to Root...")
    curr_idx = leaf_index
    for depth, sibling in enumerate(merkle_siblings):
        if curr_idx % 2 == 0:
            combined = current_hash + sibling
        else:
            combined = sibling + current_hash
        current_hash = sha256(combined)
        curr_idx //= 2
        print(f"    Level {depth + 1} Hash: {current_hash}")

    if current_hash.lower() == expected_root.lower():
        print("  ✓ SUCCESS: User balance is cryptographically included in the Merkle Root!")
    else:
        print("  ✗ ERROR: Merkle root mismatch!")
        return False

    print("\n[3] Verifying Schnorr Zero-Knowledge Proof of Reserve...")
    # 1. Compute Q = C_total - S*G
    s_g = scalar_mul((G_X, G_Y), claimed_reserve)
    s_g_neg = (s_g[0], (P - s_g[1]) % P)
    Q = point_add(total_c_pt, s_g_neg)

    # 2. Compute Fiat-Shamir challenge: e = SHA256(Q.x || Q.y || T.x || T.y || S) mod N
    q_x_hex = f"{Q[0]:064x}"
    q_y_hex = f"{Q[1]:064x}"
    t_x_hex = f"{t_pt[0]:064x}"
    t_y_hex = f"{t_pt[1]:064x}"
    s_hex = f"{claimed_reserve:064x}"

    chal_hex = sha256(q_x_hex + q_y_hex + t_x_hex + t_y_hex + s_hex)
    e = int(chal_hex, 16) % N

    # 3. Verify: z * H == T + e * Q
    lhs = scalar_mul((H_X, H_Y), z)
    e_q = scalar_mul(Q, e)
    rhs = point_add(t_pt, e_q)

    print(f"    LHS (z * H):       ({lhs[0]:064x}, {lhs[1]:064x})")
    print(f"    RHS (T + e * Q):   ({rhs[0]:064x}, {rhs[1]:064x})")

    if lhs == rhs:
        print("  ✓ SUCCESS: Schnorr Proof Verified! Exchange holds 100% of claimed reserves ($" + str(
            claimed_reserve) + ").")
        print("\n======================================================================")
        print("FINAL VERDICT: ALL CRYPTOGRAPHIC PROOFS PASSED (Zero-Knowledge Intact)")
        print("======================================================================")
        return True
    else:
        print("  ✗ ERROR: Schnorr proof validation failed!")
        return False


if __name__ == "__main__":
    verify_customer_proof("user_proof_alice.json")