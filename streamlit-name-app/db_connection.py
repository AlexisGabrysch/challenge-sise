import mysql.connector
from mysql.connector import Error

# MySQL connection configuration
DB_CONFIG = {
    'host': 'maglev.proxy.rlwy.net',
    'user': 'root',
    'password': 'EeXtIBwNKhAyySgijzeanMRgNAQifsmZ',
    'database': 'railway',
    'port': 40146
}

def get_mysql_connection():
    """
    Establishes a connection to the MySQL database
    
    Returns:
        connection: The connection object if successful, None otherwise
    """
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def setup_database():
    """
    Sets up the MySQL database tables if they don't exist
    """
    conn = get_mysql_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Create users table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create user_content table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_content (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                section_name VARCHAR(255) NOT NULL,
                content TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, section_name)
            )
            ''')
            
            conn.commit()
            print("Database setup complete!")
        except Error as err:
            print(f"Error setting up database: {err}")
        finally:
            cursor.close()
            conn.close()