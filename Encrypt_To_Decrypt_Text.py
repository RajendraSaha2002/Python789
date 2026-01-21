from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from binascii import b2a_hex
import sys

def main():
    # Get plaintext from args (join to allow spaces) or prompt
    if len(sys.argv) > 1:
        plain_text = " ".join(sys.argv[1:])
    else:
        plain_text = input("Enter plaintext: ")

    # Key must be 16/24/32 bytes (AES-128/192/256)
    key = b"this is a 16 key"  # 16 bytes -> AES-128

    # 16-byte IV for AES block size
    iv = get_random_bytes(16)

    # Encrypt (CFB with 128-bit segment to match full block size)
    cipher = AES.new(key, AES.MODE_CFB, iv=iv, segment_size=128)
    ct = cipher.encrypt(plain_text.encode("utf-8"))

    # Store IV + ciphertext together so we can decrypt later
    packet = iv + ct
    with open("encrypted.bin", "wb") as f:
        f.write(packet)

    # Decrypt (from the in-memory packet; could also read back from file)
    iv2, ct2 = packet[:16], packet[16:]
    decrypt = AES.new(key, AES.MODE_CFB, iv=iv2, segment_size=128)
    decrypted = decrypt.decrypt(ct2).decode("utf-8")

    print("The key k is: ", key)
    print("iv is: ", b2a_hex(iv))
    print("The encrypted data is: ", b2a_hex(ct))
    print("The decrypted data is: ", decrypted)
    print("Saved IV+ciphertext to encrypted.bin")

if __name__ == "__main__":
    main()