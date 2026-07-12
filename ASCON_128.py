"""Pure-Python ASCON-128 AEAD (NIST SP 800-232, little-endian variant).

This module uses only the Python standard library.  It supports a 128-bit key,
128-bit nonce and 128-bit authentication tag.  Ciphertexts returned by encrypt
are `encrypted_message || tag`.
"""

from __future__ import annotations

import hmac
import sys
from typing import Final

KEY_SIZE: Final = 16
NONCE_SIZE: Final = 16
TAG_SIZE: Final = 16
RATE: Final = 16
MASK64: Final = (1 << 64) - 1
ASCON_128_IV: Final = 0x00001000808C0001
ROUND_CONSTANTS: Final = (0xF0, 0xE1, 0xD2, 0xC3, 0xB4, 0xA5,
                          0x96, 0x87, 0x78, 0x69, 0x5A, 0x4B)


class InvalidTag(ValueError):
    """Raised when the ciphertext authentication tag is invalid."""


def _u64(data: bytes) -> int:
    return int.from_bytes(data, "little")


def _b64(value: int) -> bytes:
    return (value & MASK64).to_bytes(8, "little")


def _rotr(value: int, amount: int) -> int:
    return ((value >> amount) | (value << (64 - amount))) & MASK64


def _permutation(state: list[int], rounds: int) -> None:
    """Apply the ASCON permutation in place (rounds must be 8 or 12)."""
    if rounds not in (8, 12):
        raise ValueError("ASCON only uses 8 or 12 permutation rounds")

    for constant in ROUND_CONSTANTS[12 - rounds:]:
        x0, x1, x2, x3, x4 = state
        x2 ^= constant

        # Substitution layer, evaluated bit-sliced over all 64 bit positions.
        x0 ^= x4
        x4 ^= x3
        x2 ^= x1
        t0 = (x0 ^ (~x1 & x2)) & MASK64
        t1 = (x1 ^ (~x2 & x3)) & MASK64
        t2 = (x2 ^ (~x3 & x4)) & MASK64
        t3 = (x3 ^ (~x4 & x0)) & MASK64
        t4 = (x4 ^ (~x0 & x1)) & MASK64
        t1 ^= t0
        t0 ^= t4
        t3 ^= t2
        t2 = (~t2) & MASK64
        x0, x1, x2, x3, x4 = t0, t1, t2, t3, t4

        # Linear diffusion layer.
        x0 ^= _rotr(x0, 19) ^ _rotr(x0, 28)
        x1 ^= _rotr(x1, 61) ^ _rotr(x1, 39)
        x2 ^= _rotr(x2, 1) ^ _rotr(x2, 6)
        x3 ^= _rotr(x3, 10) ^ _rotr(x3, 17)
        x4 ^= _rotr(x4, 7) ^ _rotr(x4, 41)
        state[:] = [x0 & MASK64, x1 & MASK64, x2 & MASK64,
                    x3 & MASK64, x4 & MASK64]


def _pad(data: bytes) -> bytes:
    """ASCON's multi-rate padding for its 16-byte rate."""
    return data + b"\x01" + b"\x00" * ((-len(data) - 1) % RATE)


def _xor_rate(state: list[int], block: bytes) -> None:
    state[0] ^= _u64(block[:8])
    state[1] ^= _u64(block[8:])


def _rate_bytes(state: list[int]) -> bytes:
    return _b64(state[0]) + _b64(state[1])


def _initialise(key: bytes, nonce: bytes) -> tuple[list[int], int, int]:
    k0, k1 = _u64(key[:8]), _u64(key[8:])
    n0, n1 = _u64(nonce[:8]), _u64(nonce[8:])
    state = [ASCON_128_IV, k0, k1, n0, n1]
    _permutation(state, 12)
    state[3] ^= k0
    state[4] ^= k1
    return state, k0, k1


def _absorb_ad(state: list[int], associated_data: bytes) -> None:
    if associated_data:
        padded = _pad(associated_data)
        for offset in range(0, len(padded), RATE):
            _xor_rate(state, padded[offset:offset + RATE])
            _permutation(state, 8)
    # DSEP = 0x80 in the most-significant byte of x4 (little-endian standard).
    state[4] ^= 0x8000000000000000


def _finalise(state: list[int], k0: int, k1: int) -> bytes:
    # ASCON-AEAD128 uses the second and third state words here.  This differs
    # from the pre-standardized Ascon-128 construction.
    state[2] ^= k0
    state[3] ^= k1
    _permutation(state, 12)
    state[3] ^= k0
    state[4] ^= k1
    return _b64(state[3]) + _b64(state[4])


