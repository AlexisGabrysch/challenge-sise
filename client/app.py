import streamlit as st
from streamlit.components.v1 import html
import os
import requests
import json
from typing import Optional, Dict, Any
import base64
from datetime import datetime
import time
# Configuration pour la largeur complète
st.set_page_config(
    page_title="CV Manager",
    page_icon="📄",
    layout="wide",  # Utilise toute la largeur disponible
    initial_sidebar_state="auto"
)
# Configuration URLs
SERVER_URL = os.getenv("SERVER_URL", "https://challenge-sise-production-0bc4.up.railway.app")

# Définir les pages de l'application
PAGE_HOME = "home"  # Nouvelle page d'accueil
PAGE_LOGIN = "login"
PAGE_REGISTER = "register"
PAGE_USER_PROFILE = "profile"
PAGE_EDIT_CV = "edit_cv"
PAGE_VIEW_CV = "view_cv"

# Initialiser l'état de session
if "page" not in st.session_state:
    st.session_state.page = PAGE_HOME  # Changer la page par défaut à HOME

if "user" not in st.session_state:
    st.session_state.user = None

if "session_token" not in st.session_state:
    st.session_state.session_token = None

# Fonction pour charger une image locale et la convertir en base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Fonction pour définir un arrière-plan personnalisé
def set_background(png_file):
    try:
        bin_str = get_base64_of_bin_file(png_file)
        page_bg_img = '''
        <style>
        .stApp {
            background-image: url("data:image/png;base64,%s");
            background-size: cover;
        }
        </style>
        ''' % bin_str
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except:
        # Si l'image n'est pas disponible, utiliser une couleur de fond dégradée
        st.markdown(
            """
            <style>
            .stApp {
                background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%);
            }
            </style>
            """,
            unsafe_allow_html=True
        )

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

