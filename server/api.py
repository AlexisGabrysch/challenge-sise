from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
from typing import Dict, Any, Optional
from connection import connect_to_mysql, execute_query, close_connection
from db_setup import setup_database

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

# MySQL connection configuration
DB_CONFIG = {
    'host': 'maglev.proxy.rlwy.net',
    'user': 'root',
    'password': 'EeXtIBwNKhAyySgijzeanMRgNAQifsmZ',
    'database': 'railway',
    'port': 40146
}

# URLs for redirects - Ne pas utiliser ici car cause des problèmes de redirection interne
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
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE name = %s", (name,))
        user = cursor.fetchone()
        
        if user:
            logger.debug(f"Found existing user with id: {user['id']}")
            return user["id"]
        
        # Create new user
        cursor.execute("INSERT INTO users (name) VALUES (%s)", (name,))
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
            "SELECT id, content FROM user_content WHERE user_id = %s AND section_name = %s",
            (user_id, section_name)
        )
        content = cursor.fetchone()
        
        if content:
            return content["content"]
        
        # Create default content
        cursor.execute(
            "INSERT INTO user_content (user_id, section_name, content) VALUES (%s, %s, %s)",
            (user_id, section_name, default_content)
        )
        conn.commit()
        return default_content
    finally:
        cursor.close()
        close_connection(conn)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    logger.debug("Root endpoint accessed")
    # Au lieu de rediriger, afficher une page d'accueil simple
    html_content = """
    <html>
        <head>
            <title>Personal Pages API</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                    text-align: center;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                }
                h1 {
                    color: #FF4B4B;
                }
                p {
                    line-height: 1.6;
                }
                .btn {
                    display: inline-block;
                    padding: 10px 20px;
                    margin: 10px;
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 5px;
                    text-decoration: none;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to Personal Pages API</h1>
                <p>This API allows you to create and manage personal pages with customizable content.</p>
                <p>To view a user's page, use the following URL pattern:</p>
                <code>/user/{name}</code>
                <p>Example:</p>
                <a href="/user/alexis" class="btn">View Alexis' Page</a>
                <p>You can test the API's health by visiting:</p>
                <a href="/test" class="btn">Test API</a>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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
        
        return templates.TemplateResponse(
            "user_template.html", 
            {
                "request": request, 
                "name": name, 
                "header": header_content,
                "section1": section1_content, 
                "section2": section2_content,
                "client_url": SERVER_URL  # Utilisez SERVER_URL comme page de retour
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
    conn = connect_to_mysql(**DB_CONFIG)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get user id
        cursor.execute("SELECT id FROM users WHERE name = %s", (name,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        
        # Try to update existing content
        cursor.execute(
            """
            UPDATE user_content 
            SET content = %s, last_updated = CURRENT_TIMESTAMP 
            WHERE user_id = %s AND section_name = %s
            """,
            (content, user_id, section)
        )
        
        # Check if any rows were updated
        if cursor.rowcount == 0:
            # If no rows were updated, insert new content
            cursor.execute(
                "INSERT INTO user_content (user_id, section_name, content) VALUES (%s, %s, %s)",
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