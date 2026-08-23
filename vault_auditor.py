

import hashlib
import struct
import os

ROUND_CONSTANTS = [
    0xf0, 0xe1, 0xd2, 0xc3, 0xb4, 0xa5, 0x96, 0x87, 0x78, 0x69, 0x5a, 0x4b
]


def rotr(x, n):
    return ((x >> n) | (x << (64 - n))) & 0xFFFFFFFFFFFFFFFF


def ascon_permutation(s, rounds):
    for r in range(12 - rounds, 12):
        s[2] ^= ROUND_CONSTANTS[r]
        s[0] ^= s[4];
        s[4] ^= s[3];
        s[2] ^= s[1]
        t0 = (~s[0]) & s[1];
        t1 = (~s[1]) & s[2];
        t2 = (~s[2]) & s[3]
        t3 = (~s[3]) & s[4];
        t4 = (~s[4]) & s[0]
        s[0] ^= t1;
        s[1] ^= t2;
        s[2] ^= t3;
        s[3] ^= t4;
        s[4] ^= t0
        s[1] ^= s[0];
        s[0] ^= s[4];
        s[3] ^= s[2];
        s[2] = (~s[2]) & 0xFFFFFFFFFFFFFFFF
        s[0] ^= rotr(s[0], 19) ^ rotr(s[0], 28)
        s[1] ^= rotr(s[1], 61) ^ rotr(s[1], 39)
        s[2] ^= rotr(s[2], 1) ^ rotr(s[2], 6)
        s[3] ^= rotr(s[3], 10) ^ rotr(s[3], 17)
        s[4] ^= rotr(s[4], 7) ^ rotr(s[4], 41)


def decrypt_ascon_file(file_path: str, password: str) -> bool:
    print(f"[*] Decrypting and Authenticating: {file_path}")
    if not os.path.exists(file_path):
        print("[-] File not found.")
        return False

    with open(file_path, "rb") as f:
        nonce = f.read(16)
        expected_tag = f.read(16)
        ciphertext = f.read()

    # Derive 128-bit key
    key = hashlib.sha256(password.encode('utf-8')).digest()[:16]

    k0, k1 = struct.unpack(">QQ", key)
    n0, n1 = struct.unpack(">QQ", nonce)

    s = [0x80400c0600000000, k0, k1, n0, n1]
    ascon_permutation(s, 12)
    s[3] ^= k0
    s[4] ^= k1

    plaintext = bytearray()
    offset = 0
    length = len(ciphertext)

    while length >= 8:
        c = struct.unpack(">Q", ciphertext[offset:offset + 8])[0]
        p = s[0] ^ c
        plaintext.extend(struct.pack(">Q", p))
        s[0] = c
        ascon_permutation(s, 6)
        offset += 8
        length -= 8

    last_c = ciphertext[offset:]
    last_out = struct.pack(">Q", s[0])
    for i in range(len(last_c)):
        plaintext.append(last_out[i] ^ last_c[i])

    # Pad & compute tag
    padded = bytearray(last_c) + b"\x80" + b"\x00" * (7 - len(last_c))
    s[0] ^= struct.unpack(">Q", padded)[0]
    s[1] ^= k0
    s[2] ^= k1
    ascon_permutation(s, 12)
    s[3] ^= k0
    s[4] ^= k1

    calculated_tag = struct.pack(">QQ", s[3], s[4])
    if calculated_tag == expected_tag:
        out_name = file_path.replace(".ascon", ".decrypted")
        with open(out_name, "wb") as f:
            f.write(plaintext)
        print(f"✓ SUCCESS: Authentication tag valid. Decrypted to {out_name}")
        return True
    else:
        print("✗ ERROR: Authentication failed. Invalid key or corrupted file.")
        return False


def audit_offline_log():
    if os.path.exists("vault_offline_sync.sql"):
        print("\n" + "=" * 65)
        print("           POSTGRESQL VAULT AUDIT TRAIL LOG           ")
        print("=" * 65)
        with open("vault_offline_sync.sql", "r") as f:
            for line in f:
                print("  " + line.strip())
        print("=" * 65)


if __name__ == "__main__":
    audit_offline_log()