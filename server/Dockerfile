FROM python:3.9-slim

WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application et les templates
COPY *.py .
COPY templates/ templates/
COPY modules/ modules/
RUN mkdir -p static

# Variables d'environnement pour Railway
# Suppression des slashes finaux pour éviter les doubles slashes dans les URLs
ENV SERVER_URL=https://challenge-sise-production-0bc4.up.railway.app
ENV CLIENT_URL=https://beneficial-liberation-production.up.railway.app
ENV PORT=8000
ENV HOST=0.0.0.0

# Pour debug - log plus détaillé
ENV LOG_LEVEL=debug

# Exposer le port FastAPI
EXPOSE 8000

# Commande de démarrage de l'application
CMD ["python", "api.py"]