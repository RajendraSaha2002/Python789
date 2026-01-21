import hashlib
import json
import time
import os


class Block:
    def __init__(self, index, timestamp, shell_id, status, location, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.shell_id = shell_id
        self.status = status  # e.g., "Manufactured", "In Transit", "Fired"
        self.location = location  # e.g., "Factory A", "Truck 101", "Forward Base"
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """Creates a unique fingerprint for this block based on its content."""
        block_string = f"{self.index}{self.timestamp}{self.shell_id}{self.status}{self.location}{self.previous_hash}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "shell_id": self.shell_id,
            "status": self.status,
            "location": self.location,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }


class AmmoLedger:
    def __init__(self, filename="ammo_ledger.json"):
        self.chain = []
        self.filename = filename

        # Load existing chain or start new
        if os.path.exists(filename):
            self.load_chain()
        else:
            self.create_genesis_block()

    def create_genesis_block(self):
        """The first block in the chain."""
        genesis_block = Block(0, time.time(), "GENESIS", "System Init", "Root", "0")
        self.chain.append(genesis_block)
        self.save_chain()

    def get_latest_block(self):
        return self.chain[-1]

    def add_event(self, shell_id, status, location):
        """Adds a new status update to the ledger."""
        prev_block = self.get_latest_block()

        new_block = Block(
            index=prev_block.index + 1,
            timestamp=time.time(),
            shell_id=shell_id,
            status=status,
            location=location,
            previous_hash=prev_block.hash
        )

        self.chain.append(new_block)
        self.save_chain()
        print(f"[SUCCESS] Block #{new_block.index} added. Hash: {new_block.hash[:10]}...")

    def is_chain_valid(self):
        """Checks if the ledger has been tampered with."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # 1. Check if current block's hash is valid
            if current.hash != current.calculate_hash():
                print(f"[ALERT] Data Corruption at Block #{current.index}")
                return False

            # 2. Check if it links correctly to previous block
            if current.previous_hash != previous.hash:
                print(f"[ALERT] Broken Chain at Block #{current.index}")
                return False

        return True

    def get_shell_history(self, shell_id):
        """Filters the chain for a specific shell."""
        history = [b for b in self.chain if b.shell_id == shell_id]
        return history

    def save_chain(self):
        with open(self.filename, 'w') as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=4)

    def load_chain(self):
        with open(self.filename, 'r') as f:
            data = json.load(f)
            self.chain = []
            for item in data:
                b = Block(
                    item['index'], item['timestamp'], item['shell_id'],
                    item['status'], item['location'], item['previous_hash']
                )
                b.hash = item['hash']  # Load the saved hash
                self.chain.append(b)


# --- CLI INTERFACE ---
def main():
    ledger = AmmoLedger()

    while True:
        print("\n--- ARTILLERY AMMO BLOCKCHAIN LEDGER ---")
        print("1. Register/Update Shell Status")
        print("2. Track Shell History")
        print("3. Verify Ledger Integrity")
        print("4. Exit")

        choice = input("Select Option: ")

        if choice == '1':
            sid = input("Shell ID (e.g., SHELL-101): ")
            stat = input("Status (e.g., Manufactured, In Truck, Fired): ")
            loc = input("Location: ")
            ledger.add_event(sid, stat, loc)

        elif choice == '2':
            sid = input("Enter Shell ID to Track: ")
            history = ledger.get_shell_history(sid)
            if not history:
                print("No records found.")
            else:
                print(f"\n--- LIFECYCLE FOR {sid} ---")
                for block in history:
                    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(block.timestamp))
                    print(f"[{ts}] {block.status} @ {block.location}")

        elif choice == '3':
            print("\nVerifying Cryptographic Links...")
            if ledger.is_chain_valid():
                print("✅ LEDGER IS VALID. No tampering detected.")
            else:
                print("❌ LEDGER IS INVALID! Data has been altered.")

        elif choice == '4':
            break


if __name__ == "__main__":
    main()