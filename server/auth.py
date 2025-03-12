import hashlib
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from connection import connect_to_mysql, execute_query, close_connection
from fastapi import HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def hash_password(password: str) -> str:
    """Hash a password for storing"""
    salt = os.urandom(32)  # A new salt for this user
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000,  # number of iterations
    )
    return salt.hex() + ':' + key.hex()

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a stored password against one provided by user"""
    if not stored_password or not provided_password:
        return False
        
    try:
        salt_hex, key_hex = stored_password.split(':')
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt,
            100000,  # number of iterations
        )
        return key.hex() == key_hex
    except Exception:
        return False

def create_user(db_config: dict, name: str, email: str, password: str) -> int:
    """Create a new user with authentication"""
    conn = connect_to_mysql(**db_config)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Check if user exists by email
        cursor.execute("SELECT id FROM logging WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        # Check if name exists
        cursor.execute("SELECT id FROM logging WHERE name = %s", (name,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create new user
        cursor.execute("INSERT INTO logging (name, email, password_hash, is_authenticated) VALUES (%s, %s, %s, TRUE)", 
                       (name, email, password_hash))
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    finally:
        cursor.close()
        close_connection(conn)

def authenticate_user(db_config: dict, email: str, password: str) -> Optional[dict]:
    """Authenticate user credentials"""
    conn = connect_to_mysql(**db_config)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get user by email
        cursor.execute("SELECT id, name, email, password_hash FROM logging WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user or not verify_password(user["password_hash"], password):
            return None
        
        return {"id": user["id"], "name": user["name"], "email": user["email"]}
    finally:
        cursor.close()
        close_connection(conn)

def create_session(db_config: dict, user_id: int) -> str:
    """Create a new session for a user"""
    conn = connect_to_mysql(**db_config)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor()
        
        # Generate session token
        session_token = str(uuid.uuid4())
        
        # Set expiration date (30 days)
        expires_at = datetime.now() + timedelta(days=30)
        
        # Delete any existing sessions for this user
        cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
        
        # Create new session
        cursor.execute(
            "INSERT INTO sessions (user_id, session_token, expires_at) VALUES (%s, %s, %s)",
            (user_id, session_token, expires_at)
        )
        conn.commit()
        
        return session_token
    finally:
        cursor.close()
        close_connection(conn)

def get_user_from_session(db_config: dict, session_token: str) -> Optional[dict]:
    """Get user details from session token"""
    conn = connect_to_mysql(**db_config)
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get session with user details
        cursor.execute("""
            SELECT u.id, u.name, u.email, s.expires_at 
            FROM sessions s
            JOIN logging u ON s.user_id = u.id
            WHERE s.session_token = %s
        """, (session_token,))
        
        result = cursor.fetchone()
        
        if not result:
            return None
            
        # Check if session has expired
        if result["expires_at"] < datetime.now():
            # Delete expired session
            cursor.execute("DELETE FROM sessions WHERE session_token = %s", (session_token,))
            conn.commit()
            return None
            
        return {
            "id": result["id"],
            "name": result["name"],
            "email": result["email"]
        }
    finally:
        cursor.close()
        close_connection(conn)

def is_page_owner(db_config: dict, session_token: str, page_name: str) -> bool:
    """Check if the user from the session is the owner of the page"""
    user = get_user_from_session(db_config, session_token)
    
    if not user:
        return False
        
    return user["name"] == page_name

async def get_current_user(request: Request, db_config: dict) -> Optional[dict]:
    """Get the current user from cookies"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        return None
        
    return get_user_from_session(db_config, session_token)