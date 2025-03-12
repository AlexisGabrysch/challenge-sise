FROM python:3.9-slim

WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY app.py .

# Variable d'environnement pour Railway
ENV SERVER_URL=https://challenge-sise-production.up.railway.app
ENV CLIENT_URL=https://challenge-sise-client.up.railway.app

# Exposer le port Streamlit
EXPOSE 8501

# Commande de démarrage de l'application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]