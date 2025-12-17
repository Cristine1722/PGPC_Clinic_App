import os
import sqlite3
import sys

# Build the absolute path to the database file for reliability
backend_dir = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(backend_dir, 'clinic.db')

def make_admin(idnumber):
    """
    Promotes a user to an admin by their ID number.
    """
    if not idnumber:
        print("Error: Please provide an ID number.")
        print("Usage: python make_admin.py <user_idnumber>")
        return
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # The SQL command to update the user's admin status
        cursor.execute("UPDATE users SET is_admin = 1 WHERE idnumber = ?", (idnumber,))

        if cursor.rowcount == 0:
            print(f"Error: No user found with ID number '{idnumber}'.")
        else:
            conn.commit()
            print(f"Success! User with ID number '{idnumber}' has been promoted to an admin.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Get the ID number from the command-line arguments
    user_idnumber = sys.argv[1] if len(sys.argv) > 1 else None
    make_admin(user_idnumber)