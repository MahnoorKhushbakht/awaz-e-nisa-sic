import sqlite3

def update_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
   
    try:
        c.execute("ALTER TABLE chat_history ADD COLUMN success_rate TEXT")
        c.execute("ALTER TABLE chat_history ADD COLUMN merits TEXT")
        c.execute("ALTER TABLE chat_history ADD COLUMN demerits TEXT")
        conn.commit()
        print("Database successfully updated with new columns!")
    except sqlite3.OperationalError:
        print("Columns already exist or table not found.")
    
    conn.close()

if __name__ == "__main__":
    update_database()