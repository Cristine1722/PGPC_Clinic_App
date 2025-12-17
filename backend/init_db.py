import sqlite3
import os

DATABASE_FILENAME = 'clinic.db'

def initialize_database():
    """
    Connects to the database (creating it if it doesn't exist)
    and sets up the necessary tables. This script is safe to run
    multiple times.
    """
    # Get the absolute path to the directory this script is in
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(backend_dir, DATABASE_FILENAME)

    try:
        print(f"Initializing database at '{db_path}'...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create 'students' table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                createdAt TEXT NOT NULL,
                createdBy TEXT NOT NULL
            )''')
        print("- 'students' table is ready.")

        # Create 'users' table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                idnumber TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password TEXT NOT NULL,
                is_admin BOOLEAN NOT NULL DEFAULT 0
            )''')
        print("- 'users' table is ready.")

        conn.commit()
        print("\nDatabase initialized successfully.")

    except sqlite3.Error as e:
        print(f"\nAn error occurred during database initialization: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    initialize_database()