import socket
import json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

# CONFIGURATION
HOST = '127.0.0.1'
PORT = 65432


def load_public_key(filename):
    with open(filename, "rb") as key_file:
        return serialization.load_pem_public_key(key_file.read())


def verify_signature(public_key, message, signature_hex):
    """Checks if the signature matches the message using the Public Key."""
    try:
        signature_bytes = bytes.fromhex(signature_hex)
        public_key.verify(
            signature_bytes,
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        print(f"Verification Error: {e}")
        return False


def start_silo():
    print("--- NUCLEAR SILO (LISTENING) ---")

    # 1. Load the Trusted Keys (We only trust the President and General)
    try:
        pres_key = load_public_key("president_public.pem")
        gen_key = load_public_key("general_public.pem")
        print("Trusted Keys Loaded.")
    except FileNotFoundError:
        print("Error: Keys not found. Run 'setup_keys.py' first.")
        return

    # 2. Start Socket Server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Silo active at {HOST}:{PORT}...")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"\nConnection from {addr}")
                data = conn.recv(4096)
                if not data: break

                try:
                    # 3. Parse the Command Bundle
                    payload = json.loads(data.decode('utf-8'))
                    order_text = payload['order']
                    sig_pres = payload['president_signature']
                    sig_gen = payload['general_signature']

                    print(f"Received Order: '{order_text}'")
                    print("Verifying Chain of Command...")

                    # 4. Verification Logic
                    # Layer 1: Check President
                    if verify_signature(pres_key, order_text, sig_pres):
                        print("✅ President's Signature: VALID")
                    else:
                        print("❌ President's Signature: INVALID (Order Tampered!)")
                        conn.sendall(b"REJECTED: President Signature Mismatch")
                        continue

                    # Layer 2: Check General
                    if verify_signature(gen_key, order_text, sig_gen):
                        print("✅ General's Signature:   VALID")
                    else:
                        print("❌ General's Signature:   INVALID")
                        conn.sendall(b"REJECTED: General Signature Mismatch")
                        continue

                    # 5. Execute
                    print("\n>>> AUTHENTICATION CONFIRMED. LAUNCH INITIATED. <<<")
                    conn.sendall(b"ACCEPTED: Launch Sequence Started")

                except json.JSONDecodeError:
                    print("Error: Invalid Data Format")
                except KeyError:
                    print("Error: Missing Signatures")


if __name__ == "__main__":
    start_silo()