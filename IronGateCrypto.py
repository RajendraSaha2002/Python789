import psycopg2
from cryptography.fernet import Fernet
import hashlib
import time

# DB CONFIG
DB_CONFIG = {"dbname": "postgres", "user": "postgres", "password": "varrie75", "host": "localhost"}


class SecureTerminal:
    def __init__(self):
        # Generate a key for AES-256
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        print(f"🔒 TERMINAL KEY GENERATED: {self.key.decode()}")

    def encrypt_and_upload(self, title, content, sender):
        try:
            # 1. Encrypt Content
            content_bytes = content.encode('utf-8')
            encrypted_data = self.cipher.encrypt(content_bytes)

            # 2. Calculate Hash (Integrity Check)
            file_hash = hashlib.sha256(encrypted_data).hexdigest()

            # 3. Upload to DB
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()

            # Insert Document
            cur.execute("""
                        INSERT INTO secure_documents (title, sender, encrypted_blob, checksum)
                        VALUES (%s, %s, %s, %s)
                        """, (title, sender, encrypted_data, file_hash))

            # Insert Audit Log
            cur.execute("""
                        INSERT INTO access_logs (user_identity, action_type, status)
                        VALUES (%s, 'UPLOAD_ENCRYPTED', 'SUCCESS')
                        """, (sender,))

            conn.commit()
            conn.close()
            print(f"✅ DOCUMENT UPLOADED: {title} [SHA: {file_hash[:8]}...]")

        except Exception as e:
            print(f"❌ UPLOAD FAILED: {e}")

    def simulate_attack(self):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            print("⚠️ INITIATING NETWORK ATTACK SIMULATION...")
            time.sleep(1)
            # Compromise the Cyber Warfare channel
            cur.execute("UPDATE comm_channels SET status = 'COMPROMISED' WHERE name = 'CYBER-WARFARE-DIV'")
            conn.commit()
            conn.close()
            print("⚠️ ATTACK SUCCESSFUL: CYBER-WARFARE-DIV COMPROMISED")
        except Exception as e:
            print(e)


if __name__ == "__main__":
    terminal = SecureTerminal()

    while True:
        print("\n--- SECURE COMMAND INTERFACE ---")
        print("1. Upload Tactical Order (Alpha)")
        print("2. Upload Nuclear Protocol (Omega)")
        print("3. SIMULATE NETWORK ATTACK (Trigger Alert)")
        print("4. Exit")

        choice = input("Select Action: ")

        if choice == "1":
            terminal.encrypt_and_upload("Operation Blue Sky", "Deploy Squadrons to Sector 9.", "CDS-OFFICE")
        elif choice == "2":
            terminal.encrypt_and_upload("Nuclear Triad Check", "Verify launch codes immediately.", "PMO-OFFICE")
        elif choice == "3":
            terminal.simulate_attack()
        elif choice == "4":
            break