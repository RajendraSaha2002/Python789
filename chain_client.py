import socket
import json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# CONFIGURATION
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432


def load_private_key(filename):
    with open(filename, "rb") as key_file:
        return serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )


def sign_message(private_key, message):
    """Creates a cryptographic signature for the message."""
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature.hex()


def run_chain_of_command():
    print("--- HEADQUARTERS (COMMAND CENTER) ---")

    # 1. Load Identities
    try:
        pres_key = load_private_key("president_private.pem")
        gen_key = load_private_key("general_private.pem")
    except FileNotFoundError:
        print("Error: Keys not found. Run 'setup_keys.py' first.")
        return

    # 2. The President Issues an Order
    order = "LAUNCH CODE ALPHA-9"
    print(f"\n1. President Issues Order: '{order}'")
    pres_sig = sign_message(pres_key, order)
    print(f"   (Signed by President: {pres_sig[:20]}...)")

    # 3. The General Reviews (and optionally tampers)
    print("\n2. Passing to General...")

    tamper = input(">> SIMULATION: Do you want to Hack/Tamper with the order? (y/n): ").lower()

    final_order_text = order
    if tamper == 'y':
        final_order_text = "LAUNCH CODE BRAVO-6"  # Changed text!
        print(f"   ⚠️ GENERAL TAMPERED WITH ORDER! New text: '{final_order_text}'")
        print("   (Note: The President's signature is still attached to the OLD text)")

    # The General signs whatever text is currently on the paper
    gen_sig = sign_message(gen_key, final_order_text)
    print(f"   (Signed by General: {gen_sig[:20]}...)")

    # 4. Transmit to Silo
    print("\n3. Transmitting to Silo...")

    # We send the (potentially tampered) text, plus the signatures
    payload = {
        "order": final_order_text,
        "president_signature": pres_sig,  # This sig matches "ALPHA-9"
        "general_signature": gen_sig  # This sig matches "BRAVO-6" (if tampered)
    }

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_HOST, SERVER_PORT))
            s.sendall(json.dumps(payload).encode('utf-8'))

            # Wait for Silo response
            response = s.recv(1024)
            print(f"\n[SILO RESPONSE]: {response.decode('utf-8')}")

    except ConnectionRefusedError:
        print("Error: Silo is offline. Run 'silo_server.py' first.")


if __name__ == "__main__":
    run_chain_of_command()