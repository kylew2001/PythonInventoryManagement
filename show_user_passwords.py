import sqlite3

# Connect to your SQLite database
conn = sqlite3.connect('database.db')  # Replace with your actual DB path
cursor = conn.cursor()

# Retrieve all users and their password hashes in one query
cursor.execute('SELECT username, password_hash FROM users')
users = cursor.fetchall()

# Display usernames and password hashes
print("Usernames and their password hashes:")
for user in users:
    username, password_hash = user  # Unpacking the tuple into username and password_hash
    print(f"Username: {username} | Password Hash: {password_hash}")

# Close the database connection
conn.close()
