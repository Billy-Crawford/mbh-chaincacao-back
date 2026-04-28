#!/usr/bin/env bash
# Arrêter le script en cas d'erreur
set -o errexit

# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Collecter les fichiers statiques (CSS, JS, Images)
# C'est ce qui permet à l'admin Django d'avoir un beau design sur Render
python manage.py collectstatic --no-input

# 3. Appliquer les migrations à la base de données (Neon/Postgres)
python manage.py migrate

