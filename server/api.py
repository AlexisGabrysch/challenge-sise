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

logger.debug(f"SERVER_URL: {SERVER_URL}")

# Helper to get or create user
def get_or_create_user(name: str):
    conn = connect_to_mysql(**DB_CONFIG)
    if not conn:
        logger.error("Failed to connect to database")
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Check if user exists in users_login table first
        cursor.execute("SELECT id FROM users_login WHERE name = %s", (name,))
        user = cursor.fetchone()
        
        if user:
            logger.debug(f"Found existing user in users_login with id: {user['id']}")
            return user["id"]
            
        # If not found in users_login, check the legacy users table if it exists
        try:
            cursor.execute("SELECT id FROM users WHERE name = %s", (name,))
            user = cursor.fetchone()
            
            if user:
                logger.debug(f"Found existing user in users table with id: {user['id']}")
                return user["id"]
        except Exception as e:
            # Table might not exist, ignore this error
            logger.debug(f"Could not check users table: {e}")
        
        # Create new user in users_login table
        cursor.execute("INSERT INTO users_login (name, email, password_hash, is_authenticated) VALUES (%s, %s, %s, FALSE)", 
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
            "SELECT id, content FROM users_content WHERE user_id = %s AND section_name = %s",
            (user_id, section_name)
        )
        content = cursor.fetchone()
        
        if content:
            return content["content"]
        
        # Create default content
        cursor.execute(
            "INSERT INTO users_content (user_id, section_name, content) VALUES (%s, %s, %s)",
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
    
    # Get CV content
    header_content = get_or_create_content(user_id, "header", f"Welcome to {name}'s Page")
    section1_content = get_or_create_content(
        user_id, 
        "section1", 
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
    )
    section2_content = get_or_create_content(
        user_id, 
        "section2", 
        "Donec ullamcorper nulla non metus auctor fringilla."
    )
    
    # Return CV data
    return {
        "name": name,
        "header": header_content,
        "section1": section1_content,
        "section2": section2_content
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
            UPDATE users_content 
            SET content = %s, last_updated = CURRENT_TIMESTAMP 
            WHERE user_id = %s AND section_name = %s
            """,
            (update_data.content, user_id, update_data.section)
        )
        
        # Check if any rows were updated
        if cursor.rowcount == 0:
            # If no rows were updated, insert new content
            cursor.execute(
                "INSERT INTO users_content (user_id, section_name, content) VALUES (%s, %s, %s)",
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
        header_content = get_or_create_content(user_id, "header", f"Welcome to {name}'s Page")
        
        section1_content = get_or_create_content(
            user_id, 
            "section1", 
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed eget efficitur magna. Suspendisse potenti."
        )
        
        section2_content = get_or_create_content(
            user_id, 
            "section2", 
            "Donec ullamcorper nulla non metus auctor fringilla. Vestibulum id ligula porta felis euismod semper."
        )
        
        # Check if current user is the owner of the page
        session_token = request.cookies.get("session_token")
        is_owner = False
        
        if session_token:
            is_owner = is_page_owner(DB_CONFIG, session_token, name)
        
        return templates.TemplateResponse(
            "user_template.html", 
            {
                "request": request, 
                "name": name, 
                "header": header_content,
                "section1": section1_content, 
                "section2": section2_content,
                "client_url": SERVER_URL,
                "is_owner": is_owner,
                "logged_in": session_token is not None
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
        
        # Get user id from users_login
        cursor.execute("SELECT id FROM users_login WHERE name = %s", (name,))
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
            UPDATE users_content 
            SET content = %s, last_updated = CURRENT_TIMESTAMP 
            WHERE user_id = %s AND section_name = %s
            """,
            (content, user_id, section)
        )
        
        # Check if any rows were updated
        if cursor.rowcount == 0:
            # If no rows were updated, insert new content
            cursor.execute(
                "INSERT INTO users_content (user_id, section_name, content) VALUES (%s, %s, %s)",
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