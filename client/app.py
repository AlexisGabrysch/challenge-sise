import streamlit as st
from streamlit.components.v1 import html
import os
import sys
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

# API URL configuration
SERVER_URL = os.getenv("SERVER_URL", "https://challenge-sise-production.up.railway.app")
CLIENT_URL = os.getenv("CLIENT_URL", "https://challenge-sise-client.up.railway.app")

def connect_to_mysql(host, user, password, database=None, port=3306):
    """
    Établit une connexion à une base de données MySQL distante
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

def main():
    # Initialize MySQL connection at startup
    if 'mysql_connection' not in st.session_state:
        conn = connect_to_mysql(**DB_CONFIG)
        if conn:
            st.session_state.mysql_connection = conn
            st.success("Connected to MySQL database")
        else:
            st.error("Failed to connect to MySQL database")
    
    # Check if we are on a user page
    query_params = st.query_params
    if "name" in query_params:
        user_name = query_params["name"]
        show_user_page(user_name)
    else:
        show_main_page()

def show_main_page():
    st.title("Personalized Page Creator")
    
    first_name = st.text_input("Enter your first name:")
    
    if st.button("Create Your Page"):
        if first_name:
            # Store the name in session state
            st.session_state.user_name = first_name
            
            # Create user page URL using the SERVER URL - changed from /users/ to /user/
            user_url = f"{SERVER_URL}/user/{first_name}"
            
            st.success(f"Your personal page has been created!")
            st.markdown(f"[Visit your page]({user_url})")
            
            # Alternatively, use JS to redirect
            if st.button("Go to page now"):
                redirect_js = f"""
                    <script>
                    window.location.href = "{user_url}";
                    </script>
                """
                html(redirect_js)
        else:
            st.error("Please enter a name.")

def show_user_page(user_name):
    st.title(f"Welcome to your page, {user_name}!")
    st.write(f"This is your personalized page.")
    st.balloons()
    
    # Changed from /users/ to /user/
    user_url = f"{SERVER_URL}/user/{user_name}"
    st.markdown(f"[Visit your custom page with editable sections]({user_url})")
    
    if st.button("Return to Main Page"):
        redirect_js = f"""
            <script>
            window.location.href = "{CLIENT_URL}";
            </script>
        """
        html(redirect_js)

# Close MySQL connection when the app exits
def on_shutdown():
    if 'mysql_connection' in st.session_state:
        try:
            st.session_state.mysql_connection.close()
            print("MySQL connection closed")
        except Exception as e:
            print(f"Error closing MySQL connection: {e}")

if __name__ == "__main__":
    main()
    # Register shutdown hook
    import atexit
    atexit.register(on_shutdown)