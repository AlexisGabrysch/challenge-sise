from fastapi import FastAPI, Request, Form, HTTPException, Depends, Cookie, Body, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic
import uvicorn
import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

import tempfile
import os
from fastapi import UploadFile, File
from server.modules.ocr_extraction import extract_text_from_pdf, extract_text_from_image
from server.modules.llm_structuring import structure_cv_json


from connection import connect_to_mysql, execute_query, close_connection
from db_setup import setup_database
from auth import (
    authenticate_user, create_user, create_session, 
    get_user_from_session, is_page_owner, get_current_user
)

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

# MySQL connection configuration
DB_CONFIG = {
    'host': 'maglev.proxy.rlwy.net',
    'user': 'root',
    'password': 'EeXtIBwNKhAyySgijzeanMRgNAQifsmZ',
    'database': 'railway',
    'port': 40146
}

# URLs for redirects
SERVER_URL = os.getenv("SERVER_URL", "https://challenge-sise-production-0bc4.up.railway.app")
# Ajoutez cette ligne après la définition de SERVER_URL
CLIENT_URL = os.getenv("CLIENT_URL", "https://beneficial-liberation-production.up.railway.app")
logger.debug(f"CLIENT_URL: {CLIENT_URL}")

logger.debug(f"SERVER_URL: {SERVER_URL}")

# Helper to get or create user
def get_or_create_user(name: str):
    conn = connect_to_mysql(**DB_CONFIG)
    if not conn:
        logger.error("Failed to connect to database")
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Check if user exists in logging table first
        cursor.execute("SELECT id FROM logging WHERE name = %s", (name,))
        user = cursor.fetchone()
        
        if user:
            logger.debug(f"Found existing user in logging with id: {user['id']}")
            return user["id"]
            
        # If not found in logging, check the legacy users table if it exists
        try:
            cursor.execute("SELECT id FROM users WHERE name = %s", (name,))
            user = cursor.fetchone()
            
            if user:
                logger.debug(f"Found existing user in users table with id: {user['id']}")
                return user["id"]
        except Exception as e:
            # Table might not exist, ignore this error
            logger.debug(f"Could not check users table: {e}")
        
        # Create new user in logging table
        cursor.execute("INSERT INTO logging (name, email, password_hash, is_authenticated) VALUES (%s, %s, %s, FALSE)", 
                      (name, f"{name}@example.com", "temporary"))
        conn.commit()
        user_id = cursor.lastrowid
        logger.debug(f"Created new user with id: {user_id}")
        return user_id
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        close_connection(conn)

# Helper to get or create default content
def get_or_create_content(user_id: int, section_name: str, default_content: str = ""):
    conn = connect_to_mysql(**DB_CONFIG)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Check if content exists
        cursor.execute(
            "SELECT id, content FROM contents WHERE user_id = %s AND section_name = %s",
            (user_id, section_name)
        )
        content = cursor.fetchone()
        
        if content:
            return content["content"]
        
        # Create default content
        cursor.execute(
            "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
            (user_id, section_name, default_content)
        )
        conn.commit()
        return default_content
    finally:
        cursor.close()
        close_connection(conn)

# Classe pour la validation des données d'entrée
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

# --------- API JSON Routes for Streamlit Client ---------

