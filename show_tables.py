import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('database.db')  # Replace with your actual database file path
cursor = conn.cursor()

# Query to get all table names in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

# Fetch all table names
tables = cursor.fetchall()

# Display the table names
print("Tables in the database:")
for table in tables:
    print(table[0])

# Close the connection
conn.close()
