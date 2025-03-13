import hashlib
import os
import uuid
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pymongo import MongoClient
from bson import ObjectId

security = HTTPBasic()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["Challenge_SISE"]
users_collection = db["users"]      # Collection of users
sessions_collection = db["sessions"]  # Collection for sessions

def hash_password(password: str) -> str:
    """Hash a password for storing using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a stored password against one provided by user using bcrypt"""
    if not stored_password or not provided_password:
        return False
        
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))
    except Exception:
        return False

def create_user(name: str, email: str, password: str) -> str:
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
    return str(result.inserted_id)

def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Authenticate user credentials"""
    user = users_collection.find_one({"email": email})
    
    if not user or not verify_password(user["password_hash"], password):
        return None
    
    return {
        "id": str(user["_id"]),
        "name": user["user_name"],
        "email": user["email"]
    }

def create_session(user_id: str) -> str:
    """Create a new session for a user"""
    # Generate session token
    session_token = str(uuid.uuid4())
        
    # Set expiration date (30 days)
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    # Delete any existing sessions for this user
    sessions_collection.delete_many({"user_id": ObjectId(user_id)})
    
    # Create new session
    session_data = {
        "user_id": ObjectId(user_id),
        "session_token": session_token,
        "expires_at": expires_at
    }
    sessions_collection.insert_one(session_data)
    
    return session_token

def get_user_from_session(session_token: str) -> Optional[dict]:
    """Get user details from session token"""
    # Get session
    session = sessions_collection.find_one({"session_token": session_token})
        
    if not session:
        return None
        
    # Check if session has expired
    if session["expires_at"] < datetime.utcnow():
        # Delete expired session
        sessions_collection.delete_one({"session_token": session_token})
        return None
    
    # Get user
    user = users_collection.find_one({"_id": session["user_id"]})
    
    if not user:
        return None
        
    return {
        "id": str(user["_id"]),
        "name": user["user_name"],
        "email": user["email"]
    }

def is_page_owner(session_token: str, page_name: str) -> bool:
    """Check if the user from the session is the owner of the page"""
    user = get_user_from_session(session_token)
    
    if not user:
        return False
        
    return user["name"] == page_name

async def get_current_user(request: Request) -> Optional[dict]:
    """Get the current user from cookies"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        return None
        
    return get_user_from_session(session_token)