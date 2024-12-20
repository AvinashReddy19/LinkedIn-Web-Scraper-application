import sqlite3

def display_profiles():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('linkedin_profiles.db')  # Replace with your database file
        cursor = conn.cursor()

        # Execute the SELECT query
        cursor.execute('SELECT * FROM Profiles')

        # Fetch all rows from the executed query
        rows = cursor.fetchall()

        # Get column names from cursor description
        column_names = [description[0] for description in cursor.description]
        print(column_names)

        # Display each row
        for row in rows:
            print(row)

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Call the function to display profiles
display_profiles()
