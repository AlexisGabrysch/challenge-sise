from fastapi import FastAPI, Request, Form, HTTPException, Depends, Cookie, Body, Header, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic
import uvicorn
import os
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
from datetime import datetime, timedelta
import secrets
import tempfile
import json
import asyncio
from modules.pdf_preprocessing import remove_background_from_pdf
from modules.ocr_extraction import extract_text_and_first_image_from_pdf, extract_text_from_pdf, extract_text_from_image
from modules.llm_structuring import structure_cv_json
from modules.cv_utils import add_cv_to_user


# Classes pour validation
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class CVUpdateRequest(BaseModel):
    section: str
    content: str

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("LOG_LEVEL") == "debug" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Setup Jinja2 templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

security = HTTPBasic()

# MongoDB connection
MONGO_URI = "mongodb+srv://cv_database:YnUNdP7NqfdkSRKy@challengesise.1aioj.mongodb.net/?retryWrites=true&w=majority&appName=challengeSISE"
client = MongoClient(MONGO_URI)
db = client["Challenge_SISE"]  # Base de données
users_collection = db["users"]  # Collection des utilisateurs
cvs_collection = db["cvs"]      # Collection des CV
sessions_collection = db["sessions"]  # Nouvelle collection pour les sessions

# URLs for redirects
SERVER_URL = os.getenv("SERVER_URL", "https://challenge-sise-production-0bc4.up.railway.app")
CLIENT_URL = os.getenv("CLIENT_URL", "https://beneficial-liberation-production.up.railway.app")
logger.debug(f"CLIENT_URL: {CLIENT_URL}")
logger.debug(f"SERVER_URL: {SERVER_URL}")

# Helper Functions
def hash_password(password: str) -> str:
    """Hash a password for storing"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a stored password against one provided by user"""
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))

def create_user(name: str, email: str, password: str):
    """Create a new user in MongoDB"""
    # Check if user already exists
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if users_collection.find_one({"user_name": name}):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user
    user_data = {
        "email": email,
        "password_hash": hash_password(password),
        "user_name": name,
        "created_at": datetime.utcnow()
    }
    
    result = users_collection.insert_one(user_data)
    return result.inserted_id

def authenticate_user(email: str, password: str):
    """Authenticate a user"""
    user = users_collection.find_one({"email": email})
    
    if not user or not verify_password(user["password_hash"], password):
        return None
    
    return {
        "id": str(user["_id"]),
        "name": user["user_name"],
        "email": user["email"]
    }
def create_session(user_id: str):
    """Create a new session for a user"""
    token = secrets.token_hex(32)
    # Change from 10 minutes to 30 days
    expires = datetime.utcnow() + timedelta(days=30)  # Changed from minutes=10 to days=30
    
    session = {
        "user_id": user_id,
        "token": token,
        "created_at": datetime.utcnow(),
        "expires_at": expires
    }
    
    sessions_collection.insert_one(session)
    return token

