import streamlit as st
from streamlit.components.v1 import html
import os
import sys
import mysql.connector
from mysql.connector import Error
import requests
import json
from typing import Optional, Dict, Any

# Configuration URLs
SERVER_URL = os.getenv("SERVER_URL", "https://challenge-sise-production-0bc4.up.railway.app")

# Définir les pages de l'application
PAGE_LOGIN = "login"
PAGE_REGISTER = "register"
PAGE_USER_PROFILE = "profile"
PAGE_EDIT_CV = "edit_cv"
PAGE_VIEW_CV = "view_cv"

# Initialiser l'état de session
if "page" not in st.session_state:
    st.session_state.page = PAGE_LOGIN

if "user" not in st.session_state:
    st.session_state.user = None

if "session_token" not in st.session_state:
    st.session_state.session_token = None

def set_page(page: str):
    """Change la page actuelle"""
    st.session_state.page = page
    st.rerun()

def login(email: str, password: str) -> bool:
    """Authentifie l'utilisateur avec le serveur API"""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/login",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.user = {
                "id": data["id"],
                "name": data["name"],
                "email": data["email"]
            }
            st.session_state.session_token = data["session_token"]
            # Ajouter cette ligne pour rediriger vers le CV après login
            st.markdown(f"""
            <meta http-equiv="refresh" content="1; url={SERVER_URL}/user/{data['name']}">
            <p>Login successful! Redirecting to your CV...</p>
            """, unsafe_allow_html=True)
            return True
        return False
    except Exception as e:
        st.error(f"Error connecting to server: {e}")
        return False

