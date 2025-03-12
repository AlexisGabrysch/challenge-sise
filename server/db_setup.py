from connection import connect_to_mysql, execute_query, close_connection

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
            # Create users table
            execute_query(conn, '''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create user_content table
            execute_query(conn, '''
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
            
            print("Database setup complete!")
        finally:
            close_connection(conn)
    else:
        print("Failed to connect to MySQL database")

if __name__ == "__main__":
    setup_database()