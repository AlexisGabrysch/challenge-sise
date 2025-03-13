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

from modules.ocr_extraction import extract_text_from_pdf, extract_text_from_image
from modules.llm_structuring import structure_cv_json

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
    expires = datetime.utcnow() + timedelta(days=30)
    
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
    cv = cvs_collection.find_one({"user_id": user_id})
    
    if cv:
        # Update existing CV
        cvs_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    section: content,
                    "last_updated": datetime.utcnow()
                }
            }
        )
    else:
        # Create new CV with this section
        new_cv = {
            "user_id": user_id,
            section: content,
            "last_updated": datetime.utcnow()
        }
        cvs_collection.insert_one(new_cv)

# Pydantic Models
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

# API Routes
@app.post("/api/login")
async def api_login(login_data: LoginRequest):
    """API endpoint pour la connexion"""
    logger.debug(f"API Login attempt: {login_data.email}")
    
    # Authenticate user
    user = authenticate_user(login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    session_token = create_session(user["id"])
    
    # Return user data and token
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "session_token": session_token
    }

@app.post("/api/register")
async def api_register(register_data: RegisterRequest):
    """API endpoint pour l'inscription"""
    logger.debug(f"API Register attempt: {register_data.name}, {register_data.email}")
    
    try:
        # Create user
        user_id = create_user(register_data.name, register_data.email, register_data.password)
        
        # Create session
        session_token = create_session(str(user_id))
        
        # Return user data and token
        return {
            "id": str(user_id),
            "name": register_data.name,
            "email": register_data.email,
            "session_token": session_token
        }
    
    except HTTPException as e:
        raise e
@app.get("/api/cv/{name}")
async def api_get_cv(name: str, authorization: str = Header(None)):
    """API endpoint pour récupérer les données du CV"""
    logger.debug(f"API Get CV: {name}")
    
    # Get user by username
    user = users_collection.find_one({"user_name": name})
    
    if not user:
        # Create a new user if not found
        user_id = get_or_create_user(name)
    else:
        user_id = str(user["_id"])
    
    # Get CV data from MongoDB
    cv = cvs_collection.find_one({"user_id": ObjectId(user_id)})
    
    # Get default sections if CV doesn't exist
    if not cv:
        cv = {
            "sections": {
                "header": name,
                "section1": "Développeur web passionné avec plus de 5 ans d'expérience.",
                "section2": "<div class=\"hobbies-list\">\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">🏃</div>\n        <span>Course à pied</span>\n    </div>\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">📚</div>\n        <span>Lecture</span>\n    </div>\n</div>",
                "experience": '<div class="timeline-item">\n    <div class="date">Jan 2023 - Présent</div>\n    <h3 class="timeline-title">Développeur Full Stack</h3>\n    <div class="organization">Tech Solutions Inc.</div>\n    <p class="description">Développement et maintenance d\'applications web utilisant React, Node.js et MongoDB.</p>\n</div>',
                "education": '<div class="timeline-item">\n    <div class="date">2019 - 2022</div>\n    <h3 class="timeline-title">Master en Informatique</h3>\n    <div class="organization">Université de Paris</div>\n    <p class="description">Spécialisation en développement web et applications mobiles.</p>\n</div>',
                "skills": '<div class="skill-tag">JavaScript</div>\n<div class="skill-tag">React.js</div>\n<div class="skill-tag">Node.js</div>',
                "title": "Développeur Full Stack",
                "email": f"{name}@example.com",
                "phone": "06 12 34 56 78",
                "location": "Paris, France",
                "linkedin": f"linkedin.com/in/{name}"
            }
        }
    
    # Return CV data
    return {
        "name": name,
        "header": cv["sections"].get("header", name),
        "section1": cv["sections"].get("section1", ""),
        "section2": cv["sections"].get("section2", ""),
        "experience": cv["sections"].get("experience", ""),
        "education": cv["sections"].get("education", ""),
        "skills": cv["sections"].get("skills", ""),
        "title": cv["sections"].get("title", "Développeur Full Stack"),
        "email": cv["sections"].get("email", f"{name}@example.com"),
        "phone": cv["sections"].get("phone", "06 12 34 56 78"),
        "location": cv["sections"].get("location", "Paris, France"),
        "linkedin": cv["sections"].get("linkedin", f"linkedin.com/in/{name}")
    }

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
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        contents = await file.read()
        temp_file.write(contents)
        temp_path = temp_file.name
    
    try:
        # Extract text based on file type
        file_extension = file.filename.split('.')[-1].lower()
        
        if file_extension in ['pdf']:
            text = extract_text_from_pdf(temp_path)
        elif file_extension in ['jpg', 'jpeg', 'png']:
            text = extract_text_from_image(temp_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Structure CV data with LLM
        cv_data = structure_cv_json(text)
        
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
        raise HTTPException(status_code=500, detail=f"Error processing CV: {str(e)}")
    
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)

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
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=30*24*60*60,  # 30 days
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
        cv = get_cv_content(user_id)
        
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
        
        # Prepare template data
        template_data = {
            "request": request,
            "name": name,
            "SERVER_URL": SERVER_URL,
            "CLIENT_URL": CLIENT_URL,
            "is_owner": is_owner,
            "logged_in": current_user is not None,
            "current_user_name": current_user_name
        }
        
        # Add required fields with defaults if missing
        template_data["header"] = cv.get("header") or name
        template_data["section1"] = cv.get("section1") or "Développeur web passionné avec plus de 5 ans d'expérience."
        template_data["section2"] = cv.get("section2") or '<div class="hobbies-list"><div class="hobby-item"><div class="hobby-icon">🏃</div><span>Course à pied</span></div><div class="hobby-item"><div class="hobby-icon">📚</div><span>Lecture</span></div></div>'
        
        # Add optional fields only if they exist
        for field in ["experience", "education", "skills", "title", "email", "phone", "location"]:
            if cv.get(field):
                template_data[field] = cv[field]
            else:
                # Set some defaults for basic fields
                if field == "title":
                    template_data[field] = "Développeur Full Stack"
                elif field == "email":
                    template_data[field] = f"{name}@example.com"
                elif field == "phone":
                    template_data[field] = "06 12 34 56 78" 
                elif field == "location":
                    template_data[field] = "Paris, France"
        
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


if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    # Use 0.0.0.0 to listen on all interfaces in cloud environments
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("api:app", host=host, port=port, log_level="info")