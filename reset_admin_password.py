import sqlite3
from werkzeug.security import generate_password_hash

# Connect to your SQLite database
conn = sqlite3.connect('database.db')  # Replace with your actual DB path
cursor = conn.cursor()

# Define the username and the new password
username = 'KyleW'
new_password = 'KyleW2001'  # Change this to the desired new password

# Hash the new password
hashed_password = generate_password_hash(new_password)

# Update the password for the specified admin user
cursor.execute('''
    UPDATE users 
    SET password_hash = ? 
    WHERE username = ? 
''', (hashed_password, username))

# Commit the changes and close the connection
conn.commit()
conn.close()

print(f"Password for {username} has been updated successfully.")