def register(name: str, email: str, password: str) -> bool:
    """Crée un nouvel utilisateur sur le serveur API"""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/register",
            json={"name": name, "email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.user = {
                "id": data["id"],
                "name": data["name"],
                "email": data["email"]
            }
            st.session_state.session_token = data["session_token"]
            return True
        else:
            st.error(f"Registration failed: {response.json().get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        st.error(f"Error connecting to server: {e}")
        return False

def logout():
    """Déconnecte l'utilisateur"""
    st.session_state.user = None
    st.session_state.session_token = None
    st.session_state.page = PAGE_LOGIN
    
def get_cv_data(username: str) -> Optional[Dict[str, Any]]:
    """Récupère les données du CV depuis l'API"""
    try:
        response = requests.get(
            f"{SERVER_URL}/api/cv/{username}",
            headers={"Authorization": f"Bearer {st.session_state.session_token}"} if st.session_state.session_token else {}
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error retrieving CV data: {e}")
        return None

def update_cv_section(username: str, section: str, content: str) -> bool:
    """Met à jour une section du CV via l'API"""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/cv/{username}/update",
            headers={"Authorization": f"Bearer {st.session_state.session_token}"},
            json={"section": section, "content": content}
        )
        
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error updating CV section: {e}")
        return False

# Ajouter cette fonction pour afficher un lien vers la version publique du CV
def show_public_cv_link(username: str):
    public_cv_url = f"{SERVER_URL}/user/{username}"
    st.markdown("""
    <div style="margin-top: 30px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; text-align: center;">
        <p>Share your public CV:</p>
        <a href="{}" target="_blank" style="text-decoration: none;">
            <div style="display: inline-block; padding: 10px 20px; background-color: #4285F4; color: white; border-radius: 5px; font-weight: bold;">
                View Public CV
            </div>
        </a>
        <p style="margin-top: 10px; font-size: 12px; color: #888;">
            This link can be shared with anyone, even if they don't have an account.
        </p>
    </div>
    """.format(public_cv_url), unsafe_allow_html=True)

def show_login_page():
    st.title("Login")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if login(email, password):
                st.session_state.page = PAGE_USER_PROFILE
                st.rerun()
            else:
                st.error("Invalid email or password")
    
    st.write("Don't have an account?")
    if st.button("Register", key="register_btn_login"):
        st.session_state.page = PAGE_REGISTER
        st.rerun()

def show_register_page():
    st.title("Register")
    
    with st.form("register_form"):
        name = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")
        
        if submit:
            if password != password_confirm:
                st.error("Passwords do not match")
            elif not name or not email or not password:
                st.error("All fields are required")
            else:
                if register(name, email, password):
                    st.session_state.page = PAGE_USER_PROFILE
                    st.rerun()
    
    st.write("Already have an account?")
    if st.button("Login", key="login_btn_register"):
        st.session_state.page = PAGE_LOGIN
        st.rerun()

def show_user_profile():
    if not st.session_state.user:
        st.session_state.page = PAGE_LOGIN
        st.rerun()
        
    st.title(f"Welcome, {st.session_state.user['name']}!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("View My CV", key="view_cv_btn_profile"):
            st.session_state.page = PAGE_VIEW_CV
            st.rerun()
    
    with col2:
        if st.button("Edit My CV", key="edit_cv_btn_profile"):
            st.session_state.page = PAGE_EDIT_CV
            st.rerun()
    
    # Ajouter le lien vers le CV public
    show_public_cv_link(st.session_state.user["name"])
    
    if st.button("Logout", key="logout_btn_profile"):
        logout()
        st.rerun()

def show_view_cv():
    if not st.session_state.user:
        st.session_state.page = PAGE_LOGIN
        st.rerun()
    
    username = st.session_state.user["name"]
    st.title(f"{username}'s CV")
    
    cv_data = get_cv_data(username)
    
    if not cv_data:
        st.warning("CV data could not be loaded")
    else:
        st.header(cv_data.get("header", f"Welcome to {username}'s CV"))
        
        st.subheader("About")
        st.write(cv_data.get("section1", "No information available"))
        
        st.subheader("Additional Information")
        st.write(cv_data.get("section2", "No information available"))
    
    # Ajouter le lien vers le CV public
    show_public_cv_link(username)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Back to Profile", key="back_to_profile_btn_view"):
            st.session_state.page = PAGE_USER_PROFILE
            st.rerun()
    
    with col2:
        if st.button("Edit CV", key="edit_cv_btn_view"):
            st.session_state.page = PAGE_EDIT_CV
            st.rerun()

def show_edit_cv():
    if not st.session_state.user:
        st.session_state.page = PAGE_LOGIN
        st.rerun()
    
    username = st.session_state.user["name"]
    st.title(f"Edit {username}'s CV")
    
    cv_data = get_cv_data(username)
    
    if not cv_data:
        st.warning("CV data could not be loaded")
        if st.button("Back to Profile", key="back_to_profile_btn_edit_error"):
            st.session_state.page = PAGE_USER_PROFILE
            st.rerun()
        return
    
    with st.form("edit_header_form"):
        st.subheader("Header")
        header = st.text_input("Header", value=cv_data.get("header", f"Welcome to {username}'s CV"))
        submit_header = st.form_submit_button("Update Header")
        
        if submit_header:
            if update_cv_section(username, "header", header):
                st.success("Header updated successfully")
            else:
                st.error("Failed to update header")
    
    with st.form("edit_section1_form"):
        st.subheader("About")
        section1 = st.text_area("About", value=cv_data.get("section1", ""))
        submit_section1 = st.form_submit_button("Update About Section")
        
        if submit_section1:
            if update_cv_section(username, "section1", section1):
                st.success("About section updated successfully")
            else:
                st.error("Failed to update About section")
    
    with st.form("edit_section2_form"):
        st.subheader("Additional Information")
        section2 = st.text_area("Additional Information", value=cv_data.get("section2", ""))
        submit_section2 = st.form_submit_button("Update Additional Information Section")
        
        if submit_section2:
            if update_cv_section(username, "section2", section2):
                st.success("Additional information updated successfully")
            else:
                st.error("Failed to update Additional information")
    
    # Ajouter le lien vers le CV public
    show_public_cv_link(username)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Back to Profile", key="back_to_profile_btn_edit"):
            st.session_state.page = PAGE_USER_PROFILE
            st.rerun()
    
    with col2:
        if st.button("View CV", key="view_cv_btn_edit"):
            st.session_state.page = PAGE_VIEW_CV
            st.rerun()

def main():
    # Sidebar avec le nom de l'app
    st.sidebar.title("CV Manager")
    
    if st.session_state.user:
        st.sidebar.write(f"Logged in as: {st.session_state.user['name']}")
        if st.sidebar.button("Logout", key="logout_btn_sidebar"):
            logout()
            st.rerun()
    
    # Afficher la page actuelle
    if st.session_state.page == PAGE_LOGIN:
        show_login_page()
    elif st.session_state.page == PAGE_REGISTER:
        show_register_page()
    elif st.session_state.page == PAGE_USER_PROFILE:
        show_user_profile()
    elif st.session_state.page == PAGE_VIEW_CV:
        show_view_cv()
    elif st.session_state.page == PAGE_EDIT_CV:
        show_edit_cv()

if __name__ == "__main__":
    main()