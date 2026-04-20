try:
    import pysqlite3 as sqlite3
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    import sqlite3

# Now, ensure sqlite3 is definitely available to the rest of the script
import sqlite3

import hashlib
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = 'users.db'

@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic cleanup"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = "awaz_e_nisa_salt_2024"  # In production, use a random salt per user
    return hashlib.sha256((password + salt).encode()).hexdigest()

def init_db():
    """Initialize database with all required tables and indexes"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Users Table (enhanced)
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                user_type TEXT DEFAULT 'general'  -- 'general' or 'legal_pro'
            )''')
            
            # Chat History Table (enhanced)
            c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                mode TEXT NOT NULL,
                success_rate REAL,
                merits TEXT,
                demerits TEXT,
                case_category TEXT,
                sentiment_score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )''')
            
            # Sessions Table (new)
            c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                title TEXT DEFAULT 'New Conversation',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                is_archived BOOLEAN DEFAULT 0,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )''')
            
            # Legal Documents Table (new)
            c.execute('''CREATE TABLE IF NOT EXISTS legal_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                document_name TEXT NOT NULL,
                document_type TEXT,  -- 'pdf', 'image', 'text'
                content TEXT,
                extracted_text TEXT,
                case_type TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            )''')
            
            # Feedback Table (new)
            c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                chat_id INTEGER,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                is_helpful BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
                FOREIGN KEY (chat_id) REFERENCES chat_history(id) ON DELETE SET NULL
            )''')
            
            # Case Categories Table (new)
            c.execute('''CREATE TABLE IF NOT EXISTS case_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL,
                description TEXT,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # Insert default case categories
            default_categories = [
                ('Family Law', 'Marriage, divorce, custody, inheritance', 'talaq divorce khula custody inheritance haq mehr'),
                ('Criminal Law', 'Criminal cases and offenses', 'crime theft assault violence'),
                ('Cyber Crime', 'Online harassment and digital crimes', 'cyber harassment online digital fraud'),
                ('Workplace Harassment', 'Harassment at workplace', 'workplace harassment discrimination termination'),
                ('Property Law', 'Property disputes and rights', 'property land inheritance dispute'),
                ('Constitutional Rights', 'Fundamental rights violations', 'rights constitution fundamental')
            ]
            
            for cat in default_categories:
                c.execute('''INSERT OR IGNORE INTO case_categories 
                            (category_name, description, keywords) 
                            VALUES (?, ?, ?)''', cat)
            
            # Create indexes for better performance
            c.execute('CREATE INDEX IF NOT EXISTS idx_chat_username ON chat_history(username)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_history(timestamp)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(username)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_session ON sessions(session_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_docs_user ON legal_documents(username)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(username)')
            
            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def add_user(username: str, password: str, email: str = None, phone: str = None, user_type: str = 'general') -> bool:
    """Add a new user to the database"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            hashed_password = hash_password(password)
            c.execute("""INSERT INTO users (username, password, email, phone, user_type) 
                         VALUES (?, ?, ?, ?, ?)""", 
                      (username, hashed_password, email, phone, user_type))
            logger.info(f"User {username} created successfully")
            return True
    except sqlite3.IntegrityError:
        logger.warning(f"Username {username} already exists")
        return False
    except Exception as e:
        logger.error(f"Error adding user {username}: {e}")
        return False

def verify_user(username: str, password: str) -> bool:
    """Verify user credentials and update last login"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            hashed_password = hash_password(password)
            c.execute("SELECT id FROM users WHERE username = ? AND password = ? AND is_active = 1", 
                     (username, hashed_password))
            user = c.fetchone()
            
            if user:
                # Update last login time
                c.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?", 
                         (username,))
                logger.info(f"User {username} logged in successfully")
                return True
            return False
    except Exception as e:
        logger.error(f"Error verifying user {username}: {e}")
        return False

def save_chat_message(username: str, role: str, content: str, mode: str, 
                     session_id: str = None, case_category: str = None,
                     success_rate: float = None, merits: str = None, 
                     demerits: str = None, sentiment_score: float = None) -> Optional[int]:
    """Save a chat message with enhanced metadata"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Generate session_id if not provided
            if not session_id:
                import uuid
                session_id = str(uuid.uuid4())[:8]
            
            c.execute("""INSERT INTO chat_history 
                         (username, role, content, mode, session_id, case_category, 
                          success_rate, merits, demerits, sentiment_score, timestamp) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""", 
                      (username, role, content, mode, session_id, case_category, 
                       success_rate, merits, demerits, sentiment_score))
            
            chat_id = c.lastrowid
            
            # Update or create session
            c.execute("""INSERT INTO sessions (session_id, username, updated_at, message_count)
                         VALUES (?, ?, CURRENT_TIMESTAMP, 1)
                         ON CONFLICT(session_id) DO UPDATE SET 
                         updated_at = CURRENT_TIMESTAMP,
                         message_count = message_count + 1""",
                      (session_id, username))
            
            logger.info(f"Chat message saved for {username} in session {session_id}")
            return chat_id
            
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        return None

