FROM python:3.9-slim

WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le dossier assets
COPY assets /app/assets/
COPY .streamlit/ /app/.streamlit/

# Copier le code de l'application
COPY app.py .






# Variable d'environnement pour Railway
# Suppression des slashes finaux pour éviter les doubles slashes dans les URLs
ENV SERVER_URL=https://challenge-sise-production-0bc4.up.railway.app
ENV CLIENT_URL=https://beneficial-liberation-production.up.railway.app
ENV MONGO_URL=mongodb+srv://cv_database:YnUNdP7NqfdkSRKy@challengesise.1aioj.mongodb.net/?retryWrites=true&w=majority&appName=challengeSISE
# Exposer le port Streamlit
EXPOSE 8501

# Commande de démarrage de l'application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]