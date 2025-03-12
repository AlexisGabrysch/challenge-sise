FROM python:3.9-slim

WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application et les templates
COPY *.py .
COPY templates/ templates/
RUN mkdir -p static

# Variables d'environnement pour Railway
ENV SERVER_URL=challenge-sise.railway.internal
ENV CLIENT_URL=beneficial-liberation.railway.internal
ENV PORT=8000
ENV HOST=0.0.0.0

# Exposer le port FastAPI
EXPOSE 8000

# Commande de démarrage de l'application
CMD ["python", "api.py"]