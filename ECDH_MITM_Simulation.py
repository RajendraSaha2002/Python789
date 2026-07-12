from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


def inverse_mod(value: int, modulus: int) -> int:
    """Return a modular inverse using the extended Euclidean algorithm."""
    value %= modulus
    if value == 0:
        raise ZeroDivisionError("zero does not have a modular inverse")
    old_r, r = value, modulus
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
    if old_r != 1:
        raise ValueError("value is not invertible")
    return old_s % modulus


@dataclass(frozen=True)
class Point:
    x: int
    y: int


Infinity = Optional[Point]


@dataclass(frozen=True)
class Curve:
    name: str
    p: int
    a: int
    b: int
    generator: Point
    order: int

    def is_on_curve(self, point: Infinity) -> bool:
        if point is None:
            return True
        return (point.y * point.y - (point.x ** 3 + self.a * point.x + self.b)) % self.p == 0

    def negate(self, point: Infinity) -> Infinity:
        if point is None:
            return None
        self._require_point(point)
        return Point(point.x, (-point.y) % self.p)

    def add(self, first: Infinity, second: Infinity) -> Infinity:
        """Elliptic-curve point addition, including doubling and infinity."""
        if first is None:
            return second
        if second is None:
            return first
        self._require_point(first)
        self._require_point(second)

        if first.x == second.x and (first.y + second.y) % self.p == 0:
            return None
        if first == second:
            if first.y == 0:
                return None
            slope = (3 * first.x * first.x + self.a) * inverse_mod(2 * first.y, self.p)
        else:
            slope = (second.y - first.y) * inverse_mod(second.x - first.x, self.p)
        slope %= self.p
        x3 = (slope * slope - first.x - second.x) % self.p
        y3 = (slope * (first.x - x3) - first.y) % self.p
        return Point(x3, y3)

    def multiply(self, scalar: int, point: Infinity = None) -> Infinity:
        """Double-and-add scalar multiplication; negative scalars are allowed."""
        if point is None:
            point = self.generator
        self._require_point(point)
        if scalar < 0:
            return self.multiply(-scalar, self.negate(point))
        result: Infinity = None
        addend: Infinity = point
        while scalar:
            if scalar & 1:
                result = self.add(result, addend)
            addend = self.add(addend, addend)
            scalar >>= 1
        return result

    def _require_point(self, point: Point) -> None:
        if not self.is_on_curve(point):
            raise ValueError("point is not on this curve")


# The generator has prime order 19, so every nonzero scalar modulo 19 is valid.
TOY_CURVE_17 = Curve("ToyCurve17", p=17, a=2, b=2, generator=Point(5, 1), order=19)


def _encode_point(point: Point) -> bytes:
    return bytes((point.x, point.y))


def _challenge(data: bytes, order: int) -> int:
    """Small integer hash for this toy demonstration only; not cryptographic."""
    state = 0
    for byte in data:
        state = (state * 257 + byte) % order
    return state


@dataclass(frozen=True)
class Signature:
    commitment: Point
    response: int


@dataclass(frozen=True)
class Identity:
    """Long-term signing identity; secret must remain private in real systems."""
    name: str
    signing_secret: int
    curve: Curve = TOY_CURVE_17

    def __post_init__(self) -> None:
        if not 1 <= self.signing_secret < self.curve.order:
            raise ValueError("signing secret must be in [1, order-1]")

    @property
    def signing_public(self) -> Point:
        point = self.curve.multiply(self.signing_secret)
        assert point is not None
        return point

    def sign(self, message: bytes, nonce: int) -> Signature:
        """Create an illustrative Schnorr signature over a public ECDH key."""
        if not 1 <= nonce < self.curve.order:
            raise ValueError("signature nonce must be in [1, order-1]")
        commitment = self.curve.multiply(nonce)
        assert commitment is not None
        challenge = _challenge(_encode_point(commitment) + _encode_point(self.signing_public) + message,
                               self.curve.order)
        return Signature(commitment, (nonce + challenge * self.signing_secret) % self.curve.order)


