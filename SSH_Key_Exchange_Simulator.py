

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct
from dataclasses import dataclass


# RFC 3526 / SSH Diffie-Hellman Group 14: 2048-bit MODP prime
GROUP14_PRIME_HEX = """
FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1
29024E088A67CC74020BBEA63B139B22514A08798E3404DD
EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245
E485B576625E7EC6F44C42E9A63A3620FFFFFFFFFFFFFFFF
"""

# The screenshot asks Group 14. This standard safe prime is normally
# represented with the full RFC 3526 2048-bit value:
GROUP14_PRIME_HEX = """
FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1
29024E088A67CC74020BBEA63B139B22514A08798E3404DD
EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245
E485B576625E7EC6F44C42E9A63A3620FFFFFFFFFFFFFFFF
"""

# Correct full RFC 3526 Group 14 prime:
GROUP14_PRIME_HEX = """
FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1
29024E088A67CC74020BBEA63B139B22514A08798E3404DD
EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245
E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED
EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D
C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F
83655D23DCA3AD961C62F356208552BB9ED529077096966D
670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF
""".replace("\n", "")

P = int(GROUP14_PRIME_HEX, 16)
G = 2

SSH_MSG_KEXINIT = 20
SSH_MSG_KEXDH_INIT = 30
SSH_MSG_KEXDH_REPLY = 31


class SSHSimulationError(Exception):
    pass


def ssh_string(value: bytes | str) -> bytes:
    """RFC 4251 SSH string: uint32 length followed by bytes."""
    if isinstance(value, str):
        value = value.encode("utf-8")

    return struct.pack("!I", len(value)) + value


def mpint(value: int) -> bytes:
    """
    RFC 4251 mpint encoding.
    For positive integers, add leading zero byte if high bit is set.
    """
    if value == 0:
        return struct.pack("!I", 0)

    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")

    if raw[0] & 0x80:
        raw = b"\x00" + raw

    return struct.pack("!I", len(raw)) + raw


