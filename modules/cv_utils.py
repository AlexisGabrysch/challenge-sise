from pymongo import MongoClient

 # 📌 Connexion à MongoDB Atlas
MONGO_URI = "mongodb+srv://cv_database:YnUNdP7NqfdkSRKy@challengesise.1aioj.mongodb.net/?retryWrites=true&w=majority&appName=challengeSISE"
client = MongoClient(MONGO_URI)

# 📌 Sélection de la base de données et collection
db = client["Challenge_SISE"]
cv_collection = db["cvs"]
user_collection = db["users"]

def add_cv_to_user(email: str, cv_fr: dict, cv_en: dict):
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

    update_result = cv_collection.update_one(
        {"email": email},
        {"$set": {"cv_fr": cv_fr, "cv_en": cv_en}},  # ✅ On stocke bien les deux versions
        upsert=True
    )

    if update_result.modified_count > 0 or update_result.upserted_id:
        print(f"✅ CV mis à jour/enregistré avec succès pour {email}")
        return True
    else:
        print(f"❌ Échec de l'enregistrement du CV pour {email}")
        return False
