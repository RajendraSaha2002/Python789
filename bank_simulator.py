import psycopg2
import sys
import time

# --- CONFIGURATION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'password',  # <--- UPDATE THIS
    'dbname': 'banking_db',
    'port': 5432
}


def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Connection Error: {e}")
        return None


def view_balances():
    conn = get_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        print("\n--- Current Account Balances ---")
        cur.execute("SELECT account_id, user_name, balance FROM accounts ORDER BY account_id")
        for row in cur.fetchall():
            print(f"ID {row[0]} | {row[1]:<10} | ${row[2]}")
        print("--------------------------------")
    finally:
        conn.close()


def transfer_money(from_id, to_id, amount, simulate_crash=False):
    conn = get_connection()
    if not conn: return

    try:
        # 1. START TRANSACTION
        # In psycopg2, a transaction starts automatically when we create a cursor.
        # We must explicitly commit() or rollback() to end it.
        cur = conn.cursor()

        print(f"\nAttempting transfer: ${amount} from ID {from_id} to ID {to_id}...")

        # 2. CHECK FUNDS (Optional logic, but good practice)
        cur.execute("SELECT balance FROM accounts WHERE account_id = %s", (from_id,))
        result = cur.fetchone()
        if not result:
            print("Error: Sender account not found.")
            return

        current_balance = result[0]
        if current_balance < amount:
            raise ValueError("Insufficient funds!")

        # 3. DEBIT (Take money from Sender)
        print(f"Step 1: Withdrawing ${amount} from Sender...")
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_id = %s", (amount, from_id))

        # --- SIMULATE A CRASH/ERROR ---
        if simulate_crash:
            print("\n!!! SYSTEM CRASHING BEFORE DEPOSIT !!!")
            print("The money has left the Sender, but hasn't reached the Receiver yet.")
            print("Rolling back changes...")
            raise Exception("Simulated Power Failure")

        # 4. CREDIT (Give money to Receiver)
        print(f"Step 2: Depositing ${amount} to Receiver...")
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_id = %s", (amount, to_id))

        # 5. LOGGING
        cur.execute("""
                    INSERT INTO transaction_logs (from_account_id, to_account_id, amount, status)
                    VALUES (%s, %s, %s, 'SUCCESS')
                    """, (from_id, to_id, amount))

        # 6. COMMIT (Save everything permanently)
        conn.commit()
        print(">>> SUCCESS: Transaction Committed. Money transferred safely.")

    except Exception as e:
        # 7. ROLLBACK (Undo everything if ANY error happened)
        conn.rollback()
        print(f">>> FAILED: Transaction Rolled Back. Reason: {e}")
        print("No money was lost. State restored to before the transaction.")

        # Log the failure (Need a new transaction for this since the previous one rolled back)
        try:
            cur.execute("""
                        INSERT INTO transaction_logs (from_account_id, to_account_id, amount, status)
                        VALUES (%s, %s, %s, 'FAILED')
                        """, (from_id, to_id, amount))
            conn.commit()
        except:
            pass

    finally:
        cur.close()
        conn.close()


def main():
    while True:
        print("\n=== BANK TRANSACTION SIMULATOR ===")
        print("1. View Balances")
        print("2. Transfer Money (Safe)")
        print("3. Transfer Money (Simulate Crash/Error)")
        print("4. Exit")

        choice = input("Select an option: ")

        if choice == '1':
            view_balances()
        elif choice == '2':
            try:
                f_id = int(input("From Account ID: "))
                t_id = int(input("To Account ID: "))
                amt = float(input("Amount: "))
                transfer_money(f_id, t_id, amt, simulate_crash=False)
            except ValueError:
                print("Invalid input.")
        elif choice == '3':
            try:
                f_id = int(input("From Account ID: "))
                t_id = int(input("To Account ID: "))
                amt = float(input("Amount: "))
                transfer_money(f_id, t_id, amt, simulate_crash=True)
            except ValueError:
                print("Invalid input.")
        elif choice == '4':
            sys.exit()


if __name__ == "__main__":
    main()