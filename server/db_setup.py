from connection import connect_to_mysql, execute_query, close_connection
import hashlib
import os

def hash_password(password):
    """Hash a password for storing"""
    salt = os.urandom(32)  # A new salt for this user
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000,  # number of iterations
    )
    return salt.hex() + ':' + key.hex()

def setup_database():
    """
    Sets up the MySQL database tables if they don't exist
    """
    # MySQL connection configuration
    config = {
        'host': 'maglev.proxy.rlwy.net',
        'user': 'root',
        'password': 'EeXtIBwNKhAyySgijzeanMRgNAQifsmZ',
        'database': 'railway',
        'port': 40146
    }
    
    # Connect to MySQL
    conn = connect_to_mysql(**config)
    
    if conn:
        try:
            # Create users table with authentication fields
            execute_query(conn, '''
            CREATE TABLE IF NOT EXISTS users_login_bis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                email VARCHAR(255) UNIQUE,
                password_hash VARCHAR(255),
                is_authenticated BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create user_content table
            execute_query(conn, '''
            CREATE TABLE IF NOT EXISTS users_content_bis (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                section_name VARCHAR(255) NOT NULL,
                content TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_login_bis(id),
                UNIQUE(user_id, section_name)
            )
            ''')

            # Create sessions table
            execute_query(conn, '''
            CREATE TABLE IF NOT EXISTS sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                session_token VARCHAR(255) NOT NULL UNIQUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_login_bis(id)
            )
            ''')
            
            print("Database setup complete!")
        finally:
            close_connection(conn)
    else:
        print("Failed to connect to MySQL database")

if __name__ == "__main__":
    setup_database()