def encrypt(key: bytes, nonce: bytes, plaintext: bytes,
            associated_data: bytes = b"") -> bytes:
    """Encrypt and authenticate, returning ciphertext followed by its 16-byte tag."""
    _validate_inputs(key, nonce)
    state, k0, k1 = _initialise(key, nonce)
    _absorb_ad(state, associated_data)

    encrypted = bytearray()
    full = len(plaintext) // RATE
    for index in range(full):
        block = plaintext[index * RATE:(index + 1) * RATE]
        _xor_rate(state, block)
        encrypted.extend(_rate_bytes(state))
        _permutation(state, 8)

    tail = plaintext[full * RATE:]
    _xor_rate(state, _pad(tail))
    encrypted.extend(_rate_bytes(state)[:len(tail)])
    return bytes(encrypted) + _finalise(state, k0, k1)


def decrypt(key: bytes, nonce: bytes, ciphertext_and_tag: bytes,
            associated_data: bytes = b"") -> bytes:
    """Verify and decrypt; raise InvalidTag without returning unauthenticated data."""
    _validate_inputs(key, nonce)
    if len(ciphertext_and_tag) < TAG_SIZE:
        raise InvalidTag("ciphertext is shorter than the authentication tag")

    ciphertext, supplied_tag = (ciphertext_and_tag[:-TAG_SIZE],
                                 ciphertext_and_tag[-TAG_SIZE:])
    state, k0, k1 = _initialise(key, nonce)
    _absorb_ad(state, associated_data)

    plaintext = bytearray()
    full = len(ciphertext) // RATE
    for index in range(full):
        block = ciphertext[index * RATE:(index + 1) * RATE]
        plain_block = bytes(a ^ b for a, b in zip(block, _rate_bytes(state)))
        plaintext.extend(plain_block)
        _xor_rate(state, plain_block)
        _permutation(state, 8)

    tail = ciphertext[full * RATE:]
    rate = _rate_bytes(state)
    plain_tail = bytes(a ^ b for a, b in zip(tail, rate))
    plaintext.extend(plain_tail)
    padded = _pad(plain_tail)
    _xor_rate(state, padded)

    expected_tag = _finalise(state, k0, k1)
    if not hmac.compare_digest(supplied_tag, expected_tag):
        raise InvalidTag("authentication failed")
    return bytes(plaintext)


def _validate_inputs(key: bytes, nonce: bytes) -> None:
    if not isinstance(key, bytes) or len(key) != KEY_SIZE:
        raise ValueError("key must be exactly 16 bytes")
    if not isinstance(nonce, bytes) or len(nonce) != NONCE_SIZE:
        raise ValueError("nonce must be exactly 16 bytes")


def verify_kat_file(path: str) -> int:
    """Verify every case in an official LWC_AEAD_KAT_128_128.txt file.

    The function raises AssertionError at the first failing case and returns the
    number of successfully checked cases otherwise.
    """
    cases: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw_line in open(path, encoding="ascii"):
        line = raw_line.strip()
        if not line:
            if current:
                cases.append(current)
                current = {}
            continue
        name, value = line.split(" = ", 1)
        current[name] = value
    if current:
        cases.append(current)

    for number, case in enumerate(cases, start=1):
        key = bytes.fromhex(case["Key"])
        nonce = bytes.fromhex(case["Nonce"])
        plaintext = bytes.fromhex(case["PT"])
        ad = bytes.fromhex(case["AD"])
        expected = bytes.fromhex(case["CT"])
        actual = encrypt(key, nonce, plaintext, ad)
        if actual != expected or decrypt(key, nonce, actual, ad) != plaintext:
            raise AssertionError(f"KAT case {case.get('Count', number)} failed")
    return len(cases)


if __name__ == "__main__":
    # NIST ASCON-AEAD128 KAT, Count = 1 (empty plaintext and AD).
    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    nonce = bytes.fromhex("101112131415161718191a1b1c1d1e1f")
    expected = bytes.fromhex("4f9c278211bec9316bf68f46ee8b2ec6")
    assert encrypt(key, nonce, b"") == expected
    assert decrypt(key, nonce, expected) == b""

    # Round-trip example.  Never reuse a nonce with the same key.
    sealed = encrypt(key, nonce, b"ASCON-AEAD128 in pure Python", b"metadata")
    assert decrypt(key, nonce, sealed, b"metadata") == b"ASCON-AEAD128 in pure Python"
    print("NIST KAT and round-trip tests passed")
    if len(sys.argv) == 2:
        print(f"Verified {verify_kat_file(sys.argv[1])} cases from {sys.argv[1]}")
    elif len(sys.argv) > 2:
        raise SystemExit(f"Usage: {sys.argv[0]} [LWC_AEAD_KAT_128_128.txt]")
