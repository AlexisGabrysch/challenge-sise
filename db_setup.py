import sqlite3
import os

def setup_database():
    # Create database directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create user_content table for storing editable sections
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        section_name TEXT NOT NULL,
        content TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, section_name)
    )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database setup complete!")

if __name__ == "__main__":
    setup_database()