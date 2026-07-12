from __future__ import annotations

import math
import secrets
import time
from dataclasses import dataclass


PUBLIC_EXPONENT = 65537
MILLER_RABIN_ROUNDS = 40


def extended_gcd(a: int, b: int) -> tuple[int, int, int]:
    """Return (gcd, x, y) where a*x + b*y == gcd(a, b)."""
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        old_t, t = t, old_t - quotient * t
    return old_r, old_s, old_t


def mod_inverse(value: int, modulus: int) -> int:
    """Return value^-1 mod modulus, or raise ValueError if it does not exist."""
    gcd, coefficient, _ = extended_gcd(value, modulus)
    if gcd != 1:
        raise ValueError("inverse does not exist")
    return coefficient % modulus


def is_probable_prime(candidate: int, rounds: int = MILLER_RABIN_ROUNDS) -> bool:
    """Miller-Rabin probable-prime test with cryptographically random bases."""
    if candidate < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    if candidate in small_primes:
        return True
    if any(candidate % prime == 0 for prime in small_primes):
        return False

    odd_part = candidate - 1
    powers_of_two = 0
    while odd_part % 2 == 0:
        powers_of_two += 1
        odd_part //= 2

    for _ in range(rounds):
        base = secrets.randbelow(candidate - 3) + 2
        witness = pow(base, odd_part, candidate)
        if witness in (1, candidate - 1):
            continue
        for _ in range(powers_of_two - 1):
            witness = pow(witness, 2, candidate)
            if witness == candidate - 1:
                break
        else:
            return False
    return True


def generate_prime(bits: int, exponent: int = PUBLIC_EXPONENT) -> int:
    """Generate a prime with exactly *bits* bits and gcd(p-1, exponent) == 1."""
    if bits < 16:
        raise ValueError("prime size must be at least 16 bits")
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if math.gcd(candidate - 1, exponent) == 1 and is_probable_prime(candidate):
            return candidate


def _i2osp(value: int, length: int) -> bytes:
    if not 0 <= value < (1 << (8 * length)):
        raise ValueError("integer does not fit requested output length")
    return value.to_bytes(length, "big")


def _os2ip(data: bytes) -> int:
    return int.from_bytes(data, "big")


def pkcs1_v1_5_pad(message: bytes, block_size: int) -> bytes:
    """EME-PKCS1-v1_5 encryption encoding: 00 || 02 || PS || 00 || M."""
    if not isinstance(message, bytes):
        raise TypeError("message must be bytes")
    if len(message) > block_size - 11:
        raise ValueError(f"message is too long (maximum is {block_size - 11} bytes)")
    padding_length = block_size - len(message) - 3
    padding = bytearray()
    while len(padding) < padding_length:
        padding.extend(byte for byte in secrets.token_bytes(padding_length - len(padding)) if byte)
    return b"\x00\x02" + bytes(padding[:padding_length]) + b"\x00" + message


def pkcs1_v1_5_unpad(encoded: bytes) -> bytes:
    """Validate and remove EME-PKCS1-v1_5 encryption encoding."""
    # A production implementation must make this check independent of padding
    # validity/timing and avoid exposing a padding oracle.
    if len(encoded) < 11 or encoded[:2] != b"\x00\x02":
        raise ValueError("invalid PKCS#1 v1.5 encoded message")
    try:
        separator = encoded.index(b"\x00", 2)
    except ValueError as error:
        raise ValueError("invalid PKCS#1 v1.5 encoded message") from error
    if separator < 10 or any(byte == 0 for byte in encoded[2:separator]):
        raise ValueError("invalid PKCS#1 v1.5 encoded message")
    return encoded[separator + 1:]


@dataclass(frozen=True)
class RSAPublicKey:
    n: int
    e: int = PUBLIC_EXPONENT

    @property
    def size_bytes(self) -> int:
        return (self.n.bit_length() + 7) // 8

    def encrypt_textbook(self, message: bytes) -> bytes:
        """Raw RSA encryption, deliberately insecure and included only for the attack demo."""
        value = _os2ip(message)
        if value >= self.n:
            raise ValueError("message integer must be smaller than modulus")
        return _i2osp(pow(value, self.e, self.n), self.size_bytes)

    def encrypt(self, message: bytes) -> bytes:
        encoded = pkcs1_v1_5_pad(message, self.size_bytes)
        return _i2osp(pow(_os2ip(encoded), self.e, self.n), self.size_bytes)