def verify_signature(curve: Curve, public_key: Point, message: bytes, signature: Signature) -> bool:
    """Verify the Schnorr relation sG == R + H(R || P || message)P."""
    try:
        curve._require_point(public_key)
        curve._require_point(signature.commitment)
    except ValueError:
        return False
    if not 0 <= signature.response < curve.order:
        return False
    challenge = _challenge(_encode_point(signature.commitment) + _encode_point(public_key) + message,
                           curve.order)
    return curve.multiply(signature.response) == curve.add(
        signature.commitment, curve.multiply(challenge, public_key)
    )


@dataclass(frozen=True)
class EphemeralKey:
    secret: int
    curve: Curve = TOY_CURVE_17

    def __post_init__(self) -> None:
        if not 1 <= self.secret < self.curve.order:
            raise ValueError("ECDH secret must be in [1, order-1]")

    @property
    def public(self) -> Point:
        point = self.curve.multiply(self.secret)
        assert point is not None
        return point

    def shared_secret(self, peer_public: Point) -> Point:
        self.curve._require_point(peer_public)
        shared = self.curve.multiply(self.secret, peer_public)
        if shared is None:
            raise ValueError("invalid peer public key produced infinity")
        return shared


def signed_ephemeral_message(sender: str, recipient: str, public_key: Point) -> bytes:
    """Bind sender, recipient, and the ECDH public key into the signed message."""
    return sender.encode("ascii") + b"->" + recipient.encode("ascii") + b":" + _encode_point(public_key)


def run_demo() -> None:
    curve = TOY_CURVE_17
    alice_id = Identity("Alice", signing_secret=3)
    bob_id = Identity("Bob", signing_secret=8)
    alice_ecdh, bob_ecdh, mallory_ecdh = EphemeralKey(5), EphemeralKey(7), EphemeralKey(11)

    # Honest ECDH: both sides obtain the same point a*b*G.
    honest_alice = alice_ecdh.shared_secret(bob_ecdh.public)
    honest_bob = bob_ecdh.shared_secret(alice_ecdh.public)
    assert honest_alice == honest_bob

    # MITM: Mallory replaces each public key with her own, producing two keys.
    alice_with_mallory = alice_ecdh.shared_secret(mallory_ecdh.public)
    bob_with_mallory = bob_ecdh.shared_secret(mallory_ecdh.public)
    mallory_with_alice = mallory_ecdh.shared_secret(alice_ecdh.public)
    mallory_with_bob = mallory_ecdh.shared_secret(bob_ecdh.public)
    assert alice_with_mallory == mallory_with_alice
    assert bob_with_mallory == mallory_with_bob
    assert alice_with_mallory != bob_with_mallory

    # Alice signs the ECDH key intended for Bob. Mallory cannot replace that
    # public key and retain a valid Alice signature.
    alice_message = signed_ephemeral_message("Alice", "Bob", alice_ecdh.public)
    signature = alice_id.sign(alice_message, nonce=4)
    assert verify_signature(curve, alice_id.signing_public, alice_message, signature)
    replaced_message = signed_ephemeral_message("Alice", "Bob", mallory_ecdh.public)
    assert not verify_signature(curve, alice_id.signing_public, replaced_message, signature)

    # Bob likewise signs his own ECDH key for Alice.
    bob_message = signed_ephemeral_message("Bob", "Alice", bob_ecdh.public)
    assert verify_signature(curve, bob_id.signing_public, bob_message, bob_id.sign(bob_message, nonce=6))

    print(f"Curve: {curve.name}; generator order: {curve.order}")
    print(f"Honest ECDH shared point: {honest_alice}")
    print(f"MITM created Alice-Mallory key: {alice_with_mallory}")
    print(f"MITM created Bob-Mallory key:   {bob_with_mallory}")
    print("Signed ECDH key verification rejects Mallory's substituted key.")


if __name__ == "__main__":
    run_demo()
