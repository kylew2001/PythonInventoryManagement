import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Fetch the user and their password hash
cursor.execute('SELECT username, password_hash FROM users WHERE username = "KyleW"')
user = cursor.fetchone()
conn.close()

if user:
    print(f"Username: {user[0]}")
    print(f"Password Hash: {user[1]}")
else:
    print("User not found.")