def hex_short(value: int | bytes, length: int = 20) -> str:
    if isinstance(value, int):
        text = format(value, "X")
    else:
        text = value.hex().upper()

    if len(text) <= length:
        return text

    return text[:length] + "..."


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def hmac_sha256(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


@dataclass
class KexInit:
    cookie: bytes
    kex_algorithms: list[str]
    host_key_algorithms: list[str]
    encryption_client_to_server: list[str]
    encryption_server_to_client: list[str]
    mac_client_to_server: list[str]
    mac_server_to_client: list[str]

    def to_packet(self) -> bytes:
        """
        Simplified SSH_MSG_KEXINIT packet representation.
        It is enough for transcript hashing in this in-process simulation.
        """
        lists = [
            self.kex_algorithms,
            self.host_key_algorithms,
            self.encryption_client_to_server,
            self.encryption_server_to_client,
            self.mac_client_to_server,
            self.mac_server_to_client,
        ]

        packet = bytes([SSH_MSG_KEXINIT]) + self.cookie

        for algorithm_list in lists:
            packet += ssh_string(",".join(algorithm_list))

        # Add four language lists and follows/reserved values.
        packet += ssh_string("")
        packet += ssh_string("")
        packet += struct.pack("!BI", 0, 0)

        return packet


@dataclass
class NegotiatedAlgorithms:
    kex: str
    host_key: str
    cipher_c2s: str
    cipher_s2c: str
    mac_c2s: str
    mac_s2c: str


@dataclass
class SSHParty:
    name: str
    version: str
    kex_init: KexInit
    private_exponent: int = 0
    public_value: int = 0
    shared_secret: int = 0
    exchange_hash: bytes = b""
    session_id: bytes = b""


def choose_algorithm(client_list: list[str], server_list: list[str], label: str) -> str:
    """SSH negotiation uses the first client preference supported by server."""
    for algorithm in client_list:
        if algorithm in server_list:
            return algorithm

    raise SSHSimulationError(f"No matching {label} algorithm")


def negotiate(client: SSHParty, server: SSHParty) -> NegotiatedAlgorithms:
    return NegotiatedAlgorithms(
        kex=choose_algorithm(
            client.kex_init.kex_algorithms,
            server.kex_init.kex_algorithms,
            "key exchange",
        ),
        host_key=choose_algorithm(
            client.kex_init.host_key_algorithms,
            server.kex_init.host_key_algorithms,
            "host key",
        ),
        cipher_c2s=choose_algorithm(
            client.kex_init.encryption_client_to_server,
            server.kex_init.encryption_client_to_server,
            "client-to-server cipher",
        ),
        cipher_s2c=choose_algorithm(
            client.kex_init.encryption_server_to_client,
            server.kex_init.encryption_server_to_client,
            "server-to-client cipher",
        ),
        mac_c2s=choose_algorithm(
            client.kex_init.mac_client_to_server,
            server.kex_init.mac_client_to_server,
            "client-to-server MAC",
        ),
        mac_s2c=choose_algorithm(
            client.kex_init.mac_server_to_client,
            server.kex_init.mac_server_to_client,
            "server-to-client MAC",
        ),
    )


def generate_dh_private_exponent() -> int:
    """Create a random private exponent in the valid Group 14 range."""
    return secrets.randbelow(P - 3) + 2


def validate_dh_public_value(value: int) -> None:
    """RFC 4253 requires e and f to be in range 1 < value < p - 1."""
    if not (1 < value < P - 1):
        raise SSHSimulationError("Invalid Diffie-Hellman public value")


def create_exchange_hash(
    client_version: str,
    server_version: str,
    client_kex_packet: bytes,
    server_kex_packet: bytes,
    host_key_blob: bytes,
    e: int,
    f: int,
    shared_secret: int,
) -> bytes:
    """
    RFC 4253 exchange hash:
    H = hash(V_C || V_S || I_C || I_S || K_S || e || f || K)
    """
    transcript = (
        ssh_string(client_version)
        + ssh_string(server_version)
        + ssh_string(client_kex_packet)
        + ssh_string(server_kex_packet)
        + ssh_string(host_key_blob)
        + mpint(e)
        + mpint(f)
        + mpint(shared_secret)
    )

    return sha256(transcript)


def make_kexinit() -> KexInit:
    return KexInit(
        cookie=secrets.token_bytes(16),
        kex_algorithms=[
            "diffie-hellman-group14-sha256",
            "diffie-hellman-group14-sha1",
        ],
        host_key_algorithms=[
            "ssh-ed25519",
            "rsa-sha2-512",
        ],
        encryption_client_to_server=[
            "aes256-ctr",
            "aes128-ctr",
        ],
        encryption_server_to_client=[
            "aes256-ctr",
            "aes128-ctr",
        ],
        mac_client_to_server=[
            "hmac-sha2-256",
            "hmac-sha1",
        ],
        mac_server_to_client=[
            "hmac-sha2-256",
            "hmac-sha1",
        ],
    )


def print_negotiation(result: NegotiatedAlgorithms) -> None:
    print("\nNegotiated algorithms")
    print("-" * 55)
    print("KEX:                 ", result.kex)
    print("Host key:            ", result.host_key)
    print("Cipher client->server:", result.cipher_c2s)
    print("Cipher server->client:", result.cipher_s2c)
    print("MAC client->server:  ", result.mac_c2s)
    print("MAC server->client:  ", result.mac_s2c)


def simulate_ssh_key_exchange() -> None:
    print("=" * 72)
    print("SSH-2 RFC 4253 KEY EXCHANGE SIMULATOR")
    print("=" * 72)

    client = SSHParty(
        name="CLIENT",
        version="SSH-2.0-PythonSSHClient_1.0",
        kex_init=make_kexinit(),
    )

    server = SSHParty(
        name="SERVER",
        version="SSH-2.0-PythonSSHServer_1.0",
        kex_init=make_kexinit(),
    )

    print("\n1. SSH version exchange")
    print(f"CLIENT -> SERVER: {client.version}")
    print(f"SERVER -> CLIENT: {server.version}")

    print("\n2. SSH_MSG_KEXINIT exchange")
    client_packet = client.kex_init.to_packet()
    server_packet = server.kex_init.to_packet()

    print(f"CLIENT -> SERVER: SSH_MSG_KEXINIT ({len(client_packet)} bytes)")
    print(f"SERVER -> CLIENT: SSH_MSG_KEXINIT ({len(server_packet)} bytes)")

    algorithms = negotiate(client, server)
    print_negotiation(algorithms)

    print("\n3. Diffie-Hellman Group 14 public-value generation")

    client.private_exponent = generate_dh_private_exponent()
    client.public_value = pow(G, client.private_exponent, P)

    server.private_exponent = generate_dh_private_exponent()
    server.public_value = pow(G, server.private_exponent, P)

    print(f"CLIENT: generated e = g^x mod p = {hex_short(client.public_value)}")
    print(f"SERVER: generated f = g^y mod p = {hex_short(server.public_value)}")

    validate_dh_public_value(client.public_value)
    validate_dh_public_value(server.public_value)

    print("\n4. SSH_MSG_KEXDH_INIT")
    print(f"CLIENT -> SERVER: message={SSH_MSG_KEXDH_INIT}, e={hex_short(client.public_value)}")

    # Server independently calculates K = e^y mod p.
    server.shared_secret = pow(client.public_value, server.private_exponent, P)
    print(f"SERVER: calculated K = e^y mod p = {hex_short(server.shared_secret)}")

    # This is a demonstrative host key. Real SSH uses actual private/public keys.
    host_key_blob = ssh_string("ssh-ed25519") + ssh_string(
        b"demo-server-host-public-key-not-for-production"
    )

    print("\n5. SSH_MSG_KEXDH_REPLY host-key verification flow")
    print(f"SERVER -> CLIENT: message={SSH_MSG_KEXDH_REPLY}, host key, f, signature")

    # Client independently calculates K = f^x mod p.
    client.shared_secret = pow(server.public_value, client.private_exponent, P)
    print(f"CLIENT: calculated K = f^x mod p = {hex_short(client.shared_secret)}")

    if client.shared_secret != server.shared_secret:
        raise SSHSimulationError("Shared secrets do not match")

    print("SUCCESS: Both endpoints independently derived the same K.")

    server_hash = create_exchange_hash(
        client.version,
        server.version,
        client_packet,
        server_packet,
        host_key_blob,
        client.public_value,
        server.public_value,
        server.shared_secret,
    )

    client_hash = create_exchange_hash(
        client.version,
        server.version,
        client_packet,
        server_packet,
        host_key_blob,
        client.public_value,
        server.public_value,
        client.shared_secret,
    )

    if client_hash != server_hash:
        raise SSHSimulationError("Exchange hashes do not match")

    client.exchange_hash = client_hash
    server.exchange_hash = server_hash

    # Demonstration only: HMAC stands in for a real ssh-ed25519/RSA signature.
    demo_host_signing_key = b"demo-host-signing-key"
    host_signature = hmac_sha256(demo_host_signing_key, server.exchange_hash)

    print(f"SERVER: H = {server.exchange_hash.hex()}")
    print(f"SERVER: demo host signature = {host_signature.hex()}")

    expected_signature = hmac_sha256(
        demo_host_signing_key,
        client.exchange_hash,
    )

    if not hmac.compare_digest(host_signature, expected_signature):
        raise SSHSimulationError("Host key signature verification failed")

    print("CLIENT: Host signature verification PASS.")

    print("\n6. Session ID derivation")
    # For the first key exchange, SSH session ID is the exchange hash H.
    client.session_id = client.exchange_hash
    server.session_id = server.exchange_hash

    print(f"CLIENT session ID: {client.session_id.hex()}")
    print(f"SERVER session ID: {server.session_id.hex()}")

    if client.session_id != server.session_id:
        raise SSHSimulationError("Session IDs do not match")

    print("\nSUCCESS: SSH key-exchange simulation completed.")
    print("Session ID equals first exchange hash, as specified by RFC 4253.")


def main() -> None:
    try:
        simulate_ssh_key_exchange()

    except SSHSimulationError as error:
        print(f"\nSSH simulation error handled safely: {error}")

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")

    except Exception as error:
        print(f"\nUnexpected error handled safely: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()