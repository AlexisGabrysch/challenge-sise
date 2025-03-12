import bcrypt
from pymongo import MongoClient
from config import MONGO_URI
from datetime import datetime


# 📌 Connexion MongoDB Atlas
client = MongoClient(MONGO_URI)
db = client["Challenge_SISE"]
user_collection = db["users"]

def hash_password(password: str) -> str:
    """
    Hash un mot de passe avec bcrypt.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def register_user(email: str, password: str, user_name: str ):
    """
    Enregistre un utilisateur dans MongoDB Atlas avec un mot de passe sécurisé.
    """
    existing_user = user_collection.find_one({"email": email})
    if existing_user:
        print(f"⚠️ Un utilisateur avec l'email {email} existe déjà.")
        return None

    user_data = {
        "email": email,
        "password_hash": hash_password(password),
        "user_name": user_name,
        "created_at": datetime.utcnow()
    }

    user_id = user_collection.insert_one(user_data).inserted_id
    print(f"✅ Utilisateur {user_name} enregistré avec succès !")
    return user_id