def get_user_from_session(token: str):
    """Get user from session token"""
    session = sessions_collection.find_one({
        "token": token,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not session:
        return None
    
    user = users_collection.find_one({"_id": ObjectId(session["user_id"])})
    if not user:
        return None
    
    return {
        "id": str(user["_id"]),
        "name": user["user_name"],
        "email": user["email"]
    }

def is_page_owner(token: str, username: str):
    """Check if the current session user is the owner of a page"""
    user = get_user_from_session(token)
    
    if not user:
        return False
    
    return user["name"] == username

async def get_current_user(request: Request):
    """Get current user from request cookies"""
    token = request.cookies.get("session_token")
    
    if not token:
        return None
    
    return get_user_from_session(token)

def get_or_create_user_by_name(name: str):
    """Get or create a user by name"""
    user = users_collection.find_one({"user_name": name})
    
    if user:
        return str(user["_id"])
    
    # Create new user
    new_user = {
        "user_name": name,
        "email": f"{name}@example.com",
        "password_hash": hash_password("temporary"),
        "created_at": datetime.utcnow()
    }
    
    result = users_collection.insert_one(new_user)
    return str(result.inserted_id)

def get_cv_content(user_id: str):
    """Get CV content for a user"""
    cv = cvs_collection.find_one({"user_id": user_id})
    
    if not cv:
        # Create default CV
        default_cv = {
            "user_id": user_id,
            "header": None,
            "section1": None,
            "section2": None,
            "experience": None,
            "education": None,
            "skills": None,
            "title": None,
            "email": None,
            "phone": None,
            "location": None,
            "last_updated": datetime.utcnow()
        }
        cvs_collection.insert_one(default_cv)
        return default_cv
    
    return cv

def update_cv_section(user_id: str, section: str, content: str):
    """Update a section of a user's CV"""
    # Check if CV exists
    cv = cvs_collection.find_one({"user_id": ObjectId(user_id)})
    
    if cv:
        # Update existing CV
        if "sections" in cv:
            # Modern format with nested sections
            cvs_collection.update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        f"sections.{section}": content,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        else:
            # Legacy format
            cvs_collection.update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        section: content,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
    else:
        # Create new CV with this section
        new_cv = {
            "user_id": ObjectId(user_id),
            "sections": {section: content},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        cvs_collection.insert_one(new_cv)

@app.post("/api/register")
async def api_register(register_request: RegisterRequest):
    """API endpoint pour l'enregistrement"""
    logger.debug(f"API Register attempt: {register_request.email}")
    
    try:
        # Create user
        user_id = create_user(
            register_request.name, 
            register_request.email, 
            register_request.password
        )
        
        # Create session
        session_token = create_session(str(user_id))
        
        # Return user data and session token
        return {
            "id": str(user_id),
            "name": register_request.name,
            "email": register_request.email,
            "session_token": session_token
        }
    except HTTPException as e:
        # Re-raise the exception to preserve status code and detail
        raise e
    
@app.post("/api/login")
async def api_login(login_request: LoginRequest):
    """API endpoint pour l'authentification"""
    logger.debug(f"API Login attempt: {login_request.email}")
    
    # Authenticate user
    user = authenticate_user(login_request.email, login_request.password)
    
    if not user:
        logger.debug("API Login failed")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    session_token = create_session(user["id"])
    
    # Return user data and session token
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "session_token": session_token
    }

@app.get("/api/cv/{name}")
async def api_get_cv(name: str, authorization: str = Header(None)):
    """API endpoint pour récupérer les données du CV"""
    logger.debug(f"API Get CV: {name}")
    
    # Get user by username
    user = users_collection.find_one({"user_name": name})
    
    if not user:
        # Create a new user if not found
        user_id = get_or_create_user_by_name(name)
    else:
        user_id = str(user["_id"])
    
    # Get CV data from MongoDB
    cv_doc = cvs_collection.find_one({"user_id": ObjectId(user_id)})
    
    result = {"name": name}
    
    if cv_doc and "sections" in cv_doc:
        cv = cv_doc["sections"]
        
        # Map MongoDB document structure to API response
        if "first_name" in cv and "last_name" in cv:
            result["header"] = f"{cv['first_name']} {cv['last_name']}"
        elif "first_name" in cv:
            result["header"] = cv['first_name']
        elif "last_name" in cv:
            result["header"] = cv['last_name']
        
        # Add all fields that exist
        for field in ["email", "phone", "address", "summary", "skills", "education", "work_experience", "projects", "hobbies", "languages", "certifications", "driving_license"]:
            if field in cv and cv[field]:
                if field == "address":
                    result["location"] = cv[field]
                elif field == "summary":
                    result["section1"] = cv[field]
                else:
                    result[field] = cv[field]
    
    return result
@app.post("/api/cv/{name}/update")
async def api_update_cv(name: str, update_data: CVUpdateRequest, authorization: str = Header(None)):
    """API endpoint pour mettre à jour une section du CV"""
    logger.debug(f"API Update CV: {name}, Section: {update_data.section}")
    
    # Extract session token from Authorization header
    session_token = None
    if authorization and authorization.startswith("Bearer "):
        session_token = authorization[7:]  # Remove "Bearer " prefix
    
    # Check authorization - only page owner can update
    if not session_token or not is_page_owner(session_token, name):
        raise HTTPException(status_code=403, detail="You don't have permission to edit this page")
    
    # Get user id
    user = users_collection.find_one({"user_name": name})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    
    # Update content
    update_cv_section(user_id, update_data.section, update_data.content)
    
    return {"status": "success"}




@app.post("/api/cv/{name}/upload")
async def api_upload_cv(name: str, file: UploadFile = File(...), authorization: str = Header(None)):
    """API endpoint for uploading and processing a CV file"""
    logger.debug(f"API Upload CV: {name}")
    
    # Extract session token from Authorization header
    session_token = None
    if authorization and authorization.startswith("Bearer "):
        session_token = authorization[7:]  # Remove "Bearer " prefix
    
    # Check authorization - only page owner can upload
    if not session_token or not is_page_owner(session_token, name):
        raise HTTPException(status_code=403, detail="You don't have permission to upload for this user")
    
    # Get user
    user = users_collection.find_one({"user_name": name})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])

    # Save the file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1].lower()}") as temp_file:
        contents = await file.read()
        temp_file.write(contents)
        temp_path = temp_file.name

    try:
        file_extension = file.filename.split('.')[-1].lower()
        ocr_text_original, ocr_text_clean = "", ""

        if file_extension == 'pdf':
            cleaned_pdf_path = f"{temp_path}_cleaned.pdf"

            # Remove background for B&W version
            remove_background_from_pdf(temp_path, cleaned_pdf_path)
            try:
                # Extract text from original PDF
                ocr_result_original = extract_text_and_first_image_from_pdf(temp_path, user["email"])
                ocr_text_original = ocr_result_original["markdown"]
                first_image = ocr_result_original["image"]
            
            except Exception as e:
                logger.error(f"Error extracting OCR from original PDF: {e}")
                ocr_text_original = ""
                first_image = None





            # Extract text from cleaned B&W PDF
            ocr_text_clean = extract_text_from_pdf(cleaned_pdf_path)

            # Clean up temporary cleaned PDF
            os.unlink(cleaned_pdf_path)

        elif file_extension in ['jpg', 'jpeg', 'png']:
            ocr_text_original = extract_text_from_image(temp_path)
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        # Combine texts from both versions
        text_total = f"""
        --- OCR FROM ORIGINAL PDF ---
        {ocr_text_original}

        --- OCR FROM CLEANED PDF ---
        {ocr_text_clean}
        """

        # Structure CV data with LLM with retry logic for rate limits
        max_retries = 5
        retry_delay = 2  # Start with 2 seconds delay
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt+1}/{max_retries} to process CV with LLM")
                cv_data = structure_cv_json(text_total)
                cv_data["image"] = first_image  # Store the first image found
                break  # Success, exit retry loop
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limited by API (429). Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    # If we've exhausted all retries or it's not a rate limit error
                    raise
        
        # Update CV sections with extracted data
        cv = cvs_collection.find_one({"user_id": ObjectId(user_id)})
        
        if not cv:
            # Create new CV document
            cv_data = {
                "user_id": ObjectId(user_id),
                "sections": cv_data,

                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            cvs_collection.insert_one(cv_data)
        else:
            # Update existing CV document with all sections
            cvs_collection.update_one(
                {"_id": cv["_id"]},
                {
                    "$set": {
                        "sections": cv_data,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        return {"status": "success", "message": "CV processed successfully"}
    
    except Exception as e:
        logger.error(f"Error processing CV: {e}")
        if "429" in str(e):
            raise HTTPException(status_code=429, detail="The service is currently experiencing high traffic. Please try again in a few minutes.")
        else:
            raise HTTPException(status_code=500, detail=f"Error processing CV: {str(e)}")
    
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)



@app.delete("/api/cv/{name}/delete")
async def api_delete_cv(name: str, authorization: str = Header(None)):
    """API endpoint pour supprimer un CV"""
    logger.debug(f"API Delete CV: {name}")
    
    # Extract session token from Authorization header
    session_token = None
    if authorization and authorization.startswith("Bearer "):
        session_token = authorization[7:]  # Remove "Bearer " prefix
    
    # Check authorization - only page owner can delete
    if not session_token or not is_page_owner(session_token, name):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this CV")
    
    # Get user
    user = users_collection.find_one({"user_name": name})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    
    # Delete the CV document
    result = cvs_collection.delete_one({"user_id": ObjectId(user_id)})
    
    # Create an empty CV document with minimal information
    # This allows the URL to still work but with no data
    default_cv = {
        "user_id": ObjectId(user_id),
        "sections": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_deleted": True  # Mark as deleted
    }
    cvs_collection.insert_one(default_cv)
    
    if result.deleted_count > 0:
        return {"status": "success", "message": "CV deleted successfully"}
    else:
        return {"status": "info", "message": "No CV found to delete"}
@app.get("/users/{name}", response_class=HTMLResponse)
@app.get("/user/{name}", response_class=HTMLResponse)
async def user_page(request: Request, name: str, theme: str = None):
    logger.debug(f"User page accessed for name: {name}, theme: {theme}")
    try:
        # Get user by username
        user = users_collection.find_one({"user_name": name})
        
        if not user:
            user_id = get_or_create_user_by_name(name)
        else:
            user_id = str(user["_id"])
        
        # Get CV content
        cv_doc = cvs_collection.find_one({"user_id": ObjectId(user_id)})
        
        # Check if current user is the owner of the page
        session_token = request.cookies.get("session_token")
        is_owner = False
        current_user = None
        current_user_name = ""
        
        if session_token:
            current_user = get_user_from_session(session_token)
            if current_user:
                current_user_name = current_user["name"]
                is_owner = current_user["name"] == name
        
        # Prepare template data with base info
        template_data = {
            "request": request,
            "name": name,
            "SERVER_URL": SERVER_URL,
            "CLIENT_URL": CLIENT_URL,
            "is_owner": is_owner,
            "logged_in": current_user is not None,
            "current_user_name": current_user_name,
            # Pass the entire CV document as cv
            "cv": cv_doc["sections"] if cv_doc and "sections" in cv_doc else {}
        }
        
        # Also add the traditional data format for backwards compatibility
        if cv_doc and "sections" in cv_doc:
            cv = cv_doc["sections"]
            
            # Map MongoDB document structure to template fields
            
            # Header (full name)
            if "first_name" in cv and "last_name" in cv:
                template_data["header"] = f"{cv['first_name']} {cv['last_name']}"
            elif "first_name" in cv:
                template_data["header"] = cv['first_name']
            elif "last_name" in cv:
                template_data["header"] = cv['last_name']
            else:
                template_data["header"] = name
                
            # Section 1 (About)
            if "summary" in cv:
                template_data["section1"] = cv["summary"]
                
            # Contact information
            if "email" in cv:
                template_data["email"] = cv["email"]
                
            if "phone" in cv:
                template_data["phone"] = cv["phone"]
                
            if "address" in cv:
                template_data["location"] = cv["address"]
            
            # Professional title
            if "job_title" in cv and cv["job_title"]:
                template_data["title"] = cv["job_title"]
            elif "work_experience" in cv and cv["work_experience"] and len(cv["work_experience"]) > 0:
                template_data["title"] = cv["work_experience"][0]["job_title"]
            
            # Work Experience
            if "work_experience" in cv and cv["work_experience"]:
                experience_html = ""
                for exp in cv["work_experience"]:
                    experience_html += f'''
                    <div class="timeline-item">
                        <div class="date">{exp.get("duration", "")}</div>
                        <h3 class="timeline-title">{exp.get("job_title", "")}</h3>
                        <div class="organization">{exp.get("company", "")}</div>
                        <p class="description">{exp.get("description", "")}</p>
                    </div>
                    '''
                template_data["experience"] = experience_html
            
            # Education
            if "education" in cv and cv["education"]:
                education_html = ""
                for edu in cv["education"]:
                    education_html += f'''
                    <div class="timeline-item">
                        <div class="date">{edu.get("year", "")}</div>
                        <h3 class="timeline-title">{edu.get("degree", "")}</h3>
                        <div class="organization">{edu.get("school", "")}</div>
                        <p class="description">{edu.get("details", "")}</p>
                    </div>
                    '''
                template_data["education"] = education_html
            
            # Skills
            if "skills" in cv and cv["skills"]:
                skills_html = ""
                for skill in cv["skills"]:
                    skills_html += f'<div class="skill-tag">{skill}</div>\n'
                template_data["skills"] = skills_html
            
            # Languages
            languages_html = ""
            if "languages" in cv and cv["languages"]:
                languages_html += '<div class="languages-list">\n'
                for lang, level in cv["languages"].items():
                    languages_html += f'''
                    <div class="language-item">
                        <span class="language-name">{lang}</span>
                        <span class="language-level">({level})</span>
                    </div>
                    '''
                languages_html += '</div>\n'
            
            # Hobbies
            hobbies_html = ""
            if "hobbies" in cv and cv["hobbies"]:
                hobbies_html += '<div class="hobbies-list">\n'
                for i, hobby in enumerate(cv["hobbies"]):
                    emoji = ["🏃", "📚", "✈️", "🎮", "🎸", "🎭", "🏊", "⚽", "🎨", "🎧"][i % 10]  # Cycle through emojis
                    hobbies_html += f'''
                    <div class="hobby-item">
                        <div class="hobby-icon">{emoji}</div>
                        <span>{hobby}</span>
                    </div>
                    '''
                hobbies_html += '</div>\n'
            
            # Certifications
            certifications_html = ""
            if "certifications" in cv and cv["certifications"]:
                certifications_html += '<div class="certifications-list">\n'
                for cert in cv["certifications"]:
                    certifications_html += f'<div class="certification-item">{cert}</div>\n'
                certifications_html += '</div>\n'
            
            # Combine languages, hobbies, certifications into section2
            combined_html = ""
            if languages_html:
                combined_html += f'<h3 class="subsection-title">Langues</h3>\n{languages_html}\n'
            if hobbies_html:
                combined_html += f'<h3 class="subsection-title">Centres d\'intérêt</h3>\n{hobbies_html}\n'
            if certifications_html:
                combined_html += f'<h3 class="subsection-title">Certifications</h3>\n{certifications_html}\n'
            
            if combined_html:
                template_data["section2"] = combined_html
            
            # Projects (if any)
            if "projects" in cv and cv["projects"]:
                projects_html = ""
                for project in cv["projects"]:
                    projects_html += f'''
                    <div class="project-item">
                        <h3 class="project-title">{project.get("title", "")}</h3>
                        <div class="project-type">{project.get("type", "")}</div>
                        <p class="project-description">{project.get("description", "")}</p>
                    </div>
                    '''
                template_data["projects"] = projects_html
                
            # Other potential sections
            if "driving_license" in cv and cv["driving_license"]:
                template_data["driving_license"] = cv["driving_license"]
                
        # Select template based on theme
        template_name = "user_template_ats.html" if theme == "ats" else "user_template.html"
        
        return templates.TemplateResponse(template_name, template_data)
        
    except Exception as e:
        logger.error(f"Error serving user page: {e}", exc_info=True)
        return HTMLResponse(content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", status_code=500)
# Web Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logger.debug("Root endpoint accessed")
    # Redirecting to login page
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=RedirectResponse)
async def login_page(request: Request, error: str = None):
    logger.debug("Login page accessed - redirecting to client app")
    
    # Check if user is already logged in
    current_user = await get_current_user(request)
    
    if current_user:
        # If already logged in, redirect to their page
        return RedirectResponse(url=f"/user/{current_user['name']}", status_code=303)
    
    # Redirect to the Streamlit client login page instead of showing an HTML template
    return RedirectResponse(url=f"{CLIENT_URL}", status_code=303)

@app.post("/login", response_class=RedirectResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    logger.debug("Login attempt")
    
    # Authenticate user
    user = authenticate_user(email, password)
    
    if not user:
        logger.debug("Login failed")
        return RedirectResponse(url="/login?error=Invalid+email+or+password", status_code=303)
    
    # Create session
    session_token = create_session(user["id"])
    
    # Create response with redirect
    response = RedirectResponse(url=f"/user/{user['name']}", status_code=303)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=30*24*60*60,  # 30 days
        path="/"
    )
    
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    logger.debug("Register page accessed")
    
    # Check if user is already logged in
    current_user = await get_current_user(request)
    
    if current_user:
        # If already logged in, redirect to their page
        return RedirectResponse(url=f"/user/{current_user['name']}", status_code=303)
    
    return templates.TemplateResponse(
        "register.html", 
        {
            "request": request,
            "error": error
        }
    )

@app.post("/register", response_class=RedirectResponse)
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...)
):
    logger.debug("Register attempt")
    
    # Validate passwords match
    if password != password_confirm:
        return RedirectResponse(url="/register?error=Passwords+do+not+match", status_code=303)
    
    try:
        # Create user
        user_id = create_user(name, email, password)
        
        # Create session
        session_token = create_session(str(user_id))
        
        # Create response with redirect
        response = RedirectResponse(url=f"/user/{name}", status_code=303)
        
        # Set cookie - change from 30 days to 10 minutes
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=10*60,  # 10 minutes in seconds
            path="/"
        )
        
        return response
    
    except HTTPException as e:
        error_message = e.detail.replace(" ", "+")
        return RedirectResponse(url=f"/register?error={error_message}", status_code=303)

