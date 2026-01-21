import psycopg2
import sys

# --- DATABASE CONFIGURATION ---
# UPDATE THIS with your actual PostgreSQL password
DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'varrie75',
    'dbname': 'library_db',
    'port': 5432
}


def get_connection():
    """Establishes a connection to the database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"\n[Error] Could not connect to database: {e}")
        return None


def add_book():
    print("\n--- Add New Book ---")
    title = input("Enter Title: ")
    author = input("Enter Author: ")
    isbn = input("Enter ISBN: ")

    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = "INSERT INTO books (title, author, isbn) VALUES (%s, %s, %s)"
            cursor.execute(query, (title, author, isbn))
            conn.commit()
            print(f"Success! '{title}' added to the library.")
        except psycopg2.IntegrityError:
            print("[Error] A book with this ISBN already exists.")
            conn.rollback()
        except Exception as e:
            print(f"[Error] {e}")
        finally:
            conn.close()


def view_all_books():
    print("\n--- Library Catalog ---")
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, author, isbn FROM books ORDER BY id")
            rows = cursor.fetchall()

            print(f"{'ID':<5} {'Title':<30} {'Author':<20} {'ISBN':<15}")
            print("-" * 75)
            for row in rows:
                print(f"{row[0]:<5} {row[1]:<30} {row[2]:<20} {row[3]:<15}")
            print("-" * 75)
        except Exception as e:
            print(f"[Error] {e}")
        finally:
            conn.close()


def search_by_author():
    print("\n--- Search by Author ---")
    author_name = input("Enter Author Name (partial matches allowed): ")

    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Use % for wildcard matching in SQL
            query = "SELECT id, title, author, isbn FROM books WHERE author ILIKE %s"
            cursor.execute(query, (f"%{author_name}%",))
            rows = cursor.fetchall()

            if rows:
                print(f"\nFound {len(rows)} books:")
                for row in rows:
                    print(f"- {row[1]} (ISBN: {row[3]})")
            else:
                print("No books found for that author.")
        except Exception as e:
            print(f"[Error] {e}")
        finally:
            conn.close()


def delete_book():
    print("\n--- Delete Book ---")
    isbn = input("Enter ISBN of the book to delete: ")

    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Check if book exists first (optional, but good UX)
            cursor.execute("SELECT title FROM books WHERE isbn = %s", (isbn,))
            if cursor.fetchone() is None:
                print("[Error] No book found with that ISBN.")
                return

            # Perform deletion
            cursor.execute("DELETE FROM books WHERE isbn = %s", (isbn,))
            conn.commit()
            print("Book successfully deleted.")
        except Exception as e:
            print(f"[Error] {e}")
        finally:
            conn.close()


def main_menu():
    while True:
        print("\n=== LIBRARY MANAGEMENT SYSTEM ===")
        print("1. View All Books")
        print("2. Add New Book")
        print("3. Search by Author")
        print("4. Delete Book")
        print("5. Exit")

        choice = input("Select an option (1-5): ")

        if choice == '1':
            view_all_books()
        elif choice == '2':
            add_book()
        elif choice == '3':
            search_by_author()
        elif choice == '4':
            delete_book()
        elif choice == '5':
            print("Exiting system. Goodbye!")
            sys.exit()
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main_menu()