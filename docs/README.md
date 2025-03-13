# CVVISION - Génération de CV en ligne via IA  

[![Deploy](https://img.shields.io/badge/Access-App-blue)](https://beneficial-liberation-production.up.railway.app/)  

Une application permettant de transformer un CV classique en une page web professionnelle, optimisée pour les recruteurs et le référencement.  

## 🌟 Fonctionnalités  
✔️ **Génération automatique** d’un CV web à partir d’un fichier téléchargé.  
✔️ **Mise en page claire et esthétique** pour une meilleure lisibilité.  
✔️ **Accès facile** via une URL unique, sans téléchargement de fichiers.
✔️ **Editable** pour plus de contrôle et d'interactivité.

## 🏗️ Stack Technique  
🔹 **OCR** : Mistral OCR pour l’extraction de texte à partir des PDF/images.  
🔹 **Modèle IA** : ministral-8B-latest pour l’analyse et la structuration du CV.  
🔹 **Base de données** : MongoDB Atlas pour stocker les informations extraites.
🔹 **Backend** : FastAPI pour gérer la connexion à la base de données.   
🔹 **Frontend** : Streamlit pour une interface simple et rapide.  
🔹 **Déploiement** : Railway pour une mise en production fluide. 

## 🎯 Pourquoi utiliser CVVISION ?  
✅ **Pour les candidats** : plus de visibilité et un CV toujours accessible.  
✅ **Pour les recruteurs** : un format standardisé et lisible en un clic.  
✅ **Pour tous** : un gain de temps et une meilleure expérience utilisateur.  

## 🔗 Accès à l’application  
[➡️ Essayez dès maintenant](https://beneficial-liberation-production.up.railway.app/)

## 🔧 Installation & Déploiement  
Si vous souhaitez exécuter l’application en local :  

### 1️) Cloner le dépôt  
```bash
git clone https://github.com/AlexisGabrysch/challenge-sise
cd votre-repo
```

### 2) Construire l’image Docker
```bash
docker build -t cvvision .
```

### 3) Lancer le conteneur
```bash
docker run -p 8501:8501 cvvision
```

## 📩 Contact & Feedback  
Des suggestions ou des retours ? Ouvrez une issue ou contactez-nous !  