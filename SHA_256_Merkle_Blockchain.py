from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Iterable, Sequence


MASK32 = 0xFFFFFFFF
INITIAL_HASH = (
    0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
    0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19,
)
ROUND_CONSTANTS = (
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B,
    0x59F111F1, 0x923F82A4, 0xAB1C5ED5, 0xD807AA98, 0x12835B01,
    0x243185BE, 0x550C7DC3, 0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7,
    0xC19BF174, 0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC,
    0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA, 0x983E5152,
    0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147,
    0x06CA6351, 0x14292967, 0x27B70A85, 0x2E1B2138, 0x4D2C6DFC,
    0x53380D13, 0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
    0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3, 0xD192E819,
    0xD6990624, 0xF40E3585, 0x106AA070, 0x19A4C116, 0x1E376C08,
    0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F,
    0x682E6FF3, 0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
    0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
)


def _rotr(value: int, amount: int) -> int:
    return ((value >> amount) | (value << (32 - amount))) & MASK32


def sha256(data: bytes) -> bytes:
    """Return the SHA-256 digest of *data*, without using hashlib."""
    if not isinstance(data, bytes):
        raise TypeError("sha256 expects bytes")

    bit_length = len(data) * 8
    padded = data + b"\x80"
    padded += b"\x00" * ((56 - len(padded) % 64) % 64)
    padded += struct.pack(">Q", bit_length)
    h = list(INITIAL_HASH)

    for offset in range(0, len(padded), 64):
        words = list(struct.unpack(">16I", padded[offset:offset + 64])) + [0] * 48
        for index in range(16, 64):
            s0 = _rotr(words[index - 15], 7) ^ _rotr(words[index - 15], 18) ^ (words[index - 15] >> 3)
            s1 = _rotr(words[index - 2], 17) ^ _rotr(words[index - 2], 19) ^ (words[index - 2] >> 10)
            words[index] = (words[index - 16] + s0 + words[index - 7] + s1) & MASK32

        a, b, c, d, e, f, g, h_word = h
        for index in range(64):
            s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
            choose = (e & f) ^ (~e & g)
            temp1 = (h_word + s1 + choose + ROUND_CONSTANTS[index] + words[index]) & MASK32
            s0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
            majority = (a & b) ^ (a & c) ^ (b & c)
            temp2 = (s0 + majority) & MASK32
            h_word, g, f, e, d, c, b, a = g, f, e, (d + temp1) & MASK32, c, b, a, (temp1 + temp2) & MASK32
        h = [(value + addition) & MASK32 for value, addition in zip(h, (a, b, c, d, e, f, g, h_word))]

    return struct.pack(">8I", *h)


def _hash_leaf(data: bytes) -> bytes:
    return sha256(b"\x00" + data)


def _hash_branch(left: bytes, right: bytes) -> bytes:
    return sha256(b"\x01" + left + right)


@dataclass(frozen=True)
class MerkleProofStep:
    sibling: bytes
    sibling_is_left: bool


@dataclass(frozen=True)
class MerkleProof:
    leaf: bytes
    index: int
    steps: tuple[MerkleProofStep, ...]


class MerkleTree:
    """Merkle tree that domain-separates leaves from internal branches."""

    def __init__(self, leaves: Sequence[bytes]):
        if not leaves:
            raise ValueError("a Merkle tree needs at least one leaf")
        if any(not isinstance(leaf, bytes) for leaf in leaves):
            raise TypeError("all Merkle leaves must be bytes")
        self.leaves = tuple(leaves)
        level = [_hash_leaf(leaf) for leaf in leaves]
        self.levels: list[tuple[bytes, ...]] = [tuple(level)]
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [_hash_branch(level[i], level[i + 1]) for i in range(0, len(level), 2)]
            self.levels.append(tuple(level))

    @property
    def root(self) -> bytes:
        return self.levels[-1][0]

    def proof(self, index: int) -> MerkleProof:
        if not 0 <= index < len(self.leaves):
            raise IndexError("leaf index is outside the tree")
        original_index = index
        steps: list[MerkleProofStep] = []
        for level in self.levels[:-1]:
            sibling_index = index ^ 1
            sibling = level[sibling_index] if sibling_index < len(level) else level[index]
            steps.append(MerkleProofStep(sibling, sibling_index < index))
            index //= 2
        return MerkleProof(self.leaves[original_index], original_index, tuple(steps))


