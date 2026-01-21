from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os


def generate_key_pair(filename_prefix):
    """Generates a Private/Public key pair and saves them to files."""
    print(f"Generating identity for: {filename_prefix}...")

    # 1. Generate Private Key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # 2. Save Private Key (The "Unique Password")
    with open(f"{filename_prefix}_private.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # 3. Generate & Save Public Key (For the Silo to verify)
    public_key = private_key.public_key()
    with open(f"{filename_prefix}_public.pem", "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))


if __name__ == "__main__":
    # Create identities for the Chain of Command
    generate_key_pair("president")
    generate_key_pair("general")
    print("\n[SUCCESS] Keys generated. You can now run the Server and Client.")