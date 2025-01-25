import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('database.db')  # Replace with your actual database file path
cursor = conn.cursor()

# Query to get the schema of the 'products' table
cursor.execute("PRAGMA table_info(products);")

# Fetch the schema
columns = cursor.fetchall()

# Display the column information
print("Columns in the 'products' table:")
for column in columns:
    print(column)

# Close the connection
conn.close()
