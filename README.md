# BAMBA-CONTROLOR

Application web de gestion Wi-Fi, des abonnements et des tickets.

## Technologies
- Python
- Flask
- SQLite
- Interface web installable (PWA)

## Installation locale avec Termux

```bash
pip install -r requirements.txt
python app.py
```

Ouvrir ensuite l'adresse locale indiquée par Flask.

## Déploiement en ligne

Le serveur doit utiliser une commande de démarrage compatible avec Gunicorn :

```bash
gunicorn --bind 0.0.0.0:$PORT app:app
```

## Configuration importante

- Définir une clé secrète Flask sécurisée.
- Configurer les paramètres d'authentification dans l'environnement du serveur.
- Utiliser un stockage persistant pour la base de données SQLite.
- Configurer les clés de paiement et les paramètres du routeur avant d'activer ces services.

Ne jamais publier les mots de passe, les clés API, les fichiers de configuration privés ou la base de données.

## Projet

BAMBA-CONTROLOR — gestion et administration Wi-Fi.
