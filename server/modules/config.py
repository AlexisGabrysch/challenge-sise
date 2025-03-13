import os
# API_KEY = os.getenv("MISTRAL_API_KEY")
API_KEY = "ASMLrTY6XqnGK6S4tzT6h4loleMuXZL9"
MONGO_URI = "mongodb+srv://cv_database:YnUNdP7NqfdkSRKy@challengesise.1aioj.mongodb.net/?retryWrites=true&w=majority&appName=challengeSISE"

if not API_KEY:
    raise ValueError("Clé API MISTRAL_API_KEY non trouvée dans les variables d'environnement.")


