import streamlit as st
from streamlit.components.v1 import html
import os
import requests
import json
from typing import Optional, Dict, Any
import base64
from datetime import datetime
import time

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
        background-color: #f8f9fa;
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
    """Nouvelle page d'accueil moderne et business-orientée"""
    
    # CSS personnalisé pour la page d'accueil
    st.markdown("""
    <style>
    .main-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .hero-section {
        text-align: center;
        padding: 60px 20px;
        border-radius: 10px;
        margin-bottom: 40px;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(5px);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.2);
    }
    
    .hero-title {
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 20px;
        color: white;
        text-shadow: 0px 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .hero-subtitle {
        font-size: 1.5rem;
        margin-bottom: 30px;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .feature-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 30px;
        margin-bottom: 50px;
    }
    
    .feature-card {
        background: white;
        border-radius: 10px;
        padding: 25px;
        width: 300px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        text-align: center;
    }
    
    .feature-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2);
    }
    
    .feature-icon {
        font-size: 40px;
        margin-bottom: 20px;
        color: #4285F4;
    }
    
    .feature-title {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 15px;
        color: #333;
    }
    
    .feature-text {
        font-size: 1rem;
        color: #555;
        line-height: 1.6;
    }
    
    .cta-container {
        text-align: center;
        margin: 40px 0;
    }
    
    .cta-button {
        display: inline-block;
        padding: 15px 30px;
        background-color: #4285F4;
        color: white;
        font-size: 1.2rem;
        font-weight: 600;
        border-radius: 50px;
        text-decoration: none;
        margin: 10px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        cursor: pointer;
        border: none;
    }
    
    .cta-button:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    }
    
    .cta-button.secondary {
        background-color: transparent;
        border: 2px solid white;
    }
    
    .testimonial-section {
        padding: 40px 0;
    }
    
    .testimonial-heading {
        text-align: center;
        font-size: 2rem;
        font-weight: 600;
        margin-bottom: 30px;
        color: white;
    }
    
    .testimonial-card {
        background: white;
        border-radius: 10px;
        padding: 30px;
        margin: 15px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    }
    
    .testimonial-text {
        font-style: italic;
        font-size: 1.1rem;
        color: #333;
        margin-bottom: 20px;
    }
    
    .testimonial-author {
        font-weight: 600;
        color: #4285F4;
    }
    
    .animated {
        opacity: 0;
        animation: fadeInUp 1s forwards;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .delay-1 {
        animation-delay: 0.3s;
    }
    
    .delay-2 {
        animation-delay: 0.6s;
    }
    
    .delay-3 {
        animation-delay: 0.9s;
    }
    
    .stats-container {
        display: flex;
        justify-content: center;
        text-align: center;
        margin: 50px 0;
    }
    
    .stat-item {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(5px);
        border-radius: 10px;
        padding: 20px;
        margin: 0 15px;
        width: 200px;
    }
    
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: white;
        margin-bottom: 10px;
    }
    
    .stat-label {
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .footer {
        text-align: center;
        padding: 30px 0;
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.9rem;
    }
    
    /* Pour masquer le header Streamlit et les autres éléments */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
    
    # Contenu de la page
    st.markdown("""
    <div class="main-container">
        <div class="hero-section animated">
            <h1 class="hero-title">Créez Votre CV Professionnel avec l'IA</h1>
            <p class="hero-subtitle">Boostez votre visibilité en ligne avec un portfolio 100% optimisé par l'intelligence artificielle</p>
        </div>
        
        <div class="feature-container">
            <div class="feature-card animated delay-1">
                <div class="feature-icon">🚀</div>
                <h3 class="feature-title">Création Instantanée</h3>
                <p class="feature-text">Téléchargez votre ancien CV ou commencez de zéro. Notre IA analyse et structure votre profil en quelques secondes.</p>
            </div>
            
            <div class="feature-card animated delay-2">
                <div class="feature-icon">✨</div>
                <h3 class="feature-title">Design Professionnel</h3>
                <p class="feature-text">Des templates modernes et adaptés à votre secteur d'activité pour vous démarquer auprès des recruteurs.</p>
            </div>
            
            <div class="feature-card animated delay-3">
                <div class="feature-icon">📊</div>
                <h3 class="feature-title">Optimisation ATS</h3>
                <p class="feature-text">Votre CV est optimisé pour les systèmes de suivi des candidatures utilisés par plus de 90% des entreprises.</p>
            </div>
        </div>
        
        <div class="stats-container animated delay-2">
            <div class="stat-item">
                <div class="stat-number">85%</div>
                <div class="stat-label">Taux de succès en entretien</div>
            </div>
            
            <div class="stat-item">
                <div class="stat-number">3X</div>
                <div class="stat-label">Plus de réponses positives</div>
            </div>
            
            <div class="stat-item">
                <div class="stat-number">24h</div>
                <div class="stat-label">CV prêt en moins de</div>
            </div>
        </div>
        
        <div class="cta-container animated delay-3">
            <button class="cta-button" id="register-button">Créer Mon CV Gratuitement</button>
            <button class="cta-button secondary" id="login-button">Me Connecter</button>
        </div>
        
        <div class="testimonial-section">
            <h2 class="testimonial-heading animated">Ils ont transformé leur carrière</h2>
            
            <div style="display: flex; overflow-x: auto; padding: 10px 0;">
                <div class="testimonial-card animated delay-1">
                    <p class="testimonial-text">"Grâce à CV Manager, j'ai décroché un entretien chez Google après 3 mois de recherche infructueuse."</p>
                    <p class="testimonial-author">— Marie L., Développeuse Full Stack</p>
                </div>
                
                <div class="testimonial-card animated delay-2">
                    <p class="testimonial-text">"L'optimisation par IA a parfaitement mis en valeur mon parcours atypique. Les recruteurs me contactent désormais directement."</p>
                    <p class="testimonial-author">— Thomas B., Consultant en Transition Numérique</p>
                </div>
                
                <div class="testimonial-card animated delay-3">
                    <p class="testimonial-text">"Un outil indispensable pour les jeunes diplômés comme moi qui n'ont pas beaucoup d'expérience à mettre en avant."</p>
                    <p class="testimonial-author">— Camille D., Ingénieure débutante</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            © 2024 CV Manager | Propulsé par l'IA | Tous droits réservés
        </div>
    </div>
    
    <script>
        // Animation des statistiques (compteur)
        document.addEventListener('DOMContentLoaded', function() {
            const statNumbers = document.querySelectorAll('.stat-number');
            statNumbers.forEach(elem => {
                const finalValue = elem.innerText;
                elem.innerText = '0';
                setTimeout(() => {
                    animateValue(elem, 0, finalValue, 1500);
                }, 1200);
            });
        });
        
        function animateValue(obj, start, end, duration) {
            let startTimestamp = null;
            const step = (timestamp) => {
                if (!startTimestamp) startTimestamp = timestamp;
                const progress = Math.min((timestamp - startTimestamp) / duration, 1);
                obj.innerHTML = end.includes('%') ? 
                    Math.floor(progress * parseInt(end)) + '%' :
                    end.includes('X') ?
                    Math.floor(progress * parseInt(end)) + 'X' :
                    end;
                if (progress < 1) {
                    window.requestAnimationFrame(step);
                }
            };
            window.requestAnimationFrame(step);
        }
        
        // Navigation buttons
        document.getElementById('register-button').addEventListener('click', function() {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'register'}, '*');
        });
        
        document.getElementById('login-button').addEventListener('click', function() {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'login'}, '*');
        });
    </script>
    """, unsafe_allow_html=True)
    
    # Gestion des clics sur les boutons (puisque le JavaScript ne peut pas directement changer la page)
    component_value = st.session_state.get('component_value', None)
    if component_value == 'register':
        st.session_state.page = PAGE_REGISTER
        st.rerun()
    elif component_value == 'login':
        st.session_state.page = PAGE_LOGIN
        st.rerun()
    
    # Actions alternatives pour les boutons (au cas où le JS ne fonctionne pas)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Créer mon CV", key="register_alt_btn"):
            st.session_state.page = PAGE_REGISTER
            st.rerun()
    with col2:
        if st.button("Me connecter", key="login_alt_btn"):
            st.session_state.page = PAGE_LOGIN
            st.rerun()

# Mise à jour de la fonction principale pour inclure la page d'accueil
def main():
    # Essayer de définir un arrière-plan
    try:
        # Pour un fond d'image, vous pouvez créer un dossier 'assets' et y mettre une image
        # set_background("assets/background.png")
        
        # Ou utiliser un fond de couleur dégradée
        st.markdown(
            """
            <style>
            .stApp {
                background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%);
                background-attachment: fixed;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
    except:
        pass
    
    # Masquer les éléments Streamlit par défaut sur la page d'accueil
    if st.session_state.page == PAGE_HOME:
        st.markdown("""
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """, unsafe_allow_html=True)
    
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