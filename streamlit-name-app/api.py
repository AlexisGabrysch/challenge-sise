from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import mysql.connector
from mysql.connector import Error
import uvicorn
import os
from typing import Dict, Any, Optional
from db_connection import get_mysql_connection, setup_database

app = FastAPI()

# Create directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Setup Jinja2 templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Streamlit URL - update with your deployed URL
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "https://challenge-sise-fhnm3twfkndvfhhybh8f7w.streamlit.app")

# Helper to get or create user
async def get_or_create_user(name: str):
    conn = get_mysql_connection()
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
        conn.close()

# Helper to get or create default content
async def get_or_create_content(user_id: int, section_name: str, default_content: str = ""):
    conn = get_mysql_connection()
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
        conn.close()

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Redirect to Streamlit app
    html_content = f"""
    <html>
        <head>
            <title>Redirecting...</title>
            <meta http-equiv="refresh" content="0;url={STREAMLIT_URL}" />
        </head>
        <body>
            <p>Redirecting to the Streamlit app...</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/users/{name}", response_class=HTMLResponse)
async def user_page(request: Request, name: str):
    # Get or create user
    user_id = await get_or_create_user(name)
    
    # Get or create default content for sections
    header_content = await get_or_create_content(user_id, "header", f"Welcome to {name}'s Page")
    
    section1_content = await get_or_create_content(
        user_id, 
        "section1", 
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed eget efficitur magna. Suspendisse potenti."
    )
    
    section2_content = await get_or_create_content(
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
            "streamlit_url": STREAMLIT_URL  # Pass Streamlit URL to template
        }
    )

@app.post("/users/{name}/update", response_class=RedirectResponse)
async def update_content(
    request: Request,
    name: str,
    section: str = Form(...),
    content: str = Form(...)
):
    conn = get_mysql_connection()
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
        
        # Redirect back to user page
        return RedirectResponse(url=f"/users/{name}", status_code=303)
    finally:
        cursor.close()
        conn.close()

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