def verify_merkle_proof(root: bytes, proof: MerkleProof) -> bool:
    """Return True only if *proof* reconstructs the given Merkle root."""
    if not isinstance(root, bytes) or len(root) != 32:
        return False
    current = _hash_leaf(proof.leaf)
    for step in proof.steps:
        if not isinstance(step.sibling, bytes) or len(step.sibling) != 32:
            return False
        current = (_hash_branch(step.sibling, current) if step.sibling_is_left
                   else _hash_branch(current, step.sibling))
    return current == root


def _encode_transactions(transactions: Iterable[bytes]) -> bytes:
    encoded = bytearray()
    for transaction in transactions:
        if not isinstance(transaction, bytes):
            raise TypeError("transactions must be bytes")
        encoded.extend(struct.pack(">I", len(transaction)))
        encoded.extend(transaction)
    return bytes(encoded)


@dataclass
class Block:
    previous_hash: bytes
    transactions: tuple[bytes, ...]
    difficulty: int
    nonce: int = 0
    merkle_root: bytes = field(init=False)

    def __post_init__(self) -> None:
        if len(self.previous_hash) != 32:
            raise ValueError("previous_hash must be 32 bytes")
        if not 0 <= self.difficulty <= 64:
            raise ValueError("difficulty must be between 0 and 64 hexadecimal zeros")
        if not self.transactions:
            raise ValueError("a block needs at least one transaction")
        self.merkle_root = MerkleTree(self.transactions).root

    def header(self) -> bytes:
        return (b"PYCHAIN1" + self.previous_hash + self.merkle_root +
                struct.pack(">IQ", self.difficulty, self.nonce))

    def block_hash(self) -> bytes:
        return sha256(self.header())

    def mine(self) -> bytes:
        """Increase nonce until the block hash starts with difficulty zero hex digits."""
        target_prefix = "0" * self.difficulty
        while True:
            digest = self.block_hash()
            if digest.hex().startswith(target_prefix):
                return digest
            if self.nonce == 0xFFFFFFFFFFFFFFFF:
                raise OverflowError("nonce space exhausted")
            self.nonce += 1

    def is_valid(self, expected_previous_hash: bytes | None = None) -> bool:
        if expected_previous_hash is not None and self.previous_hash != expected_previous_hash:
            return False
        try:
            if self.merkle_root != MerkleTree(self.transactions).root:
                return False
        except (TypeError, ValueError):
            return False
        return self.block_hash().hex().startswith("0" * self.difficulty)


@dataclass
class Blockchain:
    difficulty: int = 3
    blocks: list[Block] = field(default_factory=list)

    def add_block(self, transactions: Sequence[bytes]) -> Block:
        previous = self.blocks[-1].block_hash() if self.blocks else bytes(32)
        block = Block(previous, tuple(transactions), self.difficulty)
        block.mine()
        self.blocks.append(block)
        return block

    def is_valid(self) -> bool:
        previous = bytes(32)
        for block in self.blocks:
            if not block.is_valid(previous):
                return False
            previous = block.block_hash()
        return True


if __name__ == "__main__":
    # SHA-256 official test vector.
    assert sha256(b"abc").hex() == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )

    transactions = (b"Alice pays Bob 3", b"Bob pays Carol 1", b"Carol pays Dave 1")
    tree = MerkleTree(transactions)
    proof = tree.proof(1)
    assert verify_merkle_proof(tree.root, proof)
    assert not verify_merkle_proof(tree.root, MerkleProof(b"altered", proof.index, proof.steps))

    chain = Blockchain(difficulty=3)
    chain.add_block(transactions)
    chain.add_block((b"Dave pays Alice 1",))
    assert chain.is_valid()
    print("SHA-256, Merkle proof, and blockchain self-tests passed")