@dataclass(frozen=True)
class RSAPrivateKey:
    n: int
    d: int
    p: int
    q: int
    e: int = PUBLIC_EXPONENT

    @property
    def size_bytes(self) -> int:
        return (self.n.bit_length() + 7) // 8

    def decrypt_textbook(self, ciphertext: bytes) -> bytes:
        value = _os2ip(ciphertext)
        if value >= self.n:
            raise ValueError("ciphertext integer must be smaller than modulus")
        # The returned fixed-size representation makes this inverse of the
        # textbook encrypt function; applications must not use textbook RSA.
        return _i2osp(pow(value, self.d, self.n), self.size_bytes)

    def decrypt(self, ciphertext: bytes) -> bytes:
        if len(ciphertext) != self.size_bytes:
            raise ValueError("ciphertext has wrong length")
        encoded = self.decrypt_textbook(ciphertext)
        return pkcs1_v1_5_unpad(encoded)

    def decrypt_crt(self, ciphertext: bytes) -> bytes:
        """PKCS#1 v1.5 decryption using Chinese Remainder Theorem acceleration."""
        if len(ciphertext) != self.size_bytes:
            raise ValueError("ciphertext has wrong length")
        value = _os2ip(ciphertext)
        if value >= self.n:
            raise ValueError("ciphertext integer must be smaller than modulus")
        dp, dq = self.d % (self.p - 1), self.d % (self.q - 1)
        q_inverse = mod_inverse(self.q, self.p)
        m1, m2 = pow(value, dp, self.p), pow(value, dq, self.q)
        encoded = _i2osp((m2 + self.q * ((q_inverse * (m1 - m2)) % self.p)) % self.n, self.size_bytes)
        return pkcs1_v1_5_unpad(encoded)


@dataclass(frozen=True)
class RSAKeyPair:
    public: RSAPublicKey
    private: RSAPrivateKey


def generate_keypair(prime_bits: int = 1024, exponent: int = PUBLIC_EXPONENT) -> RSAKeyPair:
    """Generate RSA keys from two distinct *prime_bits*-bit probable primes."""
    if exponent < 3 or exponent % 2 == 0:
        raise ValueError("public exponent must be odd and at least 3")
    p = generate_prime(prime_bits, exponent)
    q = generate_prime(prime_bits, exponent)
    while q == p:
        q = generate_prime(prime_bits, exponent)
    modulus = p * q
    phi = (p - 1) * (q - 1)
    private_exponent = mod_inverse(exponent, phi)
    return RSAKeyPair(RSAPublicKey(modulus, exponent), RSAPrivateKey(modulus, private_exponent, p, q, exponent))


def textbook_chosen_plaintext_attack(public_key: RSAPublicKey, ciphertext: bytes,
                                     candidate_messages: tuple[bytes, ...]) -> bytes | None:
    """Recover a low-entropy raw-RSA message by encrypting each public guess.

    This succeeds only against deterministic textbook RSA; random PKCS#1 v1.5
    padding prevents matching ciphertexts for the same plaintext.
    """
    for candidate in candidate_messages:
        if public_key.encrypt_textbook(candidate) == ciphertext:
            return candidate
    return None


def timing_comparison(private_key: RSAPrivateKey, ciphertext: bytes, repeats: int = 10) -> tuple[float, float]:
    """Return average milliseconds for normal modular exponentiation and CRT."""
    if repeats < 1:
        raise ValueError("repeats must be positive")
    started = time.perf_counter_ns()
    for _ in range(repeats):
        private_key.decrypt(ciphertext)
    normal_ms = (time.perf_counter_ns() - started) / repeats / 1_000_000
    started = time.perf_counter_ns()
    for _ in range(repeats):
        private_key.decrypt_crt(ciphertext)
    crt_ms = (time.perf_counter_ns() - started) / repeats / 1_000_000
    return normal_ms, crt_ms


if __name__ == "__main__":
    # Use the default 1024-bit primes (approximately a 2048-bit RSA modulus).
    print("Generating RSA key pair from two 1024-bit primes...")
    keys = generate_keypair()
    message = b"Confidential message"
    ciphertext = keys.public.encrypt(message)
    assert keys.private.decrypt(ciphertext) == message
    assert keys.private.decrypt_crt(ciphertext) == message

    # A raw-RSA ciphertext lets an attacker encrypt guesses and compare them.
    guesses = (b"NO", b"YES", b"MAYBE")
    raw_ciphertext = keys.public.encrypt_textbook(b"YES")
    assert textbook_chosen_plaintext_attack(keys.public, raw_ciphertext, guesses) == b"YES"
    assert textbook_chosen_plaintext_attack(keys.public, ciphertext, guesses) is None

    normal, crt = timing_comparison(keys.private, ciphertext)
    print(f"RSA modulus: {keys.public.n.bit_length()} bits")
    print("PKCS#1 v1.5 encryption/decryption passed")
    print("Textbook-RSA chosen-plaintext attack recovered: YES")
    print(f"Average decrypt time: normal={normal:.3f} ms, CRT={crt:.3f} ms")
