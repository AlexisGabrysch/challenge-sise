import mysql.connector
from mysql.connector import Error

def connect_to_mysql(host, user, password, database=None):
    """
    Établit une connexion à une base de données MySQL distante
    
    Args:
        host (str): Adresse du serveur MySQL
        user (str): Nom d'utilisateur
        password (str): Mot de passe
        database (str, optional): Nom de la base de données
        
    Returns:
        connection: L'objet connexion si réussi, None sinon
    """
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
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
    # Remplacez par vos informations de connexion
    config = {
        'host': 'adresse_serveur',
        'user': 'nom_utilisateur',
        'password': 'mot_de_passe',
        'database': 'nom_base_de_donnees'
    }
    
    # Établir la connexion
    conn = connect_to_mysql(**config)
    
    if conn:
        # Exemple de requête SELECT
        results = execute_query(conn, "SELECT * FROM votre_table LIMIT 5")
        if results:
            print("Résultats:")
            for row in results:
                print(row)
        
        # Fermer la connexion
        close_connection(conn)