@app.post("/api/login")
async def api_login(login_data: LoginRequest):
    """API endpoint pour la connexion"""
    logger.debug(f"API Login attempt: {login_data.email}")
    
    # Authenticate user
    user = authenticate_user(DB_CONFIG, login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    session_token = create_session(DB_CONFIG, user["id"])
    
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
        user_id = create_user(DB_CONFIG, register_data.name, register_data.email, register_data.password)
        
        # Create session
        session_token = create_session(DB_CONFIG, user_id)
        
        # Return user data and token
        return {
            "id": user_id,
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
    
    # Get or create user
    user_id = get_or_create_user(name)
    
    # Get CV content - basic info
    header_content = get_or_create_content(user_id, "header", f"{name}")
    section1_content = get_or_create_content(
        user_id, 
        "section1", 
        "Développeur web passionné avec plus de 5 ans d'expérience dans la création d'applications web modernes et réactives."
    )
    section2_content = get_or_create_content(
        user_id, 
        "section2", 
        "<div class=\"hobbies-list\">\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">🏃</div>\n        <span>Course à pied</span>\n    </div>\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">📚</div>\n        <span>Lecture</span>\n    </div>\n</div>"
    )
    
    # Get additional CV sections
    experience = get_or_create_content(
        user_id, 
        "experience", 
        '<div class="timeline-item">\n    <div class="date">Jan 2023 - Présent</div>\n    <h3 class="timeline-title">Développeur Full Stack</h3>\n    <div class="organization">Tech Solutions Inc.</div>\n    <p class="description">Développement et maintenance d\'applications web utilisant React, Node.js et MongoDB. Collaboration avec une équipe de 5 développeurs.</p>\n</div>\n<div class="timeline-item">\n    <div class="date">Mar 2021 - Déc 2022</div>\n    <h3 class="timeline-title">Développeur Front-End</h3>\n    <div class="organization">Digital Agency</div>\n    <p class="description">Conception et développement d\'interfaces utilisateur réactives et accessibles. Utilisation de HTML5, CSS3 et JavaScript.</p>\n</div>'
    )
    
    education = get_or_create_content(
        user_id, 
        "education", 
        '<div class="timeline-item">\n    <div class="date">2019 - 2022</div>\n    <h3 class="timeline-title">Master en Informatique</h3>\n    <div class="organization">Université de Paris</div>\n    <p class="description">Spécialisation en développement web et applications mobiles. Projet de fin d\'études sur l\'intelligence artificielle.</p>\n</div>\n<div class="timeline-item">\n    <div class="date">2016 - 2019</div>\n    <h3 class="timeline-title">Licence en Informatique</h3>\n    <div class="organization">Université de Lyon</div>\n    <p class="description">Formation aux fondamentaux de l\'informatique, algorithmique, bases de données et programmation.</p>\n</div>'
    )
    
    skills = get_or_create_content(
        user_id, 
        "skills", 
        '<div class="skill-tag">JavaScript</div>\n<div class="skill-tag">React.js</div>\n<div class="skill-tag">Node.js</div>\n<div class="skill-tag">HTML5</div>\n<div class="skill-tag">CSS3</div>\n<div class="skill-tag">MongoDB</div>\n<div class="skill-tag">Git</div>\n<div class="skill-tag">Docker</div>\n<div class="skill-tag">AWS</div>'
    )
    
    title = get_or_create_content(user_id, "title", "Développeur Full Stack")
    email = get_or_create_content(user_id, "email", f"{name}@example.com")
    phone = get_or_create_content(user_id, "phone", "06 12 34 56 78")
    location = get_or_create_content(user_id, "location", "Paris, France")
    linkedin = get_or_create_content(user_id, "linkedin", "linkedin.com/in/"+name)
    
    # Return CV data with all sections
    return {
        "name": name,
        "header": header_content,
        "section1": section1_content,
        "section2": section2_content,
        "experience": experience,
        "education": education,
        "skills": skills,
        "title": title,
        "email": email,
        "phone": phone,
        "location": location,
        "linkedin": linkedin
    }

@app.post("/api/cv/{name}/update")
async def api_update_cv(name: str, update_data: CVUpdateRequest, authorization: str = Header(None)):
    """API endpoint pour mettre à jour une section du CV"""
    logger.debug(f"API Update CV: {name}, Section: {update_data.section}")
    
    # Extract session token from Authorization header
    session_token = None
    if (authorization and authorization.startswith("Bearer ")):
        session_token = authorization[7:]  # Remove "Bearer " prefix
    
    # Check authorization - only page owner can update
    if not session_token or not is_page_owner(DB_CONFIG, session_token, name):
        raise HTTPException(status_code=403, detail="You don't have permission to edit this page")
    
    # Get user id
    user_id = get_or_create_user(name)
    
    # Update content
    conn = connect_to_mysql(**DB_CONFIG)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor()
        
        # Try to update existing content
        cursor.execute(
            """
            UPDATE contents 
            SET content = %s, last_updated = CURRENT_TIMESTAMP 
            WHERE user_id = %s AND section_name = %s
            """,
            (update_data.content, user_id, update_data.section)
        )
        
        # Check if any rows were updated
        if cursor.rowcount == 0:
            # If no rows were updated, insert new content
            cursor.execute(
                "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                (user_id, update_data.section, update_data.content)
            )
        
        conn.commit()
        
        return {"status": "success"}
    finally:
        conn.close()

# --------- Existing routes ---------

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logger.debug("Root endpoint accessed")
    # Redirecting to login page
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    logger.debug("Login page accessed")
    
    # Check if user is already logged in
    current_user = await get_current_user(request, DB_CONFIG)
    
    if (current_user):
        # If already logged in, redirect to their page
        return RedirectResponse(url=f"/user/{current_user['name']}", status_code=303)
    
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request,
            "error": error
        }
    )

