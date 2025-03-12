from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import Dict, Any, Optional
from connection import connect_to_mysql, execute_query, close_connection
from db_setup import setup_database

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

# URLs for redirects
CLIENT_URL = os.getenv("CLIENT_URL", "https://challenge-sise-client.up.railway.app")
SERVER_URL = os.getenv("SERVER_URL", "https://challenge-sise-production.up.railway.app")

# Helper to get or create user
def get_or_create_user(name: str):
    conn = connect_to_mysql(**DB_CONFIG)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE name = %s", (name,))
        user = cursor.fetchone()
        
        if user:
            return user["id"]
        
        # Create new user
        cursor.execute("INSERT INTO users (name) VALUES (%s)", (name,))
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
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
    # Redirect to Client app
    html_content = f"""
    <html>
        <head>
            <title>Redirecting...</title>
            <meta http-equiv="refresh" content="0;url={CLIENT_URL}" />
        </head>
        <body>
            <p>Redirecting to the app...</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Ajoutez cette route pour gérer également les requêtes sur /users/{name}
@app.get("/users/{name}", response_class=HTMLResponse)
async def legacy_user_page(request: Request, name: str):
    # Rediriger vers le nouveau chemin /user/{name}
    return RedirectResponse(url=f"/user/{name}")

@app.get("/user/{name}", response_class=HTMLResponse)
async def user_page(request: Request, name: str):
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
            "client_url": CLIENT_URL  # Pass Client URL to template
        }
    )

# Ajoutez cette route pour gérer les requêtes sur l'ancien chemin
@app.post("/users/{name}/update", response_class=RedirectResponse)
async def legacy_update_content(
    request: Request,
    name: str,
    section: str = Form(...),
    content: str = Form(...)
):
    # Redirigez vers la nouvelle route pour la compatibilité
    result = await update_content(request, name, section, content)
    return result

@app.post("/user/{name}/update", response_class=RedirectResponse)
async def update_content(
    request: Request,
    name: str,
    section: str = Form(...),
    content: str = Form(...)
):
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
        
        # Redirect back to user page - changed to /user/ from /users/
        return RedirectResponse(url=f"/user/{name}", status_code=303)
    finally:
        cursor.close()
        close_connection(conn)

# Setup database tables when the application starts
@app.on_event("startup")
async def startup_event():
    setup_database()

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    # Use 0.0.0.0 to listen on all interfaces in cloud environments
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("api:app", host=host, port=port, log_level="info")