@app.get("/logout", response_class=RedirectResponse)
async def logout():
    logger.debug("Logout")
    
    # Create response with redirect to login page
    response = RedirectResponse(url="/login", status_code=303)
    
    # Clear the cookie
    response.delete_cookie(key="session_token", path="/")
    
    return response

@app.get("/test", response_class=HTMLResponse)
async def test(request: Request):
    logger.debug("Test endpoint accessed")
    return HTMLResponse(content="<html><body><h1>API works!</h1></body></html>")

@app.get("/users/{name}", response_class=HTMLResponse)
@app.get("/user/{name}", response_class=HTMLResponse)
async def user_page(request: Request, name: str, theme: str = None):
    logger.debug(f"User page accessed for name: {name}, theme: {theme}")
    try:
        # Get user by username
        user = users_collection.find_one({"user_name": name})
        
        if not user:
            user_id = get_or_create_user_by_name(name)
        else:
            user_id = str(user["_id"])
        # Get CV content
        cv_doc = cvs_collection.find_one({"user_id": ObjectId(user_id)})
        
        # Check if current user is the owner of the page
        session_token = request.cookies.get("session_token")
        is_owner = False
        current_user = None
        current_user_name = ""
        
        if session_token:
            current_user = get_user_from_session(session_token)
            if current_user:
                current_user_name = current_user["name"]
                is_owner = current_user["name"] == name
        
        # Prepare template data with base info
        template_data = {
            "request": request,
            "name": name,
            "SERVER_URL": SERVER_URL,
            "CLIENT_URL": CLIENT_URL,
            "is_owner": is_owner,
            "logged_in": current_user is not None,
            "current_user_name": current_user_name
        }
        
        # No default values - only pass sections that exist in CV
        if cv_doc and "sections" in cv_doc:
            cv = cv_doc["sections"]
            
            # Map MongoDB document structure to template fields
            
            # Header (full name)
            if "first_name" in cv and "last_name" in cv:
                template_data["header"] = f"{cv['first_name']} {cv['last_name']}"
            elif "first_name" in cv:
                template_data["header"] = cv['first_name']
            elif "last_name" in cv:
                template_data["header"] = cv['last_name']
            else:
                template_data["header"] = name
                
            # Section 1 (About)
            if "summary" in cv:
                template_data["section1"] = cv["summary"]
                
            # Contact information
            if "email" in cv:
                template_data["email"] = cv["email"]
                
            if "phone" in cv:
                template_data["phone"] = cv["phone"]
                
            if "address" in cv:
                template_data["location"] = cv["address"]
            
            # Professional title
            if "job_title" in cv and cv["job_title"]:
                template_data["title"] = cv["job_title"]
            elif "work_experience" in cv and cv["work_experience"] and len(cv["work_experience"]) > 0:
                template_data["title"] = cv["work_experience"][0]["job_title"]
            
            # Work Experience
            if "work_experience" in cv and cv["work_experience"]:
                experience_html = ""
                for exp in cv["work_experience"]:
                    experience_html += f'''
                    <div class="timeline-item">
                        <div class="date">{exp.get("duration", "")}</div>
                        <h3 class="timeline-title">{exp.get("job_title", "")}</h3>
                        <div class="organization">{exp.get("company", "")}</div>
                        <p class="description">{exp.get("description", "")}</p>
                    </div>
                    '''
                template_data["experience"] = experience_html
            
            # Education
            if "education" in cv and cv["education"]:
                education_html = ""
                for edu in cv["education"]:
                    education_html += f'''
                    <div class="timeline-item">
                        <div class="date">{edu.get("year", "")}</div>
                        <h3 class="timeline-title">{edu.get("degree", "")}</h3>
                        <div class="organization">{edu.get("school", "")}</div>
                        <p class="description">{edu.get("details", "")}</p>
                    </div>
                    '''
                template_data["education"] = education_html
            
            # Skills
            if "skills" in cv and cv["skills"]:
                skills_html = ""
                for skill in cv["skills"]:
                    skills_html += f'<div class="skill-tag">{skill}</div>\n'
                template_data["skills"] = skills_html
            
            # Languages
            languages_html = ""
            if "languages" in cv and cv["languages"]:
                languages_html += '<div class="languages-list">\n'
                for lang, level in cv["languages"].items():
                    languages_html += f'''
                    <div class="language-item">
                        <span class="language-name">{lang}</span>
                        <span class="language-level">({level})</span>
                    </div>
                    '''
                languages_html += '</div>\n'
            # Hobbies
            hobbies_html = ""
            if "hobbies" in cv and cv["hobbies"]:
                hobbies_html += '<div class="hobbies-list">\n'
                for hobby in cv["hobbies"]:
                    hobbies_html += f'''
                    <div class="hobby-item">
                        <span>{hobby}</span>
                    </div>
                    '''
                hobbies_html += '</div>\n'
            
            # Certifications
            certifications_html = ""
            if "certifications" in cv and cv["certifications"]:
                certifications_html += '<div class="certifications-list">\n'
                for cert in cv["certifications"]:
                    certifications_html += f'<div class="certification-item">{cert}</div>\n'
                certifications_html += '</div>\n'
            
            # Combine languages, hobbies, certifications into section2
            combined_html = ""
            if languages_html:
                combined_html += f'<h3 class="subsection-title">Langues</h3>\n{languages_html}\n'
            if hobbies_html:
                combined_html += f'<h3 class="subsection-title">Centres d\'intérêt</h3>\n{hobbies_html}\n'
            if certifications_html:
                combined_html += f'<h3 class="subsection-title">Certifications</h3>\n{certifications_html}\n'
            
            if combined_html:
                template_data["section2"] = combined_html
            
            # Projects (if any)
            if "projects" in cv and cv["projects"]:
                projects_html = ""
                for project in cv["projects"]:
                    projects_html += f'''
                    <div class="project-item">
                        <h3 class="project-title">{project.get("title", "")}</h3>
                        <div class="project-type">{project.get("type", "")}</div>
                        <p class="project-description">{project.get("description", "")}</p>
                    </div>
                    '''
                template_data["projects"] = projects_html
                
            # Other potential sections
            if "driving_license" in cv and cv["driving_license"]:
                template_data["driving_license"] = cv["driving_license"]
                
        # Select template based on theme
        template_name = "user_template_ats.html" if theme == "ats" else "user_template.html"
        
        return templates.TemplateResponse(template_name, template_data)
        
    except Exception as e:
        logger.error(f"Error serving user page: {e}")
        return HTMLResponse(content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", status_code=500)
@app.post("/users/{name}/update", response_class=RedirectResponse)
@app.post("/user/{name}/update", response_class=RedirectResponse)
async def update_content(
    request: Request,
    name: str,
    section: str = Form(...),
    content: str = Form(...)
):
    logger.debug(f"Update content for user: {name}, section: {section}")
    
    # Check authorization - only page owner can update
    session_token = request.cookies.get("session_token")
    
    if not session_token or not is_page_owner(session_token, name):
        raise HTTPException(status_code=403, detail="You don't have permission to edit this page")
    
    # Get user
    user = users_collection.find_one({"user_name": name})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update CV section
    update_cv_section(str(user["_id"]), section, content)
    
    # Use the same path format as the request
    if request.url.path.startswith("/user/"):
        redirect_path = f"/user/{name}"
    else:
        redirect_path = f"/users/{name}"
    
    logger.debug(f"Redirecting to: {redirect_path}")
    return RedirectResponse(url=redirect_path, status_code=303)

@app.post("/users/{name}/update-field", response_class=RedirectResponse)
@app.post("/user/{name}/update-field", response_class=RedirectResponse)
async def update_field(
    request: Request,
    name: str,
    field: str = Form(...),
    content: str = Form(...)
):
    logger.debug(f"Update field for user: {name}, field: {field}")
    
    # Check authorization
    session_token = request.cookies.get("session_token")
    
    if not session_token or not is_page_owner(session_token, name):
        raise HTTPException(status_code=403, detail="You don't have permission to edit this page")
    
    # Get user
    user = users_collection.find_one({"user_name": name})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(user["_id"])
    
    # Process content based on field type
    try:
        # For fields that need to be parsed from JSON
        if field in ["skills", "hobbies", "work_experience", "education", "projects", "certifications", "languages"]:
            content_data = json.loads(content)
            update_cv_section(user_id, field, content_data)
        else:
            # For simple string fields
            update_cv_section(user_id, field, content)
    except json.JSONDecodeError:
        # If not valid JSON, just use the raw content
        update_cv_section(user_id, field, content)
    
    # Redirect back to the user's page
    if request.url.path.startswith("/user/"):
        redirect_path = f"/user/{name}"
    else:
        redirect_path = f"/users/{name}"
    
    # Add theme parameter if it exists
    theme = request.query_params.get("theme")
    if theme:
        redirect_path += f"?theme={theme}"
    
    return RedirectResponse(url=redirect_path, status_code=303)

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    # Use 0.0.0.0 to listen on all interfaces in cloud environments
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("api:app", host=host, port=port, log_level="info")