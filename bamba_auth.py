import os
import re
import hmac
import hashlib
import secrets
import sqlite3
import smtplib
import sys
from pathlib import Path
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps

from flask import (
    request, session, redirect, url_for, flash,
    render_template_string, abort
)
from werkzeug.security import generate_password_hash, check_password_hash


AUTH_DB = os.environ.get(
    "BAMBA_AUTH_DB",
    str(Path(__file__).resolve().parent / "bamba_auth.db")
)

AUTH_STYLE = """
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;
background:radial-gradient(ellipse at top,#083b83,#020817 65%);
color:#eafaff;font:15px Arial,sans-serif;padding:18px}
.card{width:100%;max-width:490px;padding:28px;border-radius:18px;
background:linear-gradient(145deg,#08234a,#031027);
border:1px solid #078cff;box-shadow:0 0 30px #007bff35}
.logo{text-align:center;color:#00eaff;font-size:29px;font-weight:900;
text-shadow:0 0 15px #00bfff;margin-bottom:5px}
.sub{text-align:center;color:#8bcfff;letter-spacing:3px;font-size:11px;
margin-bottom:24px}
h1{font-size:23px;margin-bottom:8px}
p{color:#a8cbe8;line-height:1.5}
label{display:block;color:#a8dfff;font-size:13px;margin:14px 0 7px}
input{width:100%;padding:13px;border-radius:8px;
border:1px solid #126bc0;background:#020d25;color:white}
button,.btn{display:block;width:100%;margin-top:18px;padding:13px;
border-radius:9px;border:1px solid #00dfff;
background:linear-gradient(100deg,#0765e8,#00a9d6);
color:white;font-weight:bold;text-align:center;text-decoration:none;
cursor:pointer}
a{color:#53dfff}
.notice{padding:12px;border:1px solid #087dff;border-radius:8px;
margin:12px 0;background:#071b38;overflow-wrap:anywhere}
small{color:#9cc7e9}
</style>
"""

AUTH_TEMPLATE = """
<!doctype html><html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport"
content="width=device-width,initial-scale=1">
<title>{{ title }} — BAMBA CONTROLOR</title>
""" + AUTH_STYLE + """
</head><body><main class="card">
<div class="logo">◉ BAMBA</div>
<div class="sub">CONTROLOR · ESPACE SÉCURISÉ</div>
{% with messages = get_flashed_messages() %}
{% for message in messages %}<div class="notice">{{ message }}</div>{% endfor %}
{% endwith %}
<h1>{{ title }}</h1>
{{ body|safe }}
</main></body></html>
"""


