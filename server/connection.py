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

def execute_query(connection, query, params=None):
    """
    Exécute une requête SQL
    
    Args:
        connection: L'objet connexion MySQL
        query (str): La requête SQL à exécuter
        params (tuple, optional): Paramètres pour la requête
        
    Returns:
        list: Liste des résultats si c'est une requête SELECT, None sinon
    """
    cursor = connection.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
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