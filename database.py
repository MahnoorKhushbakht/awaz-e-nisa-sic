import sqlite3
import hashlib

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    
    # Chat history table with all columns
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  role TEXT NOT NULL,
                  content TEXT NOT NULL,
                  mode TEXT NOT NULL,
                  success_rate TEXT,
                  merits TEXT,
                  demerits TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()    

def verify_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = c.fetchone()
    conn.close()
    return user is not None

def save_chat_message(username, role, content, mode, success_rate=None, merits=None, demerits=None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO chat_history 
                     (username, role, content, mode, success_rate, merits, demerits) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                  (username, role, content, mode, success_rate, merits, demerits))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving chat: {e}")
        return False
    finally:
        conn.close()

def get_chat_history(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role, content, mode, success_rate, merits, demerits FROM chat_history WHERE username = ? ORDER BY timestamp ASC", (username,))
    rows = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1], "mode": row[2], "success_rate": row[3], "merits": row[4], "demerits": row[5]} for row in rows]

def delete_chat_history(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE username = ?", (username,))
    conn.commit()
    conn.close()