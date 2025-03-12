import mysql.connector
from mysql.connector import Error

def connect_to_mysql(host, user, password, database=None, port=3306):
    """
    Établit une connexion à une base de données MySQL distante
    
    Args:
        host (str): Adresse du serveur MySQL
        user (str): Nom d'utilisateur
        password (str): Mot de passe
        database (str, optional): Nom de la base de données
        port (int, optional): Port de connexion MySQL
        
    Returns:
        connection: L'objet connexion si réussi, None sinon
    """
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        print(f"Connexion à MySQL réussie - Version de MySQL: {connection.get_server_info()}")
        
    except Error as err:
        print(f"Erreur: '{err}'")
        connection = None
    
    return connection

def execute_query(connection, query):
    """
    Exécute une requête SQL
    
    Args:
        connection: L'objet connexion MySQL
        query (str): La requête SQL à exécuter
        
    Returns:
        list: Liste des résultats si c'est une requête SELECT, None sinon
    """
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        
        if query.lower().strip().startswith("select"):
            result = cursor.fetchall()
            return result
        
        connection.commit()
        print("Requête exécutée avec succès")
        return None
        
    except Error as err:
        print(f"Erreur: '{err}'")
        return None
    finally:
        cursor.close()

def close_connection(connection):
    """Ferme la connexion à la base de données"""
    if connection:
        connection.close()
        print("Connexion fermée")

# Exemple d'utilisation
if __name__ == "__main__":
    # URL de connexion: mysql://root:EeXtIBwNKhAyySgijzeanMRgNAQifsmZ@maglev.proxy.rlwy.net:40146
    
    # Extraction correcte des informations de l'URL
    config = {
        'host': 'maglev.proxy.rlwy.net',  # Seulement le nom d'hôte
        'user': 'root',
        'password': 'EeXtIBwNKhAyySgijzeanMRgNAQifsmZ',
        'database': 'railway',
        'port': 40146  # Le port doit être un entier
    }
    
    # Établir la connexion
    conn = connect_to_mysql(**config)
    
    if conn:
        # Exemple de requête SELECT
        results = execute_query(conn, "SELECT * FROM tuser LIMIT 5")
        if results:
            print("Résultats:")
            for row in results:
                print(row)
        
        # Fermer la connexion
        close_connection(conn)