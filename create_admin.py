from werkzeug.security import generate_password_hash
import sqlite3

# Admin credentials
username = "KyleW"
password = "KyleW2001"
hashed_password = generate_password_hash(password)

# Connect to the SQLite database
conn = sqlite3.connect('database.db')
cur = conn.cursor()

# Check if the user already exists
cur.execute("SELECT * FROM users WHERE username = ?", (username,))
existing_user = cur.fetchone()

if existing_user:
    print("User already exists.")
else:
    # Insert the new admin user into the database
    cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, hashed_password, "Admin"))
    conn.commit()
    print(f"Admin user '{username}' created successfully!")

conn.close()