# Add this function to handle file uploads
def upload_cv_file(username: str, file) -> bool:
    """Upload and process a CV file via the server API"""
    try:
        # Create the multipart/form-data request
        files = {"file": (file.name, file.getvalue(), f"application/{file.type}")}
        
        response = requests.post(
            f"{SERVER_URL}/api/cv/{username}/upload",
            headers={"Authorization": f"Bearer {st.session_state.session_token}"},
            files=files
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, data.get("message", "CV uploaded and processed successfully")
        else:
            error_detail = "Unknown error"
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except:
                pass
            return False, f"Error processing CV: {error_detail}"
    except Exception as e:
        return False, f"Error uploading CV: {str(e)}"

# Add this function after the upload_cv_file function
def delete_cv(username: str) -> tuple:
    """Delete the user's CV via the server API"""
    try:
        response = requests.delete(
            f"{SERVER_URL}/api/cv/{username}/delete",
            headers={"Authorization": f"Bearer {st.session_state.session_token}"}
        )
        
        if response.status_code == 200:
            return True, "CV deleted successfully"
        else:
            error_detail = "Unknown error"
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except:
                pass
            return False, f"Error deleting CV: {error_detail}"
    except Exception as e:
        return False, f"Error deleting CV: {str(e)}"

def render_auth_header(active: str):
    """
    Affiche un header similaire à la home page pour les pages d'authentification.
    Le paramètre active doit être soit "login" soit "register".
    """
    header_html = f"""
    <style>
    .header {{
       display: flex;
       justify-content: space-between;
       align-items: center;
       padding: 1rem 0;
       margin-bottom: 2rem;
    }}
    .logo {{
       font-size: 1.8rem;
       font-weight: 700;
       background: linear-gradient(135deg, #BDD2E4, #E0D4E7);
       -webkit-background-clip: text;
       -webkit-text-fill-color: transparent;
       letter-spacing: 0.02em;
    }}
    .nav-buttons {{
       display: flex;
       gap: 1rem;
    }}
    .nav-btn {{
       padding: 0.5rem 1.5rem;
       border-radius: 50px;
       font-weight: 500;
       font-size: 0.9rem;
       cursor: pointer;
       background-color: white;
       border: 1px solid #CCDCEB;
       color: #6a7b96;
       transition: all 0.3s ease;
       text-decoration: none;
    }}
    .nav-btn.active {{
       background: linear-gradient(135deg, #BDD2E4, #E0D4E7);
       border: none;
       color: #333;
    }}
    </style>
    <div class="header">
      <div class="logo">CVision</div>
      <div class="nav-buttons">
         <div class="nav-btn {'active' if active=='login' else ''}">Connexion</div>
         <div class="nav-btn {'active' if active=='register' else ''}">S'inscrire</div>
      </div>
    </div>
    """
    st.components.v1.html(header_html, height=120)


def show_login_page():
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    render_auth_header("login")
    st.markdown("</div>", unsafe_allow_html=True)
    
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
    st.markdown("---")
    st.info("Vous n'avez pas de compte ?")
    if st.button("Register", key="go_to_register"):
        st.session_state.page = PAGE_REGISTER
        st.rerun()


def show_register_page():
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    render_auth_header("register")
    st.markdown("</div>", unsafe_allow_html=True)
    
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
    st.markdown("---")
    st.info("Vous avez déjà un compte ?")
    if st.button("Login", key="go_to_login"):
        st.session_state.page = PAGE_LOGIN
        st.rerun()

def show_user_profile():
    if not st.session_state.user:
        st.session_state.page = PAGE_LOGIN
        st.rerun()
        
    username = st.session_state.user["name"]
    st.title(f"Welcome, {username}!")
    
    # Add CV upload section
    st.header("Upload your CV")
    
    # Create a styled upload area
    st.markdown("""
    <style>
    .uploadfile {
        border: 2px dashed #aaa;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
        background-color: white !important;
    }
    .uploadfile:hover {
        border-color: #4285F4;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<p>Upload a PDF, JPEG, or PNG file of your CV:</p>", unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader("Choose your CV file", 
                                    type=["pdf", "jpg", "jpeg", "png"], 
                                    key="cv_uploader",
                                    help="Upload your CV to automatically generate your profile")
    
    if uploaded_file is not None:
        # Show file details
        file_details = {"Filename": uploaded_file.name, "File size": f"{uploaded_file.size / 1024:.2f} KB"}
        st.write(file_details)
        
        # Show preview based on file type
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension in ['jpg', 'jpeg', 'png']:
            st.image(uploaded_file, width=300, caption="Preview")
        elif file_extension == 'pdf':
            st.info("PDF preview not available. Click 'Process CV' to upload and process your CV.")
        
        # Process button
        if st.button("Process CV"):
            with st.spinner("Processing your CV with AI... This may take a moment."):
                success, message = upload_cv_file(username, uploaded_file)
                
                if success:
                    st.success(message)
                    st.info("Navigating to your CV page in 3 seconds...")
                    # Redirect to view CV after successful processing
                    st.markdown(f"""
                    <meta http-equiv="refresh" content="3; url={SERVER_URL}/user/{username}">
                    """, unsafe_allow_html=True)
                else:
                    st.error(message)
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Original buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("View My CV", key="view_cv_btn_profile"):
            st.session_state.page = PAGE_VIEW_CV
            st.rerun()
    
    with col2:
        if st.button("Edit My CV", key="edit_cv_btn_profile"):
            st.session_state.page = PAGE_EDIT_CV
            st.rerun()
    
    # Add delete CV button with confirmation
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #d32f2f;'>Danger Zone</h3>", unsafe_allow_html=True)
    
    with st.expander("Delete My CV"):
        st.warning("Warning: This action cannot be undone. Your CV data will be permanently deleted.")
        if st.button("Delete CV Permanently", key="delete_cv_btn"):
            with st.spinner("Deleting your CV..."):
                success, message = delete_cv(username)
                if success:
                    st.success(message)
                    st.info("Your CV has been deleted. You'll be redirected to your profile in 3 seconds...")
                    st.markdown(f"""
                    <meta http-equiv="refresh" content="3; url={SERVER_URL}/user/{username}">
                    """, unsafe_allow_html=True)
                else:
                    st.error(message)
    
    # Ajouter le lien vers le CV public
    show_public_cv_link(username)
    
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
        # Utiliser unsafe_allow_html=True pour rendre correctement le HTML
        section2_html = cv_data.get("section2", "<div class='hobbies-list'></div>")
        st.markdown(section2_html, unsafe_allow_html=True)
        
        # Afficher les autres sections disponibles
        if cv_data.get("experience"):
            st.subheader("Professional Experience")
            st.markdown(cv_data.get("experience"), unsafe_allow_html=True)
        
        if cv_data.get("education"):
            st.subheader("Education")
            st.markdown(cv_data.get("education"), unsafe_allow_html=True)
        
        if cv_data.get("skills"):
            st.subheader("Skills")
            st.markdown(cv_data.get("skills"), unsafe_allow_html=True)
        
        # Afficher les informations de contact
        st.subheader("Contact Information")
        contact_info = f"""
        * **Email:** {cv_data.get('email', '')}
        * **Phone:** {cv_data.get('phone', '')}
        * **Location:** {cv_data.get('location', '')}
        """
        st.markdown(contact_info)
    
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
    
    # Personal information section
    st.header("Personal Information")
    
    # Name fields
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name", value=cv_data.get("first_name", ""))
        if st.button("Update First Name"):
            if update_cv_section(username, "first_name", first_name):
                st.success("First name updated successfully")
            else:
                st.error("Failed to update first name")
    
    with col2:
        last_name = st.text_input("Last Name", value=cv_data.get("last_name", ""))
        if st.button("Update Last Name"):
            if update_cv_section(username, "last_name", last_name):
                st.success("Last name updated successfully")
            else:
                st.error("Failed to update last name")
    
    # Contact information
    st.subheader("Contact Information")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        email = st.text_input("Email", value=cv_data.get("email", ""))
        if st.button("Update Email"):
            if update_cv_section(username, "email", email):
                st.success("Email updated successfully")
            else:
                st.error("Failed to update email")
    
    with col2:
        phone = st.text_input("Phone", value=cv_data.get("phone", ""))
        if st.button("Update Phone"):
            if update_cv_section(username, "phone", phone):
                st.success("Phone updated successfully")
            else:
                st.error("Failed to update phone")
    
    with col3:
        address = st.text_input("Address", value=cv_data.get("address", "") or cv_data.get("location", ""))
        if st.button("Update Address"):
            if update_cv_section(username, "address", address):
                st.success("Address updated successfully")
            else:
                st.error("Failed to update address")
    
    # Professional information
    st.header("Professional Information")
    
    # Job title
    job_title = st.text_input("Job Title", value=cv_data.get("job_title", "") or cv_data.get("title", ""))
    if st.button("Update Job Title"):
        if update_cv_section(username, "job_title", job_title):
            st.success("Job title updated successfully")
        else:
            st.error("Failed to update job title")
    
    # Driving license
    driving_license = st.text_input("Driving License", value=cv_data.get("driving_license", ""))
    if st.button("Update Driving License"):
        if update_cv_section(username, "driving_license", driving_license):
            st.success("Driving license updated successfully")
        else:
            st.error("Failed to update driving license")
    
    # About/Summary
    st.header("About Me")
    summary = st.text_area("Professional Summary", value=cv_data.get("summary", "") or cv_data.get("section1", ""))
    if st.button("Update Summary"):
        if update_cv_section(username, "summary", summary):
            st.success("Summary updated successfully")
        else:
            st.error("Failed to update summary")
    
    # Skills
    st.header("Skills")
    
    # Get existing skills or empty list
    existing_skills = cv_data.get("skills", [])
    if isinstance(existing_skills, str):
        try:
            # Try to parse if it's a JSON string
            existing_skills = json.loads(existing_skills)
        except:
            existing_skills = []
    
    skills_text = st.text_area("Skills (one per line)", value="\n".join(existing_skills))
    if st.button("Update Skills"):
        skills_list = [skill.strip() for skill in skills_text.split("\n") if skill.strip()]
        if update_cv_section(username, "skills", skills_list):
            st.success("Skills updated successfully")
        else:
            st.error("Failed to update skills")
    
    # Languages
    st.header("Languages")
    
    # Get existing languages or empty dict
    existing_languages = cv_data.get("languages", {})
    if isinstance(existing_languages, str):
        try:
            existing_languages = json.loads(existing_languages)
        except:
            existing_languages = {}
    
    languages_text = st.text_area("Languages (format: Language: Level)", 
                               value="\n".join([f"{lang}: {level}" for lang, level in existing_languages.items()]))
    
    if st.button("Update Languages"):
        languages_dict = {}
        for line in languages_text.split("\n"):
            if ":" in line:
                lang, level = line.split(":", 1)
                languages_dict[lang.strip()] = level.strip()
        
        if update_cv_section(username, "languages", languages_dict):
            st.success("Languages updated successfully")
        else:
            st.error("Failed to update languages")
    
    # Hobbies
    st.header("Hobbies")
    
    # Get existing hobbies or empty list
    existing_hobbies = cv_data.get("hobbies", [])
    if isinstance(existing_hobbies, str):
        try:
            existing_hobbies = json.loads(existing_hobbies)
        except:
            existing_hobbies = []
    
    hobbies_text = st.text_area("Hobbies (one per line)", value="\n".join(existing_hobbies))
    if st.button("Update Hobbies"):
        hobbies_list = [hobby.strip() for hobby in hobbies_text.split("\n") if hobby.strip()]
        if update_cv_section(username, "hobbies", hobbies_list):
            st.success("Hobbies updated successfully")
        else:
            st.error("Failed to update hobbies")
    
    # Certifications
    st.header("Certifications")
    
    # Get existing certifications or empty list
    existing_certifications = cv_data.get("certifications", [])
    if isinstance(existing_certifications, str):
        try:
            existing_certifications = json.loads(existing_certifications)
        except:
            existing_certifications = []
    
    certifications_text = st.text_area("Certifications (one per line)", value="\n".join(existing_certifications))
    if st.button("Update Certifications"):
        certifications_list = [cert.strip() for cert in certifications_text.split("\n") if cert.strip()]
        if update_cv_section(username, "certifications", certifications_list):
            st.success("Certifications updated successfully")
        else:
            st.error("Failed to update certifications")
    
    # Link to public CV
    show_public_cv_link(username)
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to Profile", key="back_to_profile_btn_edit"):
            st.session_state.page = PAGE_USER_PROFILE
            st.rerun()
    
    with col2:
        if st.button("View CV", key="view_cv_btn_edit"):
            st.session_state.page = PAGE_VIEW_CV
            st.rerun()
def show_home_page():
    """Page d'accueil minimaliste avec couleurs pastel et design épuré"""
    
    # Utiliser le composant HTML pour un contrôle total sur le style
    html_content = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Poppins', sans-serif;
            }
            
            body {
                background-color: white;
                color: #333;
                line-height: 1.6;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem;
                position: relative;
            }
            
            /* Formes décoratives */
            .shape {
                position: absolute;
                z-index: -1;
                border-radius: 50%;
                opacity: 0.6;
                filter: blur(40px);
            }
            
            .shape-1 {
                width: 300px;
                height: 300px;
                background-color: #FAE7EB;
                top: -50px;
                right: 10%;
            }
            
            .shape-2 {
                width: 200px;
                height: 200px;
                background-color: #E0D4E7;
                bottom: 10%;
                left: 5%;
            }
            
            .shape-3 {
                width: 180px;
                height: 180px;
                background-color: #DBEEF7;
                top: 40%;
                right: 15%;
            }
            
            .shape-4 {
                width: 120px;
                height: 120px;
                background-color: #EECEDA;
                top: 60%;
                left: 25%;
            }
            
            /* Header */
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1rem 0;
                margin-bottom: 3rem;
            }
            
            .logo {
                font-size: 1.8rem;
                font-weight: 700;
                background: linear-gradient(135deg, #BDD2E4, #E0D4E7);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                letter-spacing: 0.02em;
            }
            
            .nav-buttons {
                display: flex;
                gap: 1rem;
            }
            
            .nav-btn {
                padding: 0.5rem 1.5rem;
                border-radius: 50px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                font-size: 0.9rem;
            }
            
            .login-btn {
                color: #6a7b96;
                border: 1px solid #CCDCEB;
                background-color: white;
            }
            
            .login-btn:hover {
                background-color: #CCDCEB;
                color: #333;
            }
            
            .signup-btn {
                background: linear-gradient(135deg, #BDD2E4, #CCDCEB);
                color: #333;
                border: none;
                box-shadow: 0 4px 10px rgba(189, 210, 228, 0.3);
            }
            
            .signup-btn:hover {
                box-shadow: 0 6px 15px rgba(189, 210, 228, 0.5);
                transform: translateY(-2px);
            }
            
            /* Hero section */
            .hero {
                display: flex;
                align-items: center;
                min-height: 550px;
                margin-bottom: 5rem;
                position: relative;
            }
            
            .hero-content {
                width: 55%;
                padding-right: 2rem;
                position: relative;
                z-index: 2;
            }
            
            .hero-tagline {
                display: inline-block;
                padding: 0.3rem 1rem;
                background-color: #FAE7EB;
                border-radius: 50px;
                font-size: 0.8rem;
                font-weight: 600;
                margin-bottom: 1.5rem;
                color: #e06e8e;
            }
            
            .hero-title {
                font-size: 3.2rem;
                font-weight: 700;
                line-height: 1.2;
                margin-bottom: 1.5rem;
                color: #333;
            }
            
            .hero-subtitle {
                font-size: 1.1rem;
                color: #6a7b96;
                margin-bottom: 2.5rem;
                max-width: 90%;
            }
            
            .cta-buttons {
                display: flex;
                gap: 1rem;
            }
            
            .primary-btn {
                padding: 0.8rem 2rem;
                border-radius: 50px;
                font-weight: 600;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                background: linear-gradient(135deg, #EECEDA, #E0D4E7);
                color: #333;
                border: none;
                box-shadow: 0 4px 15px rgba(238, 206, 218, 0.4);
            }
            
            .primary-btn:hover {
                box-shadow: 0 6px 20px rgba(238, 206, 218, 0.6);
                transform: translateY(-3px);
            }
            
            .secondary-btn {
                padding: 0.8rem 2rem;
                border-radius: 50px;
                font-weight: 600;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                background-color: transparent;
                color: #6a7b96;
                border: 1px solid #CCDCEB;
            }
            
            .secondary-btn:hover {
                background-color: #CCDCEB;
                color: #333;
            }
            
            .hero-image-container {
                width: 45%;
                position: relative;
                z-index: 1;
            }
            
            .hero-image {
                width: 100%;
                height: auto;
                object-fit: contain;
                border-radius: 10px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.05);
            }
            
            /* Features section */
            .features {
                margin-bottom: 6rem;
            }
            
            .section-title {
                text-align: center;
                font-size: 2.2rem;
                font-weight: 700;
                margin-bottom: 3rem;
                color: #333;
            }
            
            .features-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 2rem;
            }
            
            .feature-card {
                background-color: white;
                border-radius: 16px;
                padding: 2rem;
                text-align: center;
                transition: all 0.3s ease;
                box-shadow: 0 5px 20px rgba(0, 0, 0, 0.02);
                border: 1px solid #f5f5f5;
            }
            
            .feature-card:hover {
                transform: translateY(-10px);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
            }
            
            .feature-icon {
                width: 70px;
                height: 70px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1.5rem;
                font-size: 2rem;
            }
            
            .icon-1 {
                background-color: #FAE7EB;
                color: #e06e8e;
            }
            
            .icon-2 {
                background-color: #E0D4E7;
                color: #9b6dbb;
            }
            
            .icon-3 {
                background-color: #DBEEF7;
                color: #5b9bd5;
            }
            
            .feature-title {
                font-size: 1.2rem;
                font-weight: 600;
                margin-bottom: 1rem;
                color: #333;
            }
            
            .feature-description {
                font-size: 0.95rem;
                color: #6a7b96;
            }
            
            /* Testimonials */
            .testimonials {
                padding: 4rem 0;
                background-color: #f9fafc;
                border-radius: 30px;
                margin-bottom: 5rem;
            }
            
            .testimonial-card {
                background-color: white;
                border-radius: 16px;
                padding: 2rem;
                margin: 0 1.5rem;
                box-shadow: 0 5px 20px rgba(0, 0, 0, 0.03);
            }
            
            .testimonial-text {
                font-size: 1.1rem;
                font-style: italic;
                color: #4a5568;
                margin-bottom: 1.5rem;
                line-height: 1.7;
            }
            
            .testimonial-author {
                display: flex;
                align-items: center;
            }
            
            .author-avatar {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: linear-gradient(135deg, #EECEDA, #E0D4E7);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                color: white;
                margin-right: 1rem;
            }
            
            .author-info {
                line-height: 1.4;
            }
            
            .author-name {
                font-weight: 600;
                color: #333;
            }
            
            .author-title {
                font-size: 0.85rem;
                color: #6a7b96;
            }
            
            /* CTA Section */
            .cta {
                background: linear-gradient(135deg, #BDD2E4, #E0D4E7);
                border-radius: 24px;
                padding: 4rem 3rem;
                text-align: center;
                margin-bottom: 4rem;
                position: relative;
                overflow: hidden;
            }
            
            .cta-blob {
                position: absolute;
                border-radius: 50%;
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            .blob-1 {
                width: 200px;
                height: 200px;
                top: -100px;
                right: -50px;
            }
            
            .blob-2 {
                width: 150px;
                height: 150px;
                bottom: -70px;
                left: -40px;
            }
            
            .cta-title {
                font-size: 2.5rem;
                font-weight: 700;
                color: white;
                margin-bottom: 1.5rem;
                position: relative;
                z-index: 2;
            }
            
            .cta-subtitle {
                font-size: 1.1rem;
                color: rgba(255, 255, 255, 0.9);
                margin-bottom: 2.5rem;
                max-width: 700px;
                margin-left: auto;
                margin-right: auto;
                position: relative;
                z-index: 2;
            }
            
            /* Footer */
            .footer {
                text-align: center;
                padding: 2rem 0;
                color: #6a7b96;
                font-size: 0.9rem;
            }
            
            .footer-logo {
                font-size: 1.5rem;
                font-weight: 700;
                margin-bottom: 1rem;
                color: #333;
            }
            
            /* Responsive */
            @media (max-width: 1024px) {
                .hero-content {
                    width: 60%;
                }
                
                .hero-image-container {
                    width: 40%;
                }
                
                .hero-title {
                    font-size: 2.8rem;
                }
            }
            
            @media (max-width: 768px) {
                .hero {
                    flex-direction: column;
                }
                
                .hero-content, .hero-image-container {
                    width: 100%;
                }
                
                .hero-content {
                    margin-bottom: 3rem;
                    padding-right: 0;
                }
                
                .features-grid {
                    grid-template-columns: 1fr;
                    gap: 1.5rem;
                }
                
                .cta {
                    padding: 3rem 1.5rem;
                }
                
                .cta-title {
                    font-size: 2rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Formes décoratives -->
            <div class="shape shape-1"></div>
            <div class="shape shape-2"></div>
            <div class="shape shape-3"></div>
            <div class="shape shape-4"></div>
            
            <!-- Header -->
            <header class="header">
                <div class="logo">CVision</div>
                <div class="nav-buttons">
                    <a href="https://beneficial-liberation-production.up.railway.app/" class="nav-btn login-btn" id="login-nav">Connexion</a>
                    <a href="https://beneficial-liberation-production.up.railway.app/" class="nav-btn signup-btn" id="signup-nav">S'inscrire</a>
                </div>
            </header>
            
            <!-- Hero Section -->
            <section class="hero">
                <div class="hero-content">
                    <span class="hero-tagline">Alimenté par l'Intelligence Artificielle</span>
                    <h1 class="hero-title">Transformez votre parcours en opportunités</h1>
                    <p class="hero-subtitle">Créez un CV qui vous démarque grâce à notre analyse intelligente et nos designs minimalistes parfaitement adaptés aux recruteurs modernes.</p>
                    <div class="cta-buttons">
                        <a href="https://beneficial-liberation-production.up.railway.app/" class="primary-btn" id="create-cv-btn">Créer mon CV</a>
                        <a href="https://beneficial-liberation-production.up.railway.app/" class="secondary-btn" id="discover-btn">Découvrir</a>
                    </div>
                </div>
                <div class="hero-image-container">
                    <img src="https://images.unsplash.com/photo-1586281380349-632531db7ed4?ixlib=rb-4.0.3&auto=format&fit=crop&w=1050&q=80" alt="CV Design Example" class="hero-image">
                </div>
            </section>
            
            <!-- Features Section -->
            <section class="features">
                <h2 class="section-title">Pourquoi choisir CVision</h2>
                <div class="features-grid">
                    <div class="feature-card">
                        <div class="feature-icon icon-1">✨</div>
                        <h3 class="feature-title">Analyse Intelligente</h3>
                        <p class="feature-description">Notre IA identifie vos compétences clés et restructure votre parcours pour un impact maximal auprès des recruteurs.</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon icon-2">🔍</div>
                        <h3 class="feature-title">Optimisation ATS</h3>
                        <p class="feature-description">Votre CV est optimisé pour passer les systèmes de tri automatisés utilisés par 90% des entreprises aujourd'hui.</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon icon-3">🎨</div>
                        <h3 class="feature-title">Design Épuré</h3>
                        <p class="feature-description">Des mises en page élégantes et modernes qui mettent en valeur vos expériences sans surcharge visuelle.</p>
                    </div>
                </div>
            </section>
            
            <!-- Testimonials -->
            <section class="testimonials">
                <h2 class="section-title">Témoignages</h2>
                <div class="testimonial-card">
                    <p class="testimonial-text">"J'ai téléchargé mon ancien CV et en quelques minutes, j'ai obtenu une version nettement plus professionnelle et pertinente. Trois entretiens décrochés la semaine suivante !"</p>
                    <div class="testimonial-author">
                        <div class="author-avatar">ML</div>
                        <div class="author-info">
                            <div class="author-name">Marie Lemaire</div>
                            <div class="author-title">UX Designer</div>
                        </div>
                    </div>
                </div>
            </section>
            
            <!-- CTA Section -->
            <section class="cta">
                <div class="cta-blob blob-1"></div>
                <div class="cta-blob blob-2"></div>
                <h2 class="cta-title">Prêt à transformer votre carrière ?</h2>
                <p class="cta-subtitle">Rejoignez des milliers de professionnels qui ont déjà boosté leurs opportunités professionnelles grâce à CVision</p>
                <a href="https://beneficial-liberation-production.up.railway.app/" class="primary-btn" id="final-cta-btn">Commencer maintenant</a>
            </section>
            
            <!-- Footer -->
            <footer class="footer">
                <div class="footer-logo">CVision</div>
                <p>© 2024 CVision | Tous droits réservés</p>
            </footer>
        </div>
    </body>
    </html>
    """
    
    html(html_content, height=2500)

 

# Mise à jour de la fonction principale pour inclure la page d'accueil
def main():
    # Essayer de définir un arrière-plan
    
    # Masquer les éléments Streamlit par défaut sur la page d'accueil
    # if st.session_state.page == PAGE_HOME:
    #     st.markdown("""
    #         <style>
    #         #MainMenu {visibility: hidden;}
    #         header {visibility: hidden;}
    #         footer {visibility: hidden;}
    #         </style>
    #         """, unsafe_allow_html=True)
    
    # Sidebar avec le nom de l'app (sauf sur la page d'accueil)
    if st.session_state.page != PAGE_HOME:
        st.sidebar.title("CV Manager")
        
        if st.session_state.user:
            st.sidebar.write(f"Logged in as: {st.session_state.user['name']}")
            if st.sidebar.button("Logout", key="logout_btn_sidebar"):
                logout()
                st.rerun()
        else:
            if st.sidebar.button("Page d'accueil", key="home_btn_sidebar"):
                st.session_state.page = PAGE_HOME
                st.rerun()
    
    # Afficher la page actuelle
    if st.session_state.page == PAGE_HOME:
        show_home_page()
    elif st.session_state.page == PAGE_LOGIN:
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