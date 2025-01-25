from werkzeug.security import generate_password_hash
import sqlite3

# Define the new password
password_to_hash = "KyleW2001"  # Replace with your new password

# Hash the password using werkzeug's generate_password_hash (this is compatible with check_password_hash)
new_hash = generate_password_hash(password_to_hash)

# Update the database with the new hash
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Update the password for the user "test1"
cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', (new_hash, 'KyleW'))
conn.commit()
conn.close()

print("Password for test1 has been updated.")
