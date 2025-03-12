import os
API_KEY = os.getenv("MISTRAL_API_KEY")

if not API_KEY:
    raise ValueError("Clé API MISTRAL_API_KEY non trouvée dans les variables d'environnement.")
