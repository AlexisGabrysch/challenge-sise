from pymongo import MongoClient

 # 📌 Connexion à MongoDB Atlas
MONGO_URI = "mongodb+srv://cv_database:YnUNdP7NqfdkSRKy@challengesise.1aioj.mongodb.net/?retryWrites=true&w=majority&appName=challengeSISE"
client = MongoClient(MONGO_URI)

# 📌 Sélection de la base de données et collection
db = client["Challenge_SISE"]
cv_collection = db["cvs"]
user_collection = db["users"]

def add_cv_to_user(email: str, cv_data: dict):
    """
    Associe un CV à un utilisateur existant basé sur son email.
    """
    user = user_collection.find_one({"email": email})
    if not user:
        print(f"❌ Aucun utilisateur trouvé avec l'email {email}.")
        return False

    user_id = user["_id"]

    existing_cv = cv_collection.find_one({"user_id": user_id})
    if existing_cv:
        print(f"⚠️ Un CV est déjà attribué à cet utilisateur.")
        return False

    cv_data["user_id"] = user_id  # Associer le CV à l'utilisateur
    cv_collection.insert_one(cv_data)
    print(f"✅ CV attribué à {email} avec succès !")
    return True
