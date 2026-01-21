import sounddevice as sd
import numpy as np
import time
import sys

# --- Configuration ---
SAMPLE_RATE = 44100  # CD Quality
DURATION = 5  # Seconds to record
DTYPE = 'int16'  # 16-bit integer (Standard WAV format, best for XOR)


class OTPScrambler:
    def __init__(self):
        self.original_audio = None
        self.key = None
        self.encrypted_audio = None
        self.decrypted_audio = None

    def record(self):
        """Records voice from the microphone."""
        print(f"\n[MIC] Recording for {DURATION} seconds... (Speak Now)")
        try:
            # Record mono audio
            recording = sd.rec(int(DURATION * SAMPLE_RATE),
                               samplerate=SAMPLE_RATE,
                               channels=1,
                               dtype=DTYPE)
            sd.wait()  # Wait until recording is finished
            print("[MIC] Recording Complete.")

            # Flatten to 1D array
            self.original_audio = recording.flatten()

            # Clear previous keys/encryption
            self.key = None
            self.encrypted_audio = None
            self.decrypted_audio = None

        except Exception as e:
            print(f"[ERROR] Microphone access failed: {e}")

    def generate_key(self):
        """Generates a random One-Time Pad key."""
        if self.original_audio is None:
            print("[!] Error: No audio recorded yet.")
            return

        print("\n[KEY] Generating cryptographically secure random key...")
        # Generate random integers covering the full 16-bit range (-32768 to 32767)
        # We match the exact length of the audio recording
        self.key = np.random.randint(-32768, 32768,
                                     size=len(self.original_audio),
                                     dtype=DTYPE)
        print("[KEY] Key Generated.")

    def encrypt(self):
        """Encrypts audio using XOR."""
        if self.original_audio is None:
            print("[!] Record audio first.")
            return
        if self.key is None:
            self.generate_key()

        print("\n[ENC] Encrypting (Audio XOR Key)...")
        # The Math: Cipher = Message XOR Key
        # NumPy handles bitwise XOR on arrays efficiently
        self.encrypted_audio = np.bitwise_xor(self.original_audio, self.key)
        print("[ENC] Encryption Complete. Audio is now white noise.")

    def decrypt(self):
        """Decrypts audio using XOR."""
        if self.encrypted_audio is None:
            print("[!] No encrypted audio found.")
            return

        print("\n[DEC] Decrypting (Cipher XOR Key)...")
        # The Math: Message = Cipher XOR Key
        # Applying XOR twice with the same key restores the original value
        self.decrypted_audio = np.bitwise_xor(self.encrypted_audio, self.key)
        print("[DEC] Decryption Complete. Voice restored.")

    def play(self, audio_type):
        """Plays the specified audio buffer."""
        data = None
        label = ""

        if audio_type == 'original':
            data = self.original_audio
            label = "Original Voice"
        elif audio_type == 'encrypted':
            data = self.encrypted_audio
            label = "Encrypted Static (Ciphertext)"
        elif audio_type == 'decrypted':
            data = self.decrypted_audio
            label = "Decrypted Voice"

        if data is None:
            print(f"[!] {label} is empty.")
            return

        print(f"\n[PLAY] Playing {label}...")
        sd.play(data, SAMPLE_RATE)
        sd.wait()
        print("[PLAY] Done.")


def main():
    app = OTPScrambler()

    while True:
        print("\n--- ONE-TIME PAD VOICE SCRAMBLER ---")
        print("1. Record Voice (5s)")
        print("2. Play Original")
        print("3. Encrypt (Generate Key & XOR)")
        print("4. Play Encrypted (Static)")
        print("5. Decrypt (Restore Voice)")
        print("6. Play Decrypted")
        print("q. Quit")

        choice = input("Select Option: ").lower()

        if choice == '1':
            app.record()
        elif choice == '2':
            app.play('original')
        elif choice == '3':
            app.encrypt()
        elif choice == '4':
            app.play('encrypted')
        elif choice == '5':
            app.decrypt()
        elif choice == '6':
            app.play('decrypted')
        elif choice == 'q':
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()