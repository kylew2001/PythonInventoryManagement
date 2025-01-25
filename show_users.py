import sqlite3

try:
    # Connect to the SQLite database
    conn = sqlite3.connect('database.db')

    # Create a cursor object
    cur = conn.cursor()

    # Execute a query to fetch all users
    cur.execute('SELECT * FROM users')

    # Fetch all rows from the executed query
    users = cur.fetchall()

    # Check if there are any users
    if users:
        for user in users:
            print(user)
    else:
        print("No users found.")

except sqlite3.Error as e:
    print("Error occurred while fetching users:", e)

finally:
    # Close the connection
    conn.close()
