import sqlite3

# Connect to SQLite database
conn = sqlite3.connect('database.db')
with open('setup.sql', 'r') as f:
    conn.executescript(f.read())

conn.close()
print("Database initialized!")
