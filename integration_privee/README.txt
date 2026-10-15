BAMBA CONTROLOR — connexion et espace privé multi-comptes

FICHIERS
- app.py : application Flask avec comptes, connexion e-mail/téléphone, mot de passe, création de société, vérification e-mail, mot de passe oublié, session privée et données isolées par compte.
- requirements.txt : dépendances Python.
- Procfile : démarrage Render.

IMPORTANT
Cette version est un ensemble source autonome basé sur le fichier app.py du projet. Ne remplacez pas votre dossier de travail actuel sans sauvegarde : si votre app.py local contient des fonctions ajoutées après cette version, fusionnez les changements au lieu de l'écraser.

VARIABLES D'ENVIRONNEMENT À CONFIGURER SUR RENDER
- FLASK_SECRET_KEY : longue valeur aléatoire et stable.
- MAIL_SERVER : serveur SMTP du fournisseur e-mail.
- MAIL_PORT : généralement 587.
- MAIL_USERNAME : compte SMTP.
- MAIL_PASSWORD : mot de passe SMTP ou mot de passe d'application.
- MAIL_FROM : adresse d'envoi autorisée.
- PUBLIC_BASE_URL : URL publique HTTPS de l'application.
- BAMBA_ACCOUNTS_DB : chemin de la base des comptes, facultatif.
- BAMBA_TENANTS_DIR : dossier persistant des bases privées par compte, facultatif.

ISOLATION
Après connexion, db_conn() utilise data/comptes/compte_ID.db pour l'utilisateur connecté. Les pages métier doivent continuer à passer par db_conn() et ne pas ouvrir directement bamba.db pour lire ou écrire des données privées. La base bamba.db est la base héritée/non connectée ; ses données ne sont pas automatiquement attribuées à un compte.

PERSISTANCE RENDER
Configurez un disque persistant et placez ACCOUNTS_DB et TENANTS_DIR sur ce disque. Sans disque persistant, les comptes et données SQLite peuvent disparaître lors d'un redéploiement.

DÉMARRAGE LOCAL
python -m pip install -r requirements.txt
python -m py_compile app.py
gunicorn --bind 0.0.0.0:5000 app:app

L'inscription exige un SMTP fonctionnel pour envoyer le lien de vérification. Ne publiez jamais auth_config.json, les bases SQLite, ni les secrets dans Git.
