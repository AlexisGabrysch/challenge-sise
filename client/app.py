import streamlit as st
from streamlit.components.v1 import html
import os
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
def footer():
    # Footer avec crédits et liens
    return st.markdown("""
    <div style='margin-top: 30px; text-align: center;'>
        <div style='height: 1px; background: #ddd; margin: 20px 0;'></div>
        <div style='font-family: Arial, sans-serif; color: #666; font-size: 0.8rem;'>
            Projet CVVision © 2025 | Développé par 
            <a href="https://github.com/alexisgabrysch" target="_blank" style='color: #1E88E5; text-decoration: none;'>Alexis Gabrysch</a>,
            <a href="https://github.com/Sahm269" target="_blank" style='color: #1E88E5; text-decoration: none;'>Souraya Ahmed</a>, 
            <a href="https://github.com/maxenceLIOGIER" target="_blank" style='color: #1E88E5; text-decoration: none;'>Maxence Liogier</a>,
            <a href="https://github.com/akremjomaa" target="_blank" style='color: #1E88E5; text-decoration: none;'>Akrem Jomaa</a>  |
            <a href="https://github.com/alexisgabrysch/challenge-sise" target="_blank" style='color: #1E88E5; text-decoration: none;'>Repo GitHub</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def update_cv_image(username: str, file) -> tuple:
    """Convert image to base64 and update via the update_cv_section API"""
    try:
        # Convert image to base64
        import base64
        file_bytes = file.getvalue()
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        # Use the existing update_cv_section function
        if update_cv_section(username, "image_base64", base64_image):
            return True, "Profile image updated successfully"
        else:
            return False, "Failed to update profile image"
    except Exception as e:
        return False, f"Error processing image: {str(e)}"

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
    footer()
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
    footer()
def show_user_profile():
    if not st.session_state.user:
        st.session_state.page = PAGE_LOGIN
        st.rerun()
        
    username = st.session_state.user["name"]
    
    # Apply modern CSS styling
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        margin-bottom: 2rem;
        color: #1E88E5;
        font-weight: 700;
    }
    .section-container {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #333;
        border-bottom: 2px solid #f0f0f0;
        padding-bottom: 0.5rem;
    }
    .btn-primary {
        background-color: #1E88E5;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .btn-primary:hover {
        background-color: #1565C0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .btn-secondary {
        background-color: #f8f9fa;
        color: #333;
        border: 1px solid #ddd;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .btn-secondary:hover {
        background-color: #e9ecef;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .danger-zone {
        border-left: 4px solid #f44336;
        padding-left: 1rem;
    }
    .upload-container {
        border: 2px dashed #aaa;
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        background-color: #f8f9fa;
        transition: all 0.3s ease;
    }
    .upload-container:hover {
        border-color: #1E88E5;
        background-color: #f1f8fe;
    }
    .upload-icon {
        font-size: 3rem;
        color: #aaa;
        margin-bottom: 1rem;
    }
    .welcome-card {
        background: linear-gradient(135deg, #42a5f5 0%, #1976d2 100%);
        color: white;
        border-radius: 8px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Welcome card with user information
    st.markdown(f"""
    <div class="welcome-card">
        <h1 class="main-header">Welcome, {username}!</h1>
        <p>Manage your professional profile and CV from this dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for better organization
    tab1, tab2 = st.tabs(["Upload CV", "Manage Profile"])
    
    with tab1:
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-title">Upload your CV</h2>', unsafe_allow_html=True)
        
        
        
        uploaded_file = st.file_uploader("", 
                                        type=["pdf", "jpg", "jpeg", "png"], 
                                        key="cv_uploader",
                                        help="Upload your CV to automatically generate your profile")
        
        if uploaded_file is not None:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Show file details
                st.markdown(f"""
                <div style="padding: 1rem; background-color: #e3f2fd; border-radius: 4px; margin-bottom: 1rem;">
                    <p><strong>File name:</strong> {uploaded_file.name}</p>
                    <p><strong>Size:</strong> {uploaded_file.size / 1024:.2f} KB</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Process button
                if st.button("Process CV", use_container_width=True):
                    with st.spinner("Processing your CV with AI... This may take a moment."):
                        success, message = upload_cv_file(username, uploaded_file)
                        
                        if success:
                            st.success(message)
                            
            
                        else:
                            st.error(message)
            
            with col2:
                # Show preview based on file type
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                if file_extension in ['jpg', 'jpeg', 'png']:
                    st.image(uploaded_file, width=200, caption="Preview")
                elif file_extension == 'pdf':
                    st.info("PDF preview not available")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        # Action buttons with two columns
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-title">Manage Your CV</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
          
            
            # Still need a hidden button for Streamlit to work
            if st.button("View My CV", key="view_cv_btn_profile", use_container_width=True):
                st.session_state.page = PAGE_VIEW_CV
                st.rerun()
        
        with col2:
            
            
            if st.button("Edit My CV", key="edit_cv_btn_profile", use_container_width=True):
                st.session_state.page = PAGE_EDIT_CV
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Share CV section with improved styling
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-title">Share Your CV</h2>', unsafe_allow_html=True)
        
        public_cv_url = f"{SERVER_URL}/user/{username}"
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 1rem;">
            <p>Share your professional profile with this public link:</p>
            <div style="background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 4px; 
            padding: 10px; display: flex; align-items: center; margin: 10px 0;">
            <input type="text" value="{public_cv_url}" 
            style="flex: 1; border: none; background: transparent; padding: 5px; font-size: 14px;" readonly>
            </div>
        </div>
        """, unsafe_allow_html=True)

        
        st.markdown(f"""
        <div style="text-align: center;">
            <a href="{public_cv_url}" target="_blank" style="text-decoration: none;">
            <div style="display: inline-block; padding: 10px 20px; background-color: #1E88E5; 
            color: white; border-radius: 5px; font-weight: bold; margin-top: 10px;">
                View Public CV
            </div>
            </a>
            <p style="margin-top: 10px; font-size: 12px; color: #888;">
            This link can be shared with anyone, even if they don't have an account.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Danger Zone
        st.markdown('<div class="section-container">', unsafe_allow_html=True)
        st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-title" style="color: #d32f2f;">Danger Zone</h2>', unsafe_allow_html=True)
        
        with st.expander("Delete My CV"):
            st.warning("Warning: This action cannot be undone. Your CV data will be permanently deleted.")
            
            # Two-step confirmation for deletion
            confirm = st.checkbox("I understand that this action is irreversible", key="confirm_delete")
            
            if confirm:
                if st.button("Delete CV Permanently", key="delete_cv_btn", type="primary"):
                    with st.spinner("Deleting your CV..."):
                        success, message = delete_cv(username)
                        if success:
                            st.success(message)
                            st.info("Your CV has been deleted. You'll be redirected to your profile in 3 seconds...")
    
                        else:
                            st.error(message)
            else:
                st.button("Delete CV Permanently", key="delete_cv_btn_disabled", disabled=True)
        
        st.markdown('</div></div>', unsafe_allow_html=True)
        
        # Logout button at the bottom
        st.markdown('<div style="text-align: center; margin-top: 2rem;">', unsafe_allow_html=True)
        if st.button("Logout", key="logout_btn_profile", type="secondary"):
            logout()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    footer()
def show_view_cv():
    if not st.session_state.user:
        st.session_state.page = PAGE_LOGIN
        st.rerun()
    
    username = st.session_state.user["name"]
    st.title(f"{username}'s CV")
    
    # URL du CV public
    public_cv_url = f"{SERVER_URL}/user/{username}"
    
    

    # Afficher le CV en ligne avec iframe
    st.markdown("### Online CV Viewer")
    st.markdown("Below is your live online CV as others will see it when you share your public link:")
    
    # Utiliser un composant HTML pour créer un iframe responsive
    html_iframe = f"""
    <div style="position: relative; padding-bottom: 150%; height: 0; overflow: hidden; max-width: 100%; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <iframe src="{public_cv_url}" 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;" 
            title="{username}'s CV">
        </iframe>
    </div>
    <p style="text-align: center; margin-top: 10px; font-size: 14px; color: #888;">
        <a href="{public_cv_url}" target="_blank" style="color: #1E88E5; text-decoration: none;">
            Open in a new tab <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
        </a>
    </p>
    """
    
    # Rendre l'iframe
    st.components.v1.html(html_iframe, height=600)
    
    # Ajouter le lien vers le CV public
    show_public_cv_link(username)
    
   
    if st.button("Back to Profile", key="back_to_profile_btn_view"):
        st.session_state.page = PAGE_USER_PROFILE
        st.rerun()
    footer()

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
    
    # Profile Image Section
    st.subheader("Profile Image")
    
    # Afficher l'image actuelle si elle existe
    if cv_data.get("image_base64"):
        st.image(
            f"data:image/jpeg;base64,{cv_data['image_base64']}", 
            width=150, 
            caption="Current Profile Image"
        )
    
    # Upload d'une nouvelle image
    uploaded_image = st.file_uploader(
        "Upload new profile image", 
        type=["jpg", "jpeg", "png"],
        key="profile_image_uploader",
        help="Upload a new profile picture (JPG or PNG format)"
    )
    
    if uploaded_image is not None:
        # Afficher l'aperçu
        st.image(uploaded_image, width=150, caption="Preview")
        
        if st.button("Update Profile Image"):
            with st.spinner("Updating your profile image..."):
                success, message = update_cv_image(username, uploaded_image)
                if success:
                    st.success(message)
                    st.info("Your profile has been updated. Refresh the page to see changes.")
                else:
                    st.error(message)
    
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
    
   
    if st.button("Back to Profile", key="back_to_profile_btn_edit"):
        st.session_state.page = PAGE_USER_PROFILE
        st.rerun()

    
    footer()
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