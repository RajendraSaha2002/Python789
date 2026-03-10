import psycopg2
from cryptography.fernet import Fernet


# ==============================
# DATABASE CONNECTION
# ==============================

def connect_db():
    conn = psycopg2.connect(
        dbname="cipher_stream",
        user="postgres",
        password="varrie75",
        host="localhost",
        port="5432"
    )
    return conn


# ==============================
# ENCRYPTION SYSTEM
# ==============================

KEY = Fernet.generate_key()
cipher = Fernet(KEY)


def encrypt_document(data: bytes) -> bytes:
    encrypted = cipher.encrypt(data)
    return encrypted


def decrypt_document(data: bytes) -> bytes:
    decrypted = cipher.decrypt(data)
    return decrypted


# ==============================
# DOCUMENT CLEARANCE SYSTEM
# ==============================

def fetch_document(user_id, doc_id):

    conn = connect_db()
    cur = conn.cursor()

    # get user clearance
    cur.execute("SELECT clearance_level FROM users WHERE user_id=%s", (user_id,))
    clearance = cur.fetchone()[0]

    # apply PostgreSQL RLS clearance
    cur.execute("SET app.current_clearance = %s", (clearance,))

    # fetch encrypted document
    cur.execute("""
        SELECT encrypted_data
        FROM documents
        WHERE doc_id = %s
    """, (doc_id,))

    result = cur.fetchone()

    if result:
        decrypted = decrypt_document(result[0])
        return decrypted.decode()

    return "ACCESS DENIED"


# ==============================
# AUDIT LOG SYSTEM
# ==============================

def log_access(user_id, doc_id):

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tamper_proof_audit(user_id, doc_id, action)
        VALUES(%s,%s,'VIEW')
    """, (user_id, doc_id))

    conn.commit()


# ==============================
# SERVER TEST RUN
# ==============================

if __name__ == "__main__":

    user_id = 1
    doc_id = 1

    document = fetch_document(user_id, doc_id)

    print("\n===== CLASSIFIED DOCUMENT =====\n")
    print(document)

    log_access(user_id, doc_id)

    print("\nAudit log recorded.")