def get_chat_history(username: str, limit: int = 100, session_id: str = None) -> List[Dict]:
    """Get chat history with optional filtering"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            if session_id:
                c.execute("""SELECT role, content, mode, success_rate, merits, demerits, 
                                   case_category, timestamp 
                            FROM chat_history 
                            WHERE username = ? AND session_id = ? 
                            ORDER BY timestamp ASC 
                            LIMIT ?""", 
                         (username, session_id, limit))
            else:
                c.execute("""SELECT role, content, mode, success_rate, merits, demerits, 
                                   case_category, timestamp 
                            FROM chat_history 
                            WHERE username = ? 
                            ORDER BY timestamp ASC 
                            LIMIT ?""", 
                         (username, limit))
            
            rows = c.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Error getting chat history for {username}: {e}")
        return []

def get_user_sessions(username: str) -> List[Dict]:
    """Get all sessions for a user"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""SELECT session_id, title, created_at, updated_at, message_count, is_archived 
                         FROM sessions 
                         WHERE username = ? AND is_archived = 0
                         ORDER BY updated_at DESC""", 
                     (username,))
            rows = c.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Error getting sessions for {username}: {e}")
        return []

def update_session_title(session_id: str, title: str) -> bool:
    """Update session title"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("UPDATE sessions SET title = ? WHERE session_id = ?", 
                     (title, session_id))
            return True
    except Exception as e:
        logger.error(f"Error updating session title: {e}")
        return False

def delete_chat_history(username: str, session_id: str = None) -> bool:
    """Delete chat history for a user or specific session"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            if session_id:
                c.execute("DELETE FROM chat_history WHERE username = ? AND session_id = ?", 
                         (username, session_id))
                c.execute("UPDATE sessions SET is_archived = 1 WHERE session_id = ?", 
                         (session_id,))
                logger.info(f"Deleted session {session_id} for {username}")
            else:
                c.execute("DELETE FROM chat_history WHERE username = ?", (username,))
                c.execute("UPDATE sessions SET is_archived = 1 WHERE username = ?", (username,))
                logger.info(f"Deleted all chat history for {username}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error deleting chat history: {e}")
        return False

def save_feedback(username: str, rating: int, comment: str = None, 
                  chat_id: int = None, is_helpful: bool = None) -> bool:
    """Save user feedback"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO feedback (username, rating, comment, chat_id, is_helpful) 
                         VALUES (?, ?, ?, ?, ?)""",
                      (username, rating, comment, chat_id, is_helpful))
            return True
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        return False

def save_legal_document(username: str, document_name: str, content: str, 
                       extracted_text: str = None, document_type: str = None,
                       case_type: str = None) -> Optional[int]:
    """Save a legal document"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""INSERT INTO legal_documents 
                         (username, document_name, content, extracted_text, document_type, case_type) 
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      (username, document_name, content, extracted_text, document_type, case_type))
            return c.lastrowid
    except Exception as e:
        logger.error(f"Error saving legal document: {e}")
        return None

def get_user_stats(username: str) -> Dict:
    """Get user statistics"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Total chats
            c.execute("SELECT COUNT(*) as total_chats FROM chat_history WHERE username = ?", (username,))
            total_chats = c.fetchone()['total_chats']
            
            # Unique sessions
            c.execute("SELECT COUNT(DISTINCT session_id) as total_sessions FROM chat_history WHERE username = ?", (username,))
            total_sessions = c.fetchone()['total_sessions']
            
            # Last active
            c.execute("SELECT MAX(timestamp) as last_active FROM chat_history WHERE username = ?", (username,))
            last_active = c.fetchone()['last_active']
            
            # Common case categories
            c.execute("""SELECT case_category, COUNT(*) as count 
                         FROM chat_history 
                         WHERE username = ? AND case_category IS NOT NULL
                         GROUP BY case_category 
                         ORDER BY count DESC 
                         LIMIT 5""", (username,))
            common_categories = [dict(row) for row in c.fetchall()]
            
            return {
                'total_chats': total_chats,
                'total_sessions': total_sessions,
                'last_active': last_active,
                'common_categories': common_categories
            }
            
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {}

def search_chat_history(username: str, search_term: str) -> List[Dict]:
    """Search chat history for specific terms"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""SELECT role, content, mode, timestamp 
                         FROM chat_history 
                         WHERE username = ? AND content LIKE ? 
                         ORDER BY timestamp DESC 
                         LIMIT 50""", 
                     (username, f'%{search_term}%'))
            rows = c.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Error searching chat history: {e}")
        return []

# Initialize database when module is imported
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")