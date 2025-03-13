import os
API_KEY = os.getenv("MISTRAL_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

if not API_KEY:
    raise ValueError("Clé API MISTRAL_API_KEY non trouvée dans les variables d'environnement.")


