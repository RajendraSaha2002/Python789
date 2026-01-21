from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from binascii import b2a_hex
import sys

def main():
    if len(sys.argv) > 1:
        plain_text = " ".join(sys.argv[1:])
    else:
        plain_text = input("Enter plaintext: ")

    key = get_random_bytes(32)  # AES-256
    cipher = AES.new(key, AES.MODE_GCM)  # GCM is authenticated
    ct, tag = cipher.encrypt_and_digest(plain_text.encode("utf-8"))

    # Store nonce + tag + ciphertext
    packet = cipher.nonce + tag + ct
    with open("encrypted_gcm.bin", "wb") as f:
        f.write(packet)

    # Decrypt
    nonce, tag2, ct2 = packet[:16], packet[16:32], packet[32:]
    decrypt = AES.new(key, AES.MODE_GCM, nonce=nonce)
    decrypted = decrypt.decrypt_and_verify(ct2, tag2).decode("utf-8")

    print("Key: ", b2a_hex(key))
    print("Nonce: ", b2a_hex(nonce))
    print("Tag: ", b2a_hex(tag))
    print("Ciphertext: ", b2a_hex(ct))
    print("Decrypted: ", decrypted)
    print("Saved nonce+tag+ciphertext to encrypted_gcm.bin")

if __name__ == "__main__":
    main()