from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import sqlite3
import json
import jwt # PyJWT
from werkzeug.security import generate_password_hash, check_password_hash # For secure passwords

app = Flask(__name__)
CORS(app)

# --- Configuration ---
# Use an environment variable for the secret key in production
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "a-default-secret-key-for-development")

# --- Database Setup ---
# Build the absolute path to the database file. This is more reliable.
backend_dir = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(backend_dir, 'clinic.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Token Verification ---
def verify_token(req):
    """Verifies the JWT token from the Authorization header."""
    header = req.headers.get("Authorization", None)
    if not header:
        raise ValueError("Missing Authorization header")

    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Invalid Authorization format")

    token = parts[1]
    try:
        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def verify_admin(req):
    """Verifies the token and checks if the user is an admin."""
    decoded_token = verify_token(req)
    if not decoded_token.get('is_admin'):
        raise ValueError("Admin access required")
    return decoded_token


@app.route("/")
def home():
    return jsonify({"message": "PGPC backend running"})

# --- Auth Endpoints ---
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    idnumber = data.get("idnumber")
    name = data.get("name")
    password = data.get("password")  # Added password

    if not idnumber or not name or not password:
        return jsonify({"error": "ID number, name, and password are required"}), 400

    db = get_db()
    cursor = db.cursor()

    # Check if it's the first user, make them an admin
    cursor.execute("SELECT id FROM users")
    is_first_user = cursor.fetchone() is None
    is_admin = 1 if is_first_user else 0

    # Hash the password for secure storage
    hashed_password = generate_password_hash(password)

    try:
        # Updated SQL to include password column
        cursor.execute(
            "INSERT INTO users (idnumber, name, password, is_admin) VALUES (?, ?, ?, ?)",
            (idnumber, name, hashed_password, is_admin)
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "ID number already registered"}), 409

    # Automatically log the user in by generating a token
    user_id = cursor.lastrowid
    token = jwt.encode({
        "user_id": user_id,
        "idnumber": idnumber, # Add the idnumber to the token payload
        "is_admin": bool(is_admin),
        "exp": datetime.utcnow() + timedelta(hours=24) # Token validity
    }, app.config["SECRET_KEY"], algorithm="HS256")

    # Return the token along with the success message
    return jsonify({"message": "User registered successfully", "token": token}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request: No JSON data received"}), 400

    idnumber = data.get("idnumber")
    password = data.get("password") # Added password

    if not idnumber or not password:
        return jsonify({"error": "ID number and password are required"}), 400

    cursor = get_db().cursor()
    # Fetch user by ID to get the stored password hash
    cursor.execute("SELECT * FROM users WHERE idnumber = ?", (idnumber,))
    user = cursor.fetchone()

    # Check if user exists AND if the provided password matches the stored hash
    if user and check_password_hash(user["password"], password):
        token = jwt.encode({
            "user_id": user["id"],
            "idnumber": user["idnumber"], # Add the user's ID number to the token
            "is_admin": bool(user["is_admin"]),
            "exp": datetime.utcnow() + timedelta(hours=24) # Token validity
        }, app.config["SECRET_KEY"], algorithm="HS256")
        return jsonify({"token": token})

    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    idnumber = data.get("idnumber")
    if not idnumber:
        return jsonify({"error": "ID number is required"}), 400

    cursor = get_db().cursor()
    cursor.execute("SELECT * FROM users WHERE idnumber = ?", (idnumber,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User with that ID number not found"}), 404

    # Generate a short-lived, single-purpose password reset token
    reset_token = jwt.encode({
        "user_id": user["id"],
        "purpose": "password_reset",
        "exp": datetime.utcnow() + timedelta(minutes=15) # Token is only valid for 15 minutes
    }, app.config["SECRET_KEY"], algorithm="HS256")

    # In a real application, you would email this token to the user.
    # For this demo, we return it directly.
    return jsonify({"reset_token": reset_token})

@app.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        return jsonify({"error": "Token and new password are required"}), 400

    try:
        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        # Security check: ensure this token is for password reset only
        if decoded.get("purpose") != "password_reset":
            return jsonify({"error": "Invalid token type"}), 400
        
        user_id = decoded["user_id"]
        hashed_password = generate_password_hash(new_password)

        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
        db.commit()

        return jsonify({"message": "Password has been reset successfully"})
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return jsonify({"error": f"Invalid or expired token: {e}"}), 401

# --- Admin User Management Endpoints (No change needed) ---
@app.route("/users", methods=["GET"])
def list_users():
    try:
        decoded_token = verify_admin(request)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    search_query = request.args.get('q', None)
    db = get_db()
    cursor = db.cursor()

    if search_query:
        sql = "SELECT id, idnumber, name, is_admin FROM users WHERE idnumber LIKE ? OR name LIKE ? ORDER BY id"
        params = (f'%{search_query}%', f'%{search_query}%')
        cursor.execute(sql, params)
    else:
        sql = "SELECT id, idnumber, name, is_admin FROM users ORDER BY id"
        cursor.execute(sql)

    users = [dict(row) for row in cursor.fetchall()]
    return jsonify(users)

@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user_admin_status(user_id):
    try:
        decoded_token = verify_admin(request)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    data = request.get_json()
    if 'is_admin' not in data:
        return jsonify({"error": "is_admin field is required"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET is_admin = ? WHERE id = ?", (int(data['is_admin']), user_id))
    db.commit()

    return jsonify({"message": "User updated successfully"}), 200

@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        decoded_token = verify_admin(request)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return jsonify({"message": "User deleted successfully"}), 200

# --- Records Endpoints (No change needed) ---
@app.route("/records", methods=["POST"])
def create_record():
    """
    Creates a new student record. Accessible by any authenticated user.
    The record must contain 'idnumber', 'name', 'illness', and 'remarks'.
    """
    try:
        # Any logged-in user can create a record, so we use verify_token.
        decoded_token = verify_token(request)
        uid = decoded_token.get("user_id")
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    payload = request.get_json()
    # Validate that the required fields are in the payload
    required_fields = ["date", "idnumber", "name", "course", "case", "remarks"]
    if not payload or not all(field in payload for field in required_fields):
        return jsonify({"error": f"Missing required fields: {', '.join(required_fields)}"}), 400

    # Construct the data object to be stored
    record_data = {field: payload[field] for field in required_fields}
    createdAt = datetime.utcnow().isoformat()
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO students (data, createdAt, createdBy) VALUES (?, ?, ?)",
                   (json.dumps(record_data), createdAt, uid))
    db.commit()
    
    return jsonify({"id": cursor.lastrowid}), 201


@app.route("/records", methods=["GET"])
def list_records():
    try:
        # Only admins can list all records.
        decoded_token = verify_admin(request)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students ORDER BY createdAt DESC")
    rows = cursor.fetchall()
    
    data = []
    for row in rows:
        item = json.loads(row['data'])
        item['id'] = row['id']
        item['createdAt'] = row['createdAt'] # Add the creation timestamp to the response
        data.append(item)
    return jsonify(data)

@app.route("/my-records", methods=["GET"])
def list_my_records():
    """Fetches all records created by the currently authenticated user."""
    try:
        decoded_token = verify_token(request)
        uid = decoded_token.get("user_id")
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students WHERE createdBy = ? ORDER BY createdAt DESC", (uid,))
    rows = cursor.fetchall()
    
    data = []
    for row in rows:
        item = json.loads(row['data'])
        item['id'] = row['id']
        item['createdAt'] = row['createdAt']
        data.append(item)
    return jsonify(data)

@app.route("/records/<id>", methods=["GET"])
def get_record(id):
    try:
        # Only admins can get a specific record.
        decoded_token = verify_admin(request)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT data FROM students WHERE id = ?", (id,))
    row = cursor.fetchone()

    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(json.loads(row['data']))


@app.route("/records/<id>", methods=["PUT"])
def update_record(id):
    try:
        decoded_token = verify_token(request) # General token verification first
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    payload = request.get_json() or {}
    db = get_db()
    cursor = db.cursor()

    # Security Check: Allow if user is admin OR the owner of the record
    if not decoded_token.get('is_admin'):
        cursor.execute("SELECT createdBy FROM students WHERE id = ?", (id,))
        record = cursor.fetchone()
        if not record:
            return jsonify({"error": "Record not found"}), 404
        if str(record['createdBy']) != str(decoded_token.get('user_id')):
            return jsonify({"error": "Forbidden: You can only edit your own records"}), 403

    # If security check passes, proceed with update
    cursor.execute("UPDATE students SET data = ? WHERE id = ?", (json.dumps(payload), id))
    db.commit()

    return jsonify({"message": "updated"}), 200


@app.route("/records/<id>", methods=["DELETE"])
def delete_record(id):
    try:
        decoded_token = verify_token(request) # General token verification
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    db = get_db()
    cursor = db.cursor()

    # Security Check: Allow if user is admin OR the owner of the record
    if not decoded_token.get('is_admin'):
        cursor.execute("SELECT createdBy FROM students WHERE id = ?", (id,))
        record = cursor.fetchone()
        if not record:
            return jsonify({"error": "Record not found"}), 404
        if str(record['createdBy']) != str(decoded_token.get('user_id')):
            return jsonify({"error": "Forbidden: You can only delete your own records"}), 403

    # If security check passes, proceed with deletion
    cursor.execute("DELETE FROM students WHERE id = ?", (id,))
    db.commit()
    return jsonify({"message": "deleted"}), 200