@app.post("/login", response_class=RedirectResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    logger.debug("Login attempt")
    
    # Authenticate user
    user = authenticate_user(DB_CONFIG, email, password)
    
    if not user:
        logger.debug("Login failed")
        return RedirectResponse(url="/login?error=Invalid+email+or+password", status_code=303)
    
    # Create session
    session_token = create_session(DB_CONFIG, user["id"])
    
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
    current_user = await get_current_user(request, DB_CONFIG)
    
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
        user_id = create_user(DB_CONFIG, name, email, password)
        
        # Create session
        session_token = create_session(DB_CONFIG, user_id)
        
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

# Test endpoint
@app.get("/test", response_class=HTMLResponse)
async def test(request: Request):
    logger.debug("Test endpoint accessed")
    return HTMLResponse(content="<html><body><h1>API works!</h1></body></html>")

# Support both /users/ and /user/
@app.get("/users/{name}", response_class=HTMLResponse)
@app.get("/user/{name}", response_class=HTMLResponse)
async def user_page(request: Request, name: str):
    logger.debug(f"User page accessed for name: {name}")
    try:
        # Get or create user
        user_id = get_or_create_user(name)
        
        # Get or create default content for sections
        header_content = get_or_create_content(user_id, "header", f"{name}")
        
        section1_content = get_or_create_content(
            user_id, 
            "section1", 
            "Développeur web passionné avec plus de 5 ans d'expérience dans la création d'applications web modernes et réactives. Je suis spécialisé dans le développement full stack avec une expertise particulière en JavaScript et ses frameworks. J'aime résoudre des problèmes complexes et apprendre continuellement de nouvelles technologies."
        )
        
        section2_content = get_or_create_content(
            user_id, 
            "section2", 
            "<div class=\"hobbies-list\">\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">🏃</div>\n        <span>Course à pied</span>\n    </div>\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">📚</div>\n        <span>Lecture</span>\n    </div>\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">✈️</div>\n        <span>Voyages</span>\n    </div>\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">🎮</div>\n        <span>Jeux vidéo</span>\n    </div>\n    <div class=\"hobby-item\">\n        <div class=\"hobby-icon\">🎸</div>\n        <span>Guitare</span>\n    </div>\n</div>"
        )
        
        # Get additional CV sections
        experience = get_or_create_content(user_id, "experience", None)
        education = get_or_create_content(user_id, "education", None)
        skills = get_or_create_content(user_id, "skills", None)
        title = get_or_create_content(user_id, "title", "Développeur Full Stack")
        email = get_or_create_content(user_id, "email", f"{name}@example.com")
        phone = get_or_create_content(user_id, "phone", "06 12 34 56 78")
        location = get_or_create_content(user_id, "location", "Paris, France")
        linkedin = get_or_create_content(user_id, "linkedin", f"linkedin.com/in/{name}")
        
        # Check if current user is the owner of the page
        session_token = request.cookies.get("session_token")
        is_owner = False
        current_user = None
        current_user_name = ""
        
        if session_token:
            current_user = get_user_from_session(DB_CONFIG, session_token)
            if current_user:
                current_user_name = current_user["name"]
                is_owner = current_user["name"] == name
        
        return templates.TemplateResponse(
            "user_template.html", 
            {
                "request": request, 
                "name": name, 
                "header": header_content,
                "title": title,
                "email": email,
                "phone": phone,
                "location": location,
                "linkedin": linkedin,
                "section1": section1_content, 
                "section2": section2_content,
                "experience": experience,
                "education": education,
                "skills": skills,
                "SERVER_URL": SERVER_URL,
                "client_url": CLIENT_URL,
                "is_owner": is_owner,
                "logged_in": session_token is not None,
                "current_user_name": current_user_name
            }
        )
    except Exception as e:
        logger.error(f"Error serving user page: {e}")
        return HTMLResponse(content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", status_code=500)

# Support both paths for updates
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
    
    if not session_token or not is_page_owner(DB_CONFIG, session_token, name):
        raise HTTPException(status_code=403, detail="You don't have permission to edit this page")
    
    conn = connect_to_mysql(**DB_CONFIG)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get user id from logging
        cursor.execute("SELECT id FROM logging WHERE name = %s", (name,))
        user = cursor.fetchone()
        
        if not user:
            # Try legacy users table as fallback
            try:
                cursor.execute("SELECT id FROM users WHERE name = %s", (name,))
                user = cursor.fetchone()
            except Exception:
                pass
                
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Try to update existing content
        cursor.execute(
            """
            UPDATE contents 
            SET content = %s, last_updated = CURRENT_TIMESTAMP 
            WHERE user_id = %s AND section_name = %s
            """,
            (content, user_id, section)
        )
        
        # Check if any rows were updated
        if cursor.rowcount == 0:
            # If no rows were updated, insert new content
            cursor.execute(
                "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                (user_id, section, content)
            )
        
        conn.commit()
        
        # Use the same path format as the request
        if request.url.path.startswith("/user/"):
            redirect_path = f"/user/{name}"
        else:
            redirect_path = f"/users/{name}"
        
        logger.debug(f"Redirecting to: {redirect_path}")
        return RedirectResponse(url=redirect_path, status_code=303)
    finally:
        cursor.close()
        close_connection(conn)


# Add these imports at the top of the file
import tempfile
import os
from fastapi import UploadFile, File
from modules.ocr_extraction import extract_text_from_pdf, extract_text_from_image
from modules.llm_structuring import structure_cv_json

# Add this new endpoint to your FastAPI application
@app.post("/api/cv/{name}/upload")
async def api_upload_cv(name: str, file: UploadFile = File(...), authorization: str = Header(None)):
    """API endpoint for uploading and processing a CV file"""
    logger.debug(f"API Upload CV: {name}, File: {file.filename}")
    
    # Extract session token from Authorization header
    session_token = None
    if (authorization and authorization.startswith("Bearer ")):
        session_token = authorization[7:]  # Remove "Bearer " prefix
    
    # Check authorization - only page owner can update
    if not session_token or not is_page_owner(DB_CONFIG, session_token, name):
        raise HTTPException(status_code=403, detail="You don't have permission to upload for this user")
    
    # Get user id
    user_id = get_or_create_user(name)
    
    # Check file type
    file_extension = file.filename.split('.')[-1].lower()
    allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
    
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_extension}. Please upload PDF, JPEG, or PNG.")
    
    try:
        # Save the uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            # Read file
            contents = await file.read()
            temp_file.write(contents)
            temp_file_path = temp_file.name
            
        # Process the file with OCR based on file type
        if file_extension == 'pdf':
            ocr_text = extract_text_from_pdf(temp_file_path)
        else:  # jpg, jpeg, png
            ocr_text = extract_text_from_image(temp_file_path)
            
        # Structure the CV text using Mistral
        structured_cv = structure_cv_json(ocr_text)
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        # Update CV sections in the database
        conn = connect_to_mysql(**DB_CONFIG)
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection error")
            
        try:
            cursor = conn.cursor()
            
            # Map the structured CV data to our sections
            # We'll set basic fields like header, section1, etc. based on the structured data
            
            # Extract name for header
            if structured_cv.get("first_name") and structured_cv.get("last_name"):
                header = f"{structured_cv['first_name']} {structured_cv['last_name']}"
            else:
                header = name.capitalize()  # Default to the username if no name found
            
            # Update header
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (header, user_id, "header")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "header", header)
                )
            
            # Create About section (section1) from structured data
            about_section = ""
            
            # Add introduction if we have educational background
            if structured_cv.get("education"):
                highest_edu = structured_cv["education"][0]  # Assuming education is sorted with most recent first
                about_section += f"Professional with education in {highest_edu.get('degree', 'higher education')} "
                about_section += f"from {highest_edu.get('school', 'a recognized institution')}. "
                
            # Add work experience summary
            if structured_cv.get("work_experience"):
                latest_job = structured_cv["work_experience"][0]  # Assuming work experience is sorted
                about_section += f"Experienced {latest_job.get('job_title', 'professional')} "
                about_section += f"with background at {latest_job.get('company', 'reputable organizations')}. "
                
            # Add skills summary
            if structured_cv.get("skills") and len(structured_cv["skills"]) > 0:
                about_section += f"Skilled in {', '.join(structured_cv['skills'][:5])}."
                
            # Update section1
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (about_section, user_id, "section1")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "section1", about_section)
                )
                
            # Create hobbies/interests section (section2)
            hobbies_html = "<div class=\"hobbies-list\">\n"
            
            # Add hobbies with emojis
            hobby_emojis = {"sports": "🏃", "reading": "📚", "travel": "✈️", 
                           "music": "🎵", "cooking": "🍳", "photography": "📷",
                           "art": "🎨", "gaming": "🎮", "languages": "🗣️"}
                           
            if structured_cv.get("hobbies"):
                for hobby in structured_cv["hobbies"]:
                    emoji = "🔍"  # Default emoji
                    for keyword, emoji_char in hobby_emojis.items():
                        if keyword.lower() in hobby.lower():
                            emoji = emoji_char
                            break
                            
                    hobbies_html += f"""    <div class="hobby-item">
        <div class="hobby-icon">{emoji}</div>
        <span>{hobby}</span>
    </div>\n"""
            
            # If no hobbies found, add languages as additional info
            elif structured_cv.get("languages"):
                for lang, level in structured_cv["languages"].items():
                    hobbies_html += f"""    <div class="hobby-item">
        <div class="hobby-icon">🗣️</div>
        <span>{lang} ({level})</span>
    </div>\n"""
            
            hobbies_html += "</div>"
            
            # Update section2
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (hobbies_html, user_id, "section2")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "section2", hobbies_html)
                )
                
            # Create experience timeline HTML
            experience_html = ""
            if structured_cv.get("work_experience"):
                for job in structured_cv["work_experience"]:
                    experience_html += f"""<div class="timeline-item">
    <div class="date">{job.get('duration', 'N/A')}</div>
    <h3 class="timeline-title">{job.get('job_title', 'Role')}</h3>
    <div class="organization">{job.get('company', 'Company')}</div>
    <p class="description">{job.get('description', '')}</p>
</div>\n"""
            
            # Update experience
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (experience_html, user_id, "experience")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "experience", experience_html)
                )
                
            # Create education timeline HTML
            education_html = ""
            if structured_cv.get("education"):
                for edu in structured_cv["education"]:
                    education_html += f"""<div class="timeline-item">
    <div class="date">{edu.get('year', 'N/A')}</div>
    <h3 class="timeline-title">{edu.get('degree', 'Degree')}</h3>
    <div class="organization">{edu.get('school', 'Institution')}</div>
    <p class="description">{edu.get('details', '')}</p>
</div>\n"""
                
            # Update education
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (education_html, user_id, "education")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "education", education_html)
                )
                
            # Create skills HTML
            skills_html = ""
            if structured_cv.get("skills"):
                for skill in structured_cv["skills"]:
                    skills_html += f'<div class="skill-tag">{skill}</div>\n'
                    
            # Update skills
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (skills_html, user_id, "skills")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "skills", skills_html)
                )
                
            # Update additional fields
            # Title
            job_title = "Professional"
            if structured_cv.get("work_experience") and structured_cv["work_experience"]:
                job_title = structured_cv["work_experience"][0].get("job_title", "Professional")
                
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (job_title, user_id, "title")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "title", job_title)
                )
                
            # Email
            email_value = structured_cv.get("email", f"{name}@example.com")
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (email_value, user_id, "email")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "email", email_value)
                )
                
            # Phone
            phone_value = structured_cv.get("phone", "")
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (phone_value, user_id, "phone")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "phone", phone_value)
                )
                
            # Location
            location_value = structured_cv.get("address", "")
            cursor.execute(
                """
                UPDATE contents 
                SET content = %s, last_updated = CURRENT_TIMESTAMP 
                WHERE user_id = %s AND section_name = %s
                """,
                (location_value, user_id, "location")
            )
            
            if cursor.rowcount == 0:
                cursor.execute(
                    "INSERT INTO contents (user_id, section_name, content) VALUES (%s, %s, %s)",
                    (user_id, "location", location_value)
                )
            
            conn.commit()
            
            return {
                "status": "success", 
                "message": f"CV processed successfully for {name}",
                "sections_updated": ["header", "section1", "section2", "experience", "education", "skills", 
                                   "title", "email", "phone", "location"]
            }
            
        finally:
            cursor.close()
            close_connection(conn)
            
    except Exception as e:
        logger.error(f"Error processing CV file: {str(e)}")
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Error processing CV: {str(e)}")








# Setup database tables when the application starts
@app.on_event("startup")
async def startup_event():
    logger.info("Starting application, setting up database...")
    try:
        setup_database()
        logger.info("Database setup complete")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")

















if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    # Use 0.0.0.0 to listen on all interfaces in cloud environments
    host = os.getenv("HOST", "0.0.0.0")
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("api:app", host=host, port=port, log_level="info")