def auth_connection():
    Path(AUTH_DB).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(AUTH_DB, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=20000")
    return c


def init_auth_db():
    with auth_connection() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS accounts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            phone TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            company TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS auth_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            purpose TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(account_id) REFERENCES accounts(id)
        )
        """)
        c.execute("""
        CREATE INDEX IF NOT EXISTS idx_auth_tokens_account
        ON auth_tokens(account_id,purpose)
        """)


def token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_token(c, account_id, purpose, minutes=30):
    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(minutes=minutes)).isoformat()
    c.execute("""
        INSERT INTO auth_tokens(account_id,token_hash,purpose,expires_at)
        VALUES(?,?,?,?)
    """, (account_id, token_digest(token), purpose, expires))
    return token


def send_email(destination, subject, message):
    host = os.environ.get("SMTP_HOST", "").strip()
    username = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", username).strip()
    port = int(os.environ.get("SMTP_PORT", "587"))

    if not all((host, username, password, sender)):
        raise RuntimeError("Configuration SMTP absente.")

    mail = EmailMessage()
    mail["Subject"] = subject
    mail["From"] = sender
    mail["To"] = destination
    mail.set_content(message)

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(mail)


def issue_email(app, account, purpose):
    with auth_connection() as c:
        c.execute("""
            UPDATE auth_tokens SET used=1
            WHERE account_id=? AND purpose=? AND used=0
        """, (account["id"], purpose))
        token = make_token(
            c, account["id"], purpose,
            60 if purpose == "verify" else 20
        )

    if purpose == "verify":
        link = url_for("bamba_verify", token=token, _external=True)
        subject = "Vérification de votre compte BAMBA CONTROLOR"
        message = (
            "Bonjour " + account["owner_name"] + ",\n\n"
            "Confirmez votre adresse e-mail en ouvrant ce lien :\n"
            + link + "\n\nCe lien expire dans 60 minutes."
        )
    else:
        link = url_for("bamba_reset_password", token=token, _external=True)
        subject = "Réinitialisation du mot de passe BAMBA CONTROLOR"
        message = (
            "Bonjour " + account["owner_name"] + ",\n\n"
            "Pour choisir un nouveau mot de passe, ouvrez ce lien :\n"
            + link + "\n\nCe lien expire dans 20 minutes. "
            "Si vous n'avez rien demandé, ignorez ce message."
        )

    send_email(account["email"], subject, message)


def tenant_database_path(account_id, base_db):
    # Une base SQLite différente pour chaque compte.
    base = Path(base_db).resolve()
    folder = base.parent / "bamba_tenants"
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder / ("compte_" + str(int(account_id)) + ".db"))


def install_auth(app, app_globals):
    init_auth_db()

    original_init_db = app_globals["init_db"]
    original_db = app_globals["db"]
    base_db = app_globals["DB"]

    def private_db():
        account_id = session.get("bamba_account_id")
        if not account_id:
            raise RuntimeError(
                "Accès aux données métier sans compte connecté."
            )
        path = tenant_database_path(account_id, base_db)
        c = sqlite3.connect(path, timeout=20)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA busy_timeout=20000")
        return c

    # Les fonctions existantes de app.py utilisent ce db().
    # Leur accès aux données métier devient lié au compte connecté.
    app_globals["db"] = private_db

    initialized_tenants = set()

    def ensure_tenant_schema():
        account_id = session.get("bamba_account_id")
        if not account_id:
            raise RuntimeError("Compte requis pour initialiser la base.")

        tenant_path = tenant_database_path(account_id, base_db)
        tenant_key = str(account_id)

        if tenant_key in initialized_tenants and Path(tenant_path).exists():
            return

        previous_db_path = app_globals["DB"]
        previous_db_function = app_globals["db"]

        try:
            # Initialise le schéma dans la base de CE compte.
            app_globals["DB"] = tenant_path
            app_globals["db"] = original_db
            original_init_db()
            initialized_tenants.add(tenant_key)
        finally:
            app_globals["DB"] = previous_db_path
            app_globals["db"] = previous_db_function

    public_endpoints = {
        "bamba_login", "bamba_register", "bamba_verify",
        "bamba_forgot", "bamba_reset_password",
        "bamba_logout", "static"
    }

    @app.before_request
    def bamba_auth_guard():
        endpoint = request.endpoint
        if endpoint in public_endpoints:
            return None

        if not session.get("bamba_account_id"):
            return redirect(url_for("bamba_login", next=request.path))

        with auth_connection() as c:
            account = c.execute("""
                SELECT id,verified,active FROM accounts WHERE id=?
            """, (session["bamba_account_id"],)).fetchone()

        if not account or not account["active"]:
            session.clear()
            return redirect(url_for("bamba_login"))

        if not account["verified"]:
            session.clear()
            flash("Vérifiez votre adresse e-mail avant de vous connecter.")
            return redirect(url_for("bamba_login"))

        # Initialise uniquement la base de l'utilisateur connecté.
        ensure_tenant_schema()
        return None

    def auth_page(title, body):
        return render_template_string(
            AUTH_TEMPLATE, title=title, body=body
        )

    @app.route("/connexion", methods=["GET", "POST"])
    def bamba_login():
        if request.method == "POST":
            identity = request.form.get("identity", "").strip().lower()
            password = request.form.get("password", "")

            with auth_connection() as c:
                account = c.execute("""
                    SELECT * FROM accounts
                    WHERE lower(email)=? OR phone=?
                    LIMIT 1
                """, (identity, identity)).fetchone()

            if (
                not account
                or not check_password_hash(
                    account["password_hash"], password
                )
                or not account["active"]
            ):
                flash("Identifiants incorrects ou compte indisponible.")
            else:
                session.clear()
                session["bamba_account_id"] = account["id"]
                session["bamba_company"] = account["company"]
                session.permanent = True
                destination = request.args.get("next", "/")
                if not destination.startswith("/") or destination.startswith("//"):
                    destination = "/"
                return redirect(destination)

        body = """
        <form method="post">
        <label>E-mail ou téléphone</label>
        <input name="identity" autocomplete="username" required>
        <label>Mot de passe</label>
        <input type="password" name="password"
               autocomplete="current-password" required>
        <button type="submit">Se connecter</button>
        </form>
        <p><a href="/mot-de-passe-oublie">Mot de passe oublié ?</a></p>
        <p>Pas encore de compte ? <a href="/inscription">Créer un compte société</a></p>
        """
        return auth_page("Connexion", body)

    @app.route("/inscription", methods=["GET", "POST"])
    def bamba_register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()[:120]
            company = request.form.get("company", "").strip()[:160]
            email = request.form.get("email", "").strip().lower()
            phone = re.sub(r"[\s().-]", "", request.form.get("phone", ""))
            password = request.form.get("password", "")
            confirmation = request.form.get("confirmation", "")

            if not name or not company:
                flash("Le nom et le nom de la société sont obligatoires.")
            elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                flash("Adresse e-mail invalide.")
            elif phone and not re.fullmatch(r"\+?[0-9]{8,15}", phone):
                flash("Numéro de téléphone invalide.")
            elif len(password) < 10:
                flash("Choisissez un mot de passe d'au moins 10 caractères.")
            elif password != confirmation:
                flash("Les deux mots de passe ne correspondent pas.")
            else:
                try:
                    with auth_connection() as c:
                        cur = c.execute("""
                            INSERT INTO accounts(
                                email,phone,password_hash,company,
                                owner_name,verified,created_at
                            ) VALUES(?,?,?,?,?,1,?)
                        """, (
                            email, phone or None,
                            generate_password_hash(password),
                            company, name, datetime.utcnow().isoformat()
                        ))
                        account_id = cur.lastrowid
                        account = c.execute(
                            "SELECT * FROM accounts WHERE id=?",
                            (account_id,)
                        ).fetchone()

                    flash("Compte société créé. Vous pouvez vous connecter.")
                    return redirect(url_for("bamba_login"))
                except sqlite3.IntegrityError:
                    flash("Cet e-mail ou ce téléphone est déjà enregistré.")
                except Exception:
                    app.logger.exception("Échec de création du compte société")
                    flash("Impossible de créer le compte. Vérifiez les informations.")

        body = """
        <form method="post">
        <label>Nom complet</label>
        <input name="name" maxlength="120" required>
        <label>Nom de la société</label>
        <input name="company" maxlength="160" required>
        <label>Adresse e-mail</label>
        <input type="email" name="email" autocomplete="email" required>
        <label>Téléphone (facultatif)</label>
        <input name="phone" autocomplete="tel">
        <label>Mot de passe (10 caractères minimum)</label>
        <input type="password" name="password" minlength="10"
               autocomplete="new-password" required>
        <label>Confirmer le mot de passe</label>
        <input type="password" name="confirmation" minlength="10"
               autocomplete="new-password" required>
        <button type="submit">Créer mon compte</button>
        </form>
        <p><a href="/connexion">J'ai déjà un compte</a></p>
        """
        return auth_page("Inscription de la société", body)

    @app.route("/verification")
    def bamba_verify():
        token = request.args.get("token", "")
        digest = token_digest(token) if token else ""

        with auth_connection() as c:
            row = c.execute("""
                SELECT t.id AS token_id,t.account_id
                FROM auth_tokens t
                WHERE t.token_hash=? AND t.purpose='verify'
                  AND t.used=0 AND t.expires_at>?
            """, (digest, datetime.utcnow().isoformat())).fetchone()

            if not row:
                flash("Lien invalide ou expiré. Recommencez l'inscription.")
                return redirect(url_for("bamba_login"))

            c.execute(
                "UPDATE accounts SET verified=1 WHERE id=?",
                (row["account_id"],)
            )
            c.execute(
                "UPDATE auth_tokens SET used=1 WHERE id=?",
                (row["token_id"],)
            )

        flash("Compte vérifié. Vous pouvez maintenant vous connecter.")
        return redirect(url_for("bamba_login"))

    @app.route("/renvoyer-verification", methods=["GET", "POST"])
    def bamba_resend_verification():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            with auth_connection() as c:
                account = c.execute(
                    "SELECT * FROM accounts WHERE email=? AND active=1",
                    (email,)
                ).fetchone()

            if account and not account["verified"]:
                try:
                    issue_email(app, account, "verify")
                except Exception:
                    app.logger.exception("Échec d'envoi du lien de vérification")

            flash("Si un compte actif non vérifié correspond à cette adresse, un lien de vérification sera envoyé.")
            return redirect(url_for("bamba_resend_verification"))

        return auth_page("Renvoyer le lien de vérification", """
        <p>Indiquez l'adresse e-mail associée à votre compte.</p>
        <form method="post">
        <label>Adresse e-mail</label>
        <input type="email" name="email" required>
        <button type="submit">Renvoyer le lien</button>
        </form>
        <p><a href="/connexion">Retour à la connexion</a></p>
        """)

    @app.route("/mot-de-passe-oublie", methods=["GET", "POST"])
    def bamba_forgot():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            with auth_connection() as c:
                account = c.execute(
                    "SELECT * FROM accounts WHERE email=? AND active=1",
                    (email,)
                ).fetchone()

            # Réponse identique pour éviter de révéler les comptes existants.
            if account and account["verified"]:
                try:
                    issue_email(app, account, "reset")
                except Exception:
                    app.logger.exception("Échec d'envoi du lien de réinitialisation")

            flash(
                "Si un compte vérifié correspond à cette adresse, "
                "un lien de réinitialisation sera envoyé."
            )
            return redirect(url_for("bamba_forgot"))

        return auth_page("Mot de passe oublié", """
        <p>Indiquez l'adresse e-mail associée à votre compte.</p>
        <form method="post">
        <label>Adresse e-mail</label>
        <input type="email" name="email" required>
        <button type="submit">Envoyer le lien</button>
        </form><p><a href="/connexion">Retour à la connexion</a></p>
        """)

    @app.route("/reinitialiser", methods=["GET", "POST"])
    def bamba_reset_password():
        token = request.args.get("token", "")
        digest = token_digest(token) if token else ""

        with auth_connection() as c:
            row = c.execute("""
                SELECT t.id AS token_id,t.account_id
                FROM auth_tokens t
                JOIN accounts a ON a.id=t.account_id
                WHERE t.token_hash=? AND t.purpose='reset'
                  AND t.used=0 AND t.expires_at>?
                  AND a.verified=1 AND a.active=1
            """, (digest, datetime.utcnow().isoformat())).fetchone()

        if not row:
            flash("Lien invalide ou expiré.")
            return redirect(url_for("bamba_forgot"))

        if request.method == "POST":
            password = request.form.get("password", "")
            confirmation = request.form.get("confirmation", "")

            if len(password) < 10:
                flash("Le mot de passe doit contenir au moins 10 caractères.")
            elif password != confirmation:
                flash("Les deux mots de passe ne correspondent pas.")
            else:
                with auth_connection() as c:
                    c.execute("""
                        UPDATE accounts SET password_hash=? WHERE id=?
                    """, (
                        generate_password_hash(password),
                        row["account_id"]
                    ))
                    c.execute("""
                        UPDATE auth_tokens SET used=1
                        WHERE account_id=? AND purpose='reset'
                    """, (row["account_id"],))

                flash("Mot de passe changé. Connectez-vous.")
                return redirect(url_for("bamba_login"))

        return auth_page("Choisir un nouveau mot de passe", """
        <form method="post">
        <label>Nouveau mot de passe</label>
        <input type="password" name="password" minlength="10"
               autocomplete="new-password" required>
        <label>Confirmer le mot de passe</label>
        <input type="password" name="confirmation" minlength="10"
               autocomplete="new-password" required>
        <button type="submit">Changer le mot de passe</button>
        </form>
        """)

    @app.route("/deconnexion", methods=["GET", "POST"])
    def bamba_logout():
        session.clear()
        return redirect(url_for("bamba_login"))

    # Affiche l'entreprise connectée et la déconnexion dans le tableau.
    @app.context_processor
    def bamba_user_context():
        return {
            "bamba_company": session.get("bamba_company", ""),
            "bamba_logged_in": bool(session.get("bamba_account_id"))
        }

    # Le lien de déconnexion est disponible dans toutes les pages.
    app.jinja_env.globals["bamba_logout_url"] = "/deconnexion"

    # Les cookies de session sont protégés en HTTPS sur Render.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=(
            os.environ.get("COOKIE_SECURE", "1") == "1"
        ),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8)
    )
