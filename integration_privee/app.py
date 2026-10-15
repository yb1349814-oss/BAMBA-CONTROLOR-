import os
import json
import hmac
import hashlib
import secrets
import sqlite3
import csv
import io
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template_string, request, redirect, url_for,
    session, abort, flash
)
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = Path(__file__).resolve().parent
DB = Path(os.environ.get("BAMBA_DB_PATH", str(BASE_DIR / "bamba.db")))
AUTH_FILE = Path(os.environ.get("BAMBA_AUTH_FILE", str(BASE_DIR / "auth_config.json")))

app = Flask(__name__)
# Render terminates HTTPS at its proxy; trust its forwarded scheme/host for secure links.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["PREFERRED_URL_SCHEME"] = "https"
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1").lower() not in {"0", "false", "no"},
    PERMANENT_SESSION_LIFETIME=60 * 60 * 12,
)
if not app.config["SECRET_KEY"]:
    # Development fallback only. Set FLASK_SECRET_KEY in Render for stable secure sessions.
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    print("ATTENTION: FLASK_SECRET_KEY absent; configure-la dans Render pour conserver les sessions après redémarrage.")

ACCOUNTS_DB = Path(os.environ.get("BAMBA_ACCOUNTS_DB", str(BASE_DIR / "accounts.db")))
TENANTS_DIR = Path(os.environ.get("BAMBA_TENANTS_DIR", str(BASE_DIR / "data" / "comptes")))

MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_FROM = os.environ.get("MAIL_FROM", MAIL_USERNAME)
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1").lower() not in {"0", "false", "no"}


DEFAULTS = {
    "ticket_price": "100",
    "commission_percent": "10",
    "event_name": "BAMBA-CONTROLOR",
    "currency": "FCFA",
    "selected_plan": "Max",
    "subscription_status": "Essai gratuit",
    "trial_start": "",
}

def tenant_db_path(user_id):
    TENANTS_DIR.mkdir(parents=True, exist_ok=True)
    return TENANTS_DIR / f"compte_{int(user_id)}.db"

def db_conn():
    # All legacy business routes use this function. Once authenticated, every query
    # is automatically confined to that account's own SQLite database.
    path = tenant_db_path(session["user_id"]) if session.get("user_id") else DB
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def accounts_conn():
    ACCOUNTS_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ACCOUNTS_DB, timeout=20)
    con.row_factory = sqlite3.Row
    return con

def init_accounts_db():
    with accounts_conn() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS accounts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            phone TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            company TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS account_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            purpose TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_account_tokens_lookup ON account_tokens(token_hash,purpose,used)")

def init_db(db_path=None):
    path = Path(db_path) if db_path else DB
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    with con:
        con.execute("""CREATE TABLE IF NOT EXISTS vendeurs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            actif INTEGER NOT NULL DEFAULT 1
        )""")
        # Migrate older database that only had id and nom.
        seller_cols = {r["name"] for r in con.execute("PRAGMA table_info(vendeurs)")}
        if "actif" not in seller_cols:
            con.execute("ALTER TABLE vendeurs ADD COLUMN actif INTEGER NOT NULL DEFAULT 1")

        con.execute("""CREATE TABLE IF NOT EXISTS ventes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            vendeur_id INTEGER NOT NULL,
            quantite INTEGER NOT NULL,
            total INTEGER NOT NULL,
            commission INTEGER NOT NULL,
            statut TEXT NOT NULL DEFAULT 'valide',
            FOREIGN KEY(vendeur_id) REFERENCES vendeurs(id)
        )""")
        sale_cols = {r["name"] for r in con.execute("PRAGMA table_info(ventes)")}
        if "statut" not in sale_cols:
            con.execute("ALTER TABLE ventes ADD COLUMN statut TEXT NOT NULL DEFAULT 'valide'")

        con.execute("""CREATE TABLE IF NOT EXISTS parametres(
            cle TEXT PRIMARY KEY,
            valeur TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            vente_id INTEGER,
            cree_le TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'valide',
            utilise_le TEXT,
            FOREIGN KEY(vente_id) REFERENCES ventes(id)
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS operations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            montant INTEGER NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'enregistre'
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS sites(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            localisation TEXT NOT NULL DEFAULT '',
            routeurs INTEGER NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'actif',
            cree_le TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS paiements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            montant INTEGER NOT NULL,
            methode TEXT NOT NULL,
            reference TEXT NOT NULL DEFAULT '',
            statut TEXT NOT NULL DEFAULT 'en_attente'
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS import_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            fichier TEXT NOT NULL,
            importes INTEGER NOT NULL DEFAULT 0
        )""")
        for key, value in DEFAULTS.items():
            con.execute("INSERT OR IGNORE INTO parametres(cle,valeur) VALUES(?,?)", (key, value))
        con.execute("INSERT OR IGNORE INTO vendeurs(nom,actif) VALUES(?,1)", ("Vendeur principal",))
        con.commit()
    con.close()

init_accounts_db()
init_db()

PLANS = [
    {"nom": "Starter", "prix": 4000, "sites": 1, "vendeurs": 5, "routeurs": 3, "connexions": 100},
    {"nom": "Pro", "prix": 15000, "sites": 5, "vendeurs": 25, "routeurs": 10, "connexions": 1000},
    {"nom": "Max", "prix": 40000, "sites": 30, "vendeurs": 80, "routeurs": 15, "connexions": 3000},
]

def plan_limits():
    name = setting("selected_plan") or "Max"
    return next((p for p in PLANS if p["nom"] == name), PLANS[-1])

def trial_days_remaining():
    started = setting("trial_start")
    if not started:
        set_setting("trial_start", datetime.now().isoformat(timespec="seconds"))
        return 30
    try:
        start = datetime.fromisoformat(started)
        elapsed = (datetime.now() - start).days
        return max(0, 30 - elapsed)
    except (ValueError, TypeError):
        return 0

def setting(key):
    with db_conn() as con:
        row = con.execute("SELECT valeur FROM parametres WHERE cle=?", (key,)).fetchone()
    return row["valeur"] if row else DEFAULTS.get(key, "")

def set_setting(key, value):
    with db_conn() as con:
        con.execute(
            "INSERT INTO parametres(cle,valeur) VALUES(?,?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur",
            (key, str(value))
        )

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("connecte") or not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def now_text():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def make_ticket_code():
    return secrets.token_hex(5).upper()

def password_hash(password):
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 300000).hex()
    return salt.hex() + "$" + hashed

def password_matches(password, encoded):
    try:
        salt_hex, expected = encoded.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 300000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def send_account_email(to, subject, body):
    if not (MAIL_SERVER and MAIL_FROM):
        raise RuntimeError("E-mail non configuré sur le serveur. Configure MAIL_SERVER et MAIL_FROM dans Render.")
    import smtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=20) as smtp:
        if MAIL_USE_TLS:
            smtp.starttls()
        if MAIL_USERNAME and MAIL_PASSWORD:
            smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        smtp.send_message(msg)

def create_token(account_id, purpose, email, company):
    token = secrets.token_urlsafe(32)
    expiry = int(datetime.now().timestamp()) + (86400 if purpose == "verify" else 3600)
    with accounts_conn() as con:
        con.execute("UPDATE account_tokens SET used=1 WHERE account_id=? AND purpose=? AND used=0", (account_id, purpose))
        con.execute("INSERT INTO account_tokens(account_id,token_hash,purpose,expires_at) VALUES(?,?,?,?)",
                    (account_id, token_digest(token), purpose, expiry))
    endpoint = "verify_account" if purpose == "verify" else "reset_password"
    link = url_for(endpoint, token=token, _external=True)
    subject = "Vérification de votre compte BAMBA CONTROLOR" if purpose == "verify" else "Réinitialisation du mot de passe BAMBA CONTROLOR"
    instruction = "Cliquez sur ce lien pour vérifier votre compte (valable 24 heures) :" if purpose == "verify" else "Cliquez sur ce lien pour choisir un nouveau mot de passe (valable 1 heure) :"
    send_account_email(email, subject, f"Bonjour {company},\n\n{instruction}\n{link}\n\nSi vous n'êtes pas à l'origine de cette demande, ignorez ce message.")

LOGIN_PAGE = """
<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Connexion — BAMBA CONTROLOR</title>
<style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at top,#123f7d,#07101f 65%);color:#eef7ff;font-family:Arial,sans-serif}.box{width:min(430px,92vw);padding:28px;background:#101e35;border:1px solid #1d9de0;border-radius:20px;box-shadow:0 0 30px #0077ff35}h1{font-size:24px;color:#63d8ff}input,button{width:100%;padding:13px;margin-top:12px;border-radius:9px;font-size:15px}input{background:#071426;color:white;border:1px solid #345578}button{border:0;background:linear-gradient(90deg,#168bff,#31d7ff);font-weight:bold;color:#04152a;cursor:pointer}a{color:#7de0ff}.msg{color:#ffd47a}.links{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-top:16px;font-size:14px}</style></head><body><form class="box" method="post"><h1>◉ BAMBA CONTROLOR</h1><p>Connectez-vous à votre espace sécurisé.</p><input name="identifiant" required autocomplete="username" placeholder="E-mail ou téléphone"><input type="password" name="mot" required autocomplete="current-password" placeholder="Mot de passe"><button>Se connecter</button>{% if erreur %}<p class="msg">Identifiants incorrects ou compte non vérifié.</p>{% endif %}<div class="links"><a href="{{ url_for('register') }}">Créer un compte</a><a href="{{ url_for('forgot_password') }}">Mot de passe oublié ?</a></div></form></body></html>
"""

AUTH_PAGE = """
<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ titre }} — BAMBA CONTROLOR</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at top,#123f7d,#07101f 65%);color:#eef7ff;font-family:Arial,sans-serif}.box{width:min(450px,93vw);padding:26px;background:#101e35;border:1px solid #1d9de0;border-radius:20px;box-shadow:0 0 30px #0077ff35}h1{color:#63d8ff;font-size:23px}input,button{width:100%;padding:13px;margin-top:12px;border-radius:9px;font-size:15px}input{background:#071426;color:white;border:1px solid #345578}button{border:0;background:linear-gradient(90deg,#168bff,#31d7ff);font-weight:bold;color:#04152a}a{color:#7de0ff}.msg{color:#ffd47a}</style></head><body><form class="box" method="post"><h1>◉ BAMBA CONTROLOR</h1><h2>{{ titre }}</h2><p>{{ description }}</p>{% for field in fields %}<input name="{{ field.name }}" type="{{ field.type }}" placeholder="{{ field.label }}" {% if field.required %}required{% endif %} {% if field.minlength %}minlength="{{ field.minlength }}"{% endif %} autocomplete="{{ field.autocomplete }}">{% endfor %}<button>{{ bouton }}</button>{% if message %}<p class="msg">{{ message }}</p>{% endif %}<p><a href="{{ url_for('login') }}">Retour à la connexion</a></p></form></body></html>
"""

PAGE = """
<!doctype html><html lang="fr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ event_name }} — Administration</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1220;color:#eef4ff;font-family:Arial,sans-serif}
header{padding:22px 18px;background:linear-gradient(120deg,#123b83,#087eae);display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
header h1{margin:0;font-size:24px}header p{margin:7px 0 0;color:#d8edff}a{color:#8edcff}
main{max-width:1100px;margin:auto;padding:16px}h2{font-size:19px;margin:25px 0 12px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.card,.panel{background:#151f32;border:1px solid #263650;border-radius:14px;padding:15px;min-width:0}
.label{color:#aabbd5;font-size:13px}.number{font-size:23px;font-weight:bold;margin-top:8px}
form{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}input,select,button{padding:11px;border-radius:8px;border:1px solid #344761;font-size:14px}
input,select{background:#0c1627;color:white;min-width:0;flex:1}button{background:#1d8cff;color:white;border:0;font-weight:bold;cursor:pointer}
button.danger{background:#b9384b}button.muted{background:#33445f}table{width:100%;border-collapse:collapse;font-size:13px}
td,th{text-align:left;padding:10px 6px;border-bottom:1px solid #2a3850;vertical-align:top}th{color:#a9c6e8}
.scroll{overflow-x:auto}.tag{color:#58e0b0}.warning{color:#ffd27a}.msg{background:#173b34;padding:10px;border-radius:8px}
footer{padding:24px;color:#8294ae;text-align:center;font-size:12px}.inline{display:inline}
@media(min-width:700px){.cards{grid-template-columns:repeat(4,minmax(0,1fr))}}
</style></head><body>
<header><div><h1>◈ {{ event_name }}</h1><p>Administration des ventes, vendeurs et tickets</p></div>
<div><a href="{{ url_for('logout') }}">Déconnexion</a></div></header><main>
{% with messages = get_flashed_messages() %}{% for message in messages %}<p class="msg">{{ message }}</p>{% endfor %}{% endwith %}
<p class="tag">● Tableau de bord administrateur</p>
<div class="cards">
<div class="card"><div class="label">Chiffre d’affaires valide</div><div class="number">{{ ca }} {{ currency }}</div></div>
<div class="card"><div class="label">Tickets vendus valides</div><div class="number">{{ total }}</div></div>
<div class="card"><div class="label">Commissions valides</div><div class="number">{{ commissions }} {{ currency }}</div></div>
<div class="card"><div class="label">Vendeurs actifs</div><div class="number">{{ nb_vendeurs }}</div></div>
</div>

<h2>⚙️ Paramètres généraux</h2><div class="panel">
<form method="post" action="{{ url_for('save_settings') }}">
<label>Nom du service <input name="event_name" maxlength="80" value="{{ event_name }}" required></label>
<label>Prix du ticket (FCFA) <input name="ticket_price" type="number" min="1" max="1000000" value="{{ ticket_price }}" required></label>
<label>Commission (%) <input name="commission_percent" type="number" min="0" max="100" step="0.1" value="{{ commission_percent }}" required></label>
<button>Enregistrer les paramètres</button></form>
<p class="warning">Les nouveaux paramètres s’appliquent aux prochaines ventes. Les anciennes ventes ne sont pas recalculées.</p></div>

<h2>＋ Enregistrer une vente et générer ses tickets</h2><div class="panel">
<form method="post" action="{{ url_for('add_sale') }}">
<select name="vendeur" required>{% for v in vendeurs if v['actif'] %}<option value="{{ v['id'] }}">{{ v['nom'] }}</option>{% endfor %}</select>
<input name="quantite" type="number" min="1" max="500" value="1" required placeholder="Quantité">
<button>Enregistrer la vente</button></form>
<p><small>Chaque ticket de cette nouvelle vente reçoit un code unique. Les ventes historiques restent conservées.</small></p></div>

<h2>＋ Gérer les vendeurs</h2><div class="panel">
<form method="post" action="{{ url_for('add_seller') }}"><input name="nom" required maxlength="60" placeholder="Nom du nouveau vendeur"><button>Ajouter</button></form>
<div class="scroll"><table><tr><th>Nom</th><th>Statut</th><th>Action</th></tr>
{% for v in tous_vendeurs %}<tr><td>{{ v['nom'] }}</td><td>{{ 'Actif' if v['actif'] else 'Suspendu' }}</td><td>
<form method="post" action="{{ url_for('seller_action', seller_id=v['id']) }}">
<input name="nom" maxlength="60" value="{{ v['nom'] }}" aria-label="Nom">
<button name="action" value="renommer">Renommer</button>
<button name="action" value="{{ 'suspendre' if v['actif'] else 'activer' }}" class="muted">{{ 'Suspendre' if v['actif'] else 'Activer' }}</button>
<button name="action" value="supprimer" class="danger" onclick="return confirm('Supprimer ce vendeur ? Si des ventes existent, la suppression sera refusée.');">Supprimer</button>
</form></td></tr>{% endfor %}</table></div></div>

<h2>🎟️ Tickets récents</h2><div class="panel scroll"><table>
<tr><th>Code</th><th>Créé le</th><th>Vente</th><th>Statut</th><th>Action</th></tr>
{% for t in tickets %}<tr><td><code>{{ t['code'] }}</code></td><td>{{ t['cree_le'] }}</td><td>#{{ t['vente_id'] or '—' }}</td><td>{{ t['statut'] }}</td><td>
{% if t['statut'] == 'valide' %}<form method="post" action="{{ url_for('ticket_action', ticket_id=t['id']) }}">
<button name="action" value="annuler" class="danger" onclick="return confirm('Annuler ce ticket ?');">Annuler</button>
<button name="action" value="utiliser" class="muted">Marquer utilisé</button></form>{% endif %}</td></tr>
{% else %}<tr><td colspan="5">Aucun ticket généré par les nouvelles ventes.</td></tr>{% endfor %}
</table></div>

<h2>🧾 Dernières ventes</h2><div class="panel scroll"><table>
<tr><th>ID</th><th>Date</th><th>Vendeur</th><th>Qté</th><th>Total</th><th>Commission</th><th>Statut</th><th>Action</th></tr>
{% for v in ventes %}<tr><td>#{{ v['id'] }}</td><td>{{ v['date'] }}</td><td>{{ v['nom'] }}</td><td>{{ v['quantite'] }}</td><td>{{ v['total'] }} {{ currency }}</td><td>{{ v['commission'] }} {{ currency }}</td><td>{{ v['statut'] }}</td><td>
{% if v['statut'] == 'valide' %}<form method="post" action="{{ url_for('sale_action', sale_id=v['id']) }}"><button class="danger" name="action" value="annuler" onclick="return confirm('Annuler cette vente ?');">Annuler</button></form>{% endif %}</td></tr>
{% else %}<tr><td colspan="8">Aucune vente.</td></tr>{% endfor %}</table></div>

<h2>🌐 Sites Wi-Fi et routeurs</h2><div class="panel">
<p class="warning">Limites du forfait sélectionné : {{ plan_limits.sites }} sites, {{ plan_limits.vendeurs }} vendeurs, {{ plan_limits.routeurs }} routeurs par site, {{ plan_limits.connexions }} connexions simultanées.</p>
<form method="post" action="{{ url_for('add_site') }}">
<input name="nom" required maxlength="80" placeholder="Nom du site (ex. Site Abidjan)" aria-label="Nom du site">
<input name="localisation" maxlength="120" placeholder="Localisation (facultatif)" aria-label="Localisation">
<input name="routeurs" type="number" min="0" max="15" value="1" required placeholder="Routeurs" aria-label="Nombre de routeurs">
<button>Ajouter le site</button></form>
<div class="scroll"><table><tr><th>Site</th><th>Localisation</th><th>Routeurs</th><th>Statut</th><th>Action</th></tr>
{% for site in sites %}<tr><td>{{ site['nom'] }}</td><td>{{ site['localisation'] or '—' }}</td><td>{{ site['routeurs'] }}</td><td>{{ site['statut'] }}</td><td><form method="post" action="{{ url_for('site_action', site_id=site['id']) }}"><button name="action" value="{{ 'suspendre' if site['statut']=='actif' else 'activer' }}" class="muted">{{ 'Suspendre' if site['statut']=='actif' else 'Activer' }}</button><button name="action" value="supprimer" class="danger" onclick="return confirm('Supprimer ce site ?');">Supprimer</button></form></td></tr>{% else %}<tr><td colspan="5">Aucun site enregistré.</td></tr>{% endfor %}</table></div>
<p class="warning">La connexion effective aux routeurs MikroTik, RADIUS et VPN WireGuard n'est pas encore configurée par cette page.</p></div>

<h2>💳 Forfaits BAMBA-CONTROLOR</h2><div class="cards">
{% for plan in plans %}<div class="card"><div class="label">{{ plan.nom }}{% if plan.nom == selected_plan %} · FORFAIT ACTUEL{% endif %}</div><div class="number">{{ plan.prix }} FCFA</div><p>/ mois</p><p>{{ plan.sites }} sites</p><p>{{ plan.vendeurs }} vendeurs</p><p>{{ plan.routeurs }} routeurs / site</p><p>{{ plan.connexions }} connexions simultanées</p><form method="post" action="{{ url_for('choose_plan') }}"><input type="hidden" name="plan" value="{{ plan.nom }}"><button>Choisir {{ plan.nom }}</button></form></div>{% endfor %}
</div><div class="panel"><p><strong>Statut :</strong> {{ subscription_status }}{% if trial_days > 0 %} · {{ trial_days }} jour(s) d’essai estimés restants{% endif %}</p><p class="warning">L’essai de 30 jours est suivi localement dans cette version. Aucun prélèvement n’est effectué. Wave, Orange Money et les confirmations automatiques nécessitent un compte marchand et une intégration officielle.</p></div>

<h2>📥 Importer des codes existants (CSV)</h2><div class="panel"><p>Fichier CSV avec une colonne <code>code</code> ou une première colonne contenant les codes. Les codes importés sont conservés comme tickets, sans confirmation d’accès réseau.</p><form method="post" action="{{ url_for('import_tickets') }}" enctype="multipart/form-data"><input type="file" name="fichier" accept=".csv,text/csv" required><button>Importer les codes CSV</button></form><p class="warning">Vérifie le fichier avant import. Les doublons sont ignorés.</p></div>

<h2>💰 Paiements enregistrés</h2><div class="panel"><form method="post" action="{{ url_for('record_payment') }}"><input name="montant" type="number" min="1" max="100000000" required placeholder="Montant FCFA"><select name="methode"><option>Wave</option><option>Orange Money</option><option>MTN Money</option><option>Moov Money</option><option>Espèces</option></select><input name="reference" maxlength="120" placeholder="Référence de transaction (facultatif)"><button>Enregistrer comme en attente</button></form><div class="scroll"><table><tr><th>Date</th><th>Montant</th><th>Méthode</th><th>Référence</th><th>Statut</th></tr>{% for pay in paiements %}<tr><td>{{ pay['date'] }}</td><td>{{ pay['montant'] }} FCFA</td><td>{{ pay['methode'] }}</td><td>{{ pay['reference'] or '—' }}</td><td>{{ pay['statut'] }}</td></tr>{% else %}<tr><td colspan="5">Aucun paiement enregistré.</td></tr>{% endfor %}</table></div><p class="warning">Les paiements ajoutés ici ne sont pas vérifiés par Wave ou un opérateur mobile. Ne les marque pas comme payés sans confirmation officielle.</p></div>

<h2>🔐 Changer le mot de passe administrateur</h2><div class="panel">
<form method="post" action="{{ url_for('change_password') }}">
<input type="password" name="ancien" required placeholder="Mot de passe actuel">
<input type="password" name="nouveau" minlength="10" required placeholder="Nouveau mot de passe (10 caractères minimum)">
<input type="password" name="confirmation" minlength="10" required placeholder="Confirmer le nouveau mot de passe">
<button>Changer le mot de passe</button></form></div>

<h2>📡 Journal des recharges / opérations (saisie manuelle)</h2><div class="panel">
<form method="post" action="{{ url_for('add_operation') }}">
<select name="type"><option>Starlink</option><option>Maintenance</option><option>Autre</option></select>
<input name="description" maxlength="200" required placeholder="Description / référence">
<input name="montant" type="number" min="0" max="100000000" value="0" required placeholder="Montant FCFA">
<select name="statut"><option>enregistre</option><option>en_attente</option><option>termine</option><option>echec</option></select>
<button>Ajouter au journal</button></form>
<div class="scroll"><table><tr><th>Date</th><th>Type</th><th>Description</th><th>Montant</th><th>Statut</th></tr>
{% for o in operations %}<tr><td>{{ o['date'] }}</td><td>{{ o['type'] }}</td><td>{{ o['description'] }}</td><td>{{ o['montant'] }} {{ currency }}</td><td>{{ o['statut'] }}</td></tr>{% else %}<tr><td colspan="5">Aucune opération.</td></tr>{% endfor %}</table></div>
<p class="warning">Ce journal ne recharge pas automatiquement un compte Starlink. Toute recharge réelle doit être effectuée via le compte ou le fournisseur officiel.</p></div>

<p class="warning">Orange Money et Wave ne sont pas encore connectés. N’accepte pas une commande comme payée sans confirmation officielle du fournisseur.</p>
</main><footer>BAMBA-CONTROLOR · Administration sécurisée</footer></body></html>
"""

@app.before_request
def require_login_for_admin():
    public_endpoints = {"login", "register", "verify_account", "forgot_password", "reset_password", "static", "health"}
    if request.endpoint not in public_endpoints and (not session.get("connecte") or not session.get("user_id")):
        return redirect(url_for("login", next=request.path))

@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Cache-Control", "no-store")
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    erreur = False
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        email_login = identifiant.lower()
        phone_login = "".join(ch for ch in identifiant if ch.isdigit() or ch == "+")
        with accounts_conn() as con:
            account = con.execute("SELECT * FROM accounts WHERE email=? COLLATE NOCASE OR phone=?", (email_login, phone_login)).fetchone()
        if account and account["verified"] and password_matches(request.form.get("mot", ""), account["password_hash"]):
            session.clear()
            session.permanent = True
            session["connecte"] = True
            session["user_id"] = int(account["id"])
            session["company"] = account["company"]
            init_db(tenant_db_path(account["id"]))
            # Apply company name to this tenant's default dashboard settings.
            with db_conn() as con:
                con.execute("UPDATE parametres SET valeur=? WHERE cle='event_name'", (account["company"],))
            return redirect(request.args.get("next") if request.args.get("next", "").startswith("/") else url_for("index"))
        erreur = True
    return render_template_string(LOGIN_PAGE, erreur=erreur)

@app.route("/creer-compte", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    fields = [
        {"name":"societe","label":"Nom de la société","type":"text","required":True,"autocomplete":"organization"},
        {"name":"email","label":"Adresse e-mail","type":"email","required":True,"autocomplete":"email"},
        {"name":"telephone","label":"Téléphone avec indicatif si possible","type":"tel","required":True,"autocomplete":"tel"},
        {"name":"mot","label":"Mot de passe (10 caractères minimum)","type":"password","required":True,"minlength":10,"autocomplete":"new-password"},
    ]
    if request.method == "POST":
        company = request.form.get("societe", "").strip()[:120]
        email = request.form.get("email", "").strip().lower()[:254]
        phone = "".join(ch for ch in request.form.get("telephone", "") if ch.isdigit() or ch == "+")[:25]
        password = request.form.get("mot", "")
        if not company or "@" not in email or len(phone) < 8 or len(password) < 10:
            message = "Vérifiez les informations et utilisez un mot de passe d'au moins 10 caractères."
        elif not (MAIL_SERVER and MAIL_FROM):
            message = "La création nécessite la configuration d'envoi d'e-mails par l'administrateur du serveur."
        else:
            try:
                with accounts_conn() as con:
                    cur = con.execute("INSERT INTO accounts(email,phone,password_hash,company,verified,created_at) VALUES(?,?,?,?,0,?)",
                                      (email, phone, password_hash(password), company, datetime.now().isoformat(timespec="seconds")))
                    account_id = cur.lastrowid
                try:
                    create_token(account_id, "verify", email, company)
                except Exception:
                    with accounts_conn() as con:
                        con.execute("DELETE FROM accounts WHERE id=? AND verified=0", (account_id,))
                    raise
                message = "Compte créé. Consultez votre e-mail et cliquez sur le lien de vérification avant de vous connecter."
            except sqlite3.IntegrityError:
                message = "Cette adresse e-mail ou ce téléphone est déjà associé à un compte."
            except Exception:
                app.logger.exception("Échec d'envoi du mail de vérification")
                message = "Impossible d'envoyer le message de vérification. Réessayez plus tard ou contactez l'administrateur."
    return render_template_string(AUTH_PAGE, titre="Créer un compte", description="Enregistrez votre société et ouvrez votre espace privé.", fields=fields, bouton="Créer mon compte", message=message)

@app.route("/verification/<token>")
def verify_account(token):
    digest = token_digest(token)
    with accounts_conn() as con:
        row = con.execute("SELECT t.id,t.account_id,t.expires_at,a.company FROM account_tokens t JOIN accounts a ON a.id=t.account_id WHERE t.token_hash=? AND t.purpose='verify' AND t.used=0", (digest,)).fetchone()
        if not row or row["expires_at"] < int(datetime.now().timestamp()):
            flash("Lien de vérification invalide ou expiré. Créez une nouvelle demande auprès de l'administrateur.")
            return redirect(url_for("login"))
        con.execute("UPDATE accounts SET verified=1 WHERE id=?", (row["account_id"],))
        con.execute("UPDATE account_tokens SET used=1 WHERE id=?", (row["id"],))
    init_db(tenant_db_path(row["account_id"]))
    flash("Compte vérifié avec succès. Vous pouvez vous connecter.")
    return redirect(url_for("login"))

@app.route("/mot-de-passe-oublie", methods=["GET", "POST"])
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = "Si un compte correspondant existe, un lien de réinitialisation sera envoyé."
    fields = [{"name":"email","label":"Adresse e-mail du compte","type":"email","required":True,"autocomplete":"email"}]
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        with accounts_conn() as con:
            account = con.execute("SELECT id,email,company,verified FROM accounts WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        if account and account["verified"] and MAIL_SERVER and MAIL_FROM:
            try:
                create_token(account["id"], "reset", account["email"], account["company"])
            except Exception:
                app.logger.exception("Échec d'envoi du lien de réinitialisation")
    return render_template_string(AUTH_PAGE, titre="Mot de passe oublié ?", description="Entrez l'e-mail associé à votre compte.", fields=fields, bouton="Envoyer le lien", message=message)

@app.route("/reinitialiser/<token>", methods=["GET", "POST"])
def reset_password(token):
    fields = [
        {"name":"nouveau","label":"Nouveau mot de passe (10 caractères minimum)","type":"password","required":True,"minlength":10,"autocomplete":"new-password"},
        {"name":"confirmation","label":"Confirmer le mot de passe","type":"password","required":True,"minlength":10,"autocomplete":"new-password"},
    ]
    message = ""
    digest = token_digest(token)
    with accounts_conn() as con:
        row = con.execute("SELECT id,account_id,expires_at FROM account_tokens WHERE token_hash=? AND purpose='reset' AND used=0", (digest,)).fetchone()
    if not row or row["expires_at"] < int(datetime.now().timestamp()):
        return render_template_string(AUTH_PAGE, titre="Lien expiré", description="Ce lien est invalide ou expiré. Demandez-en un nouveau.", fields=[], bouton="Réinitialiser", message="Lien invalide ou expiré."), 400
    if request.method == "POST":
        new = request.form.get("nouveau", "")
        confirm = request.form.get("confirmation", "")
        if len(new) < 10 or new != confirm:
            message = "Les mots de passe doivent correspondre et contenir au moins 10 caractères."
        else:
            with accounts_conn() as con:
                con.execute("UPDATE accounts SET password_hash=? WHERE id=?", (password_hash(new), row["account_id"]))
                con.execute("UPDATE account_tokens SET used=1 WHERE account_id=? AND purpose='reset'", (row["account_id"],))
            flash("Mot de passe mis à jour. Connectez-vous avec le nouveau mot de passe.")
            return redirect(url_for("login"))
    return render_template_string(AUTH_PAGE, titre="Choisir un nouveau mot de passe", description="Le nouveau mot de passe doit contenir au moins 10 caractères.", fields=fields, bouton="Enregistrer le mot de passe", message=message)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    currency = setting("currency")
    with db_conn() as con:
        vendeurs = con.execute("SELECT id,nom,actif FROM vendeurs WHERE actif=1 ORDER BY nom").fetchall()
        tous_vendeurs = con.execute("SELECT id,nom,actif FROM vendeurs ORDER BY nom").fetchall()
        ventes = con.execute("""SELECT ventes.*, vendeurs.nom FROM ventes
            JOIN vendeurs ON vendeurs.id=ventes.vendeur_id ORDER BY ventes.id DESC LIMIT 50""").fetchall()
        tickets = con.execute("SELECT * FROM tickets ORDER BY id DESC LIMIT 50").fetchall()
        operations = con.execute("SELECT * FROM operations ORDER BY id DESC LIMIT 30").fetchall()
        sites = con.execute("SELECT * FROM sites ORDER BY id DESC").fetchall()
        paiements = con.execute("SELECT * FROM paiements ORDER BY id DESC LIMIT 30").fetchall()
        ca, total, commissions = con.execute("""SELECT
            COALESCE(SUM(CASE WHEN statut='valide' THEN total ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN statut='valide' THEN quantite ELSE 0 END),0),
            COALESCE(SUM(CASE WHEN statut='valide' THEN commission ELSE 0 END),0)
            FROM ventes""").fetchone()
    return render_template_string(PAGE, event_name=setting("event_name"), currency=currency,
        ticket_price=setting("ticket_price"), commission_percent=setting("commission_percent"),
        ca=ca, total=total, commissions=commissions,
        nb_vendeurs=sum(1 for v in tous_vendeurs if v["actif"]),
        vendeurs=vendeurs, tous_vendeurs=tous_vendeurs, ventes=ventes,
        tickets=tickets, operations=operations, sites=sites, paiements=paiements,
        plans=PLANS, selected_plan=setting("selected_plan"),
        subscription_status=setting("subscription_status"),
        trial_days=trial_days_remaining(), plan_limits=plan_limits())

@app.route("/parametres", methods=["POST"])
def save_settings():
    try:
        price = int(request.form.get("ticket_price", ""))
        commission = float(request.form.get("commission_percent", ""))
        name = request.form.get("event_name", "").strip()[:80]
        if price < 1 or price > 1_000_000 or not 0 <= commission <= 100 or not name:
            raise ValueError
    except ValueError:
        flash("Paramètres invalides.")
        return redirect(url_for("index"))
    set_setting("ticket_price", price)
    set_setting("commission_percent", commission)
    set_setting("event_name", name)
    flash("Paramètres enregistrés. Les anciennes ventes ne sont pas recalculées.")
    return redirect(url_for("index"))

@app.route("/vendeur", methods=["POST"])
def add_seller():
    name = request.form.get("nom", "").strip()[:60]
    if not name:
        flash("Le nom du vendeur est obligatoire.")
    else:
        with db_conn() as con:
            active_count = con.execute("SELECT COUNT(*) FROM vendeurs WHERE actif=1").fetchone()[0]
        if active_count >= plan_limits()["vendeurs"]:
            flash(f"Limite du forfait {plan_limits()['nom']} atteinte : {plan_limits()['vendeurs']} vendeurs actifs maximum.")
            return redirect(url_for("index"))
        try:
            with db_conn() as con:
                con.execute("INSERT INTO vendeurs(nom,actif) VALUES(?,1)", (name,))
            flash("Vendeur ajouté.")
        except sqlite3.IntegrityError:
            flash("Ce nom de vendeur existe déjà.")
    return redirect(url_for("index"))

@app.route("/vendeur/<int:seller_id>", methods=["POST"])
def seller_action(seller_id):
    action = request.form.get("action")
    with db_conn() as con:
        seller = con.execute("SELECT * FROM vendeurs WHERE id=?", (seller_id,)).fetchone()
        if not seller:
            flash("Vendeur introuvable.")
            return redirect(url_for("index"))
        if action == "renommer":
            name = request.form.get("nom", "").strip()[:60]
            if not name:
                flash("Nom invalide.")
            else:
                try:
                    con.execute("UPDATE vendeurs SET nom=? WHERE id=?", (name, seller_id))
                    flash("Vendeur renommé.")
                except sqlite3.IntegrityError:
                    flash("Ce nom existe déjà.")
        elif action == "suspendre":
            con.execute("UPDATE vendeurs SET actif=0 WHERE id=?", (seller_id,))
            flash("Vendeur suspendu.")
        elif action == "activer":
            con.execute("UPDATE vendeurs SET actif=1 WHERE id=?", (seller_id,))
            flash("Vendeur activé.")
        elif action == "supprimer":
            count = con.execute("SELECT COUNT(*) FROM ventes WHERE vendeur_id=?", (seller_id,)).fetchone()[0]
            if count:
                flash("Suppression refusée : ce vendeur a des ventes. Suspends-le pour garder l’historique.")
            else:
                con.execute("DELETE FROM vendeurs WHERE id=?", (seller_id,))
                flash("Vendeur supprimé.")
        else:
            flash("Action inconnue.")
    return redirect(url_for("index"))

@app.route("/vente", methods=["POST"])
def add_sale():
    try:
        seller_id = int(request.form.get("vendeur", ""))
        quantity = int(request.form.get("quantite", ""))
        if not 1 <= quantity <= 500:
            raise ValueError
    except ValueError:
        flash("Quantité ou vendeur invalide.")
        return redirect(url_for("index"))
    price = int(setting("ticket_price"))
    commission_rate = float(setting("commission_percent")) / 100.0
    total = quantity * price
    commission = int(total * commission_rate)
    with db_conn() as con:
        seller = con.execute("SELECT id FROM vendeurs WHERE id=? AND actif=1", (seller_id,)).fetchone()
        if not seller:
            flash("Vendeur inconnu ou suspendu.")
            return redirect(url_for("index"))
        cur = con.execute("""INSERT INTO ventes(date,vendeur_id,quantite,total,commission,statut)
            VALUES(?,?,?,?,?,'valide')""", (now_text(), seller_id, quantity, total, commission))
        sale_id = cur.lastrowid
        codes = set()
        for _ in range(quantity):
            code = make_ticket_code()
            while code in codes:
                code = make_ticket_code()
            codes.add(code)
            con.execute("INSERT INTO tickets(code,vente_id,cree_le,statut) VALUES(?,?,?,'valide')",
                        (code, sale_id, now_text()))
    flash(f"Vente #{sale_id} enregistrée : {quantity} ticket(s), total {total} FCFA.")
    return redirect(url_for("index"))

@app.route("/vente/<int:sale_id>", methods=["POST"])
def sale_action(sale_id):
    if request.form.get("action") != "annuler":
        abort(400)
    with db_conn() as con:
        sale = con.execute("SELECT statut FROM ventes WHERE id=?", (sale_id,)).fetchone()
        if not sale:
            flash("Vente introuvable.")
        elif sale["statut"] != "valide":
            flash("Cette vente est déjà annulée.")
        else:
            con.execute("UPDATE ventes SET statut='annulee' WHERE id=?", (sale_id,))
            con.execute("UPDATE tickets SET statut='annule' WHERE vente_id=? AND statut='valide'", (sale_id,))
            flash("Vente annulée et tickets associés invalidés. L’historique est conservé.")
    return redirect(url_for("index"))

@app.route("/ticket/<int:ticket_id>", methods=["POST"])
def ticket_action(ticket_id):
    action = request.form.get("action")
    with db_conn() as con:
        ticket = con.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if not ticket:
            flash("Ticket introuvable.")
        elif ticket["statut"] != "valide":
            flash("Ce ticket n’est plus valide.")
        elif action == "annuler":
            con.execute("UPDATE tickets SET statut='annule' WHERE id=? AND statut='valide'", (ticket_id,))
            flash("Ticket annulé.")
        elif action == "utiliser":
            con.execute("UPDATE tickets SET statut='utilise', utilise_le=? WHERE id=? AND statut='valide'",
                        (now_text(), ticket_id))
            flash("Ticket marqué comme utilisé.")
        else:
            abort(400)
    return redirect(url_for("index"))

@app.route("/mot-de-passe", methods=["POST"])
def change_password():
    old = request.form.get("ancien", "")
    new = request.form.get("nouveau", "")
    confirm = request.form.get("confirmation", "")
    with accounts_conn() as con:
        account = con.execute("SELECT password_hash FROM accounts WHERE id=?", (session.get("user_id"),)).fetchone()
        if not account or not password_matches(old, account["password_hash"]):
            flash("Le mot de passe actuel est incorrect.")
            return redirect(url_for("index"))
        if len(new) < 10 or new != confirm:
            flash("Le nouveau mot de passe doit contenir au moins 10 caractères et les deux champs doivent correspondre.")
            return redirect(url_for("index"))
        con.execute("UPDATE accounts SET password_hash=? WHERE id=?", (password_hash(new), session.get("user_id")))
    session.clear()
    flash("Mot de passe changé. Reconnectez-vous.")
    return redirect(url_for("login"))

@app.route("/operation", methods=["POST"])
def add_operation():
    kind = request.form.get("type", "Autre")[:40]
    description = request.form.get("description", "").strip()[:200]
    status = request.form.get("statut", "enregistre")
    allowed = {"enregistre", "en_attente", "termine", "echec"}
    try:
        amount = int(request.form.get("montant", "0"))
        if amount < 0 or amount > 100_000_000 or status not in allowed or not description:
            raise ValueError
    except ValueError:
        flash("Informations d’opération invalides.")
        return redirect(url_for("index"))
    with db_conn() as con:
        con.execute("INSERT INTO operations(date,type,description,montant,statut) VALUES(?,?,?,?,?)",
                    (now_text(), kind, description, amount, status))
    flash("Opération ajoutée au journal.")
    return redirect(url_for("index"))

@app.route("/site", methods=["POST"])
def add_site():
    name = request.form.get("nom", "").strip()[:80]
    location = request.form.get("localisation", "").strip()[:120]
    try:
        routers = int(request.form.get("routeurs", "1"))
        limits = plan_limits()
        with db_conn() as con:
            count = con.execute("SELECT COUNT(*) FROM sites WHERE statut='actif'").fetchone()[0]
        if not name or not 0 <= routers <= limits["routeurs"]:
            raise ValueError
        if count >= limits["sites"]:
            flash(f"Limite du forfait atteinte : {limits['sites']} sites actifs maximum.")
            return redirect(url_for("index"))
        with db_conn() as con:
            con.execute("INSERT INTO sites(nom,localisation,routeurs,statut,cree_le) VALUES(?,?,?,'actif',?)", (name, location, routers, now_text()))
        flash("Site ajouté. Le routeur doit encore être configuré pour se connecter réellement.")
    except ValueError:
        flash("Informations du site invalides ou nombre de routeurs supérieur à la limite du forfait.")
    except sqlite3.IntegrityError:
        flash("Un site porte déjà ce nom.")
    return redirect(url_for("index"))

@app.route("/site/<int:site_id>", methods=["POST"])
def site_action(site_id):
    action = request.form.get("action")
    with db_conn() as con:
        site = con.execute("SELECT * FROM sites WHERE id=?", (site_id,)).fetchone()
        if not site:
            flash("Site introuvable.")
        elif action == "suspendre":
            con.execute("UPDATE sites SET statut='suspendu' WHERE id=?", (site_id,))
            flash("Site suspendu dans le tableau de bord.")
        elif action == "activer":
            count = con.execute("SELECT COUNT(*) FROM sites WHERE statut='actif'").fetchone()[0]
            if count >= plan_limits()["sites"]:
                flash("Limite du forfait atteinte : impossible d’activer ce site.")
            else:
                con.execute("UPDATE sites SET statut='actif' WHERE id=?", (site_id,))
                flash("Site activé dans le tableau de bord.")
        elif action == "supprimer":
            con.execute("DELETE FROM sites WHERE id=?", (site_id,))
            flash("Site supprimé du tableau de bord.")
        else:
            abort(400)
    return redirect(url_for("index"))

@app.route("/forfait", methods=["POST"])
def choose_plan():
    name = request.form.get("plan", "")
    if name not in {p["nom"] for p in PLANS}:
        flash("Forfait inconnu.")
    else:
        set_setting("selected_plan", name)
        set_setting("subscription_status", "Essai gratuit" if trial_days_remaining() > 0 else "À renouveler")
        flash(f"Forfait {name} sélectionné. Aucun paiement n’a été débité.")
    return redirect(url_for("index"))

@app.route("/paiement", methods=["POST"])
def record_payment():
    try:
        amount = int(request.form.get("montant", ""))
        method = request.form.get("methode", "")[:40]
        reference = request.form.get("reference", "").strip()[:120]
        if amount < 1 or amount > 100_000_000 or method not in {"Wave", "Orange Money", "MTN Money", "Moov Money", "Espèces"}:
            raise ValueError
        with db_conn() as con:
            con.execute("INSERT INTO paiements(date,montant,methode,reference,statut) VALUES(?,?,?,?, 'en_attente')", (now_text(), amount, method, reference))
        flash("Paiement enregistré en attente de vérification officielle.")
    except ValueError:
        flash("Montant ou méthode de paiement invalide.")
    return redirect(url_for("index"))

@app.route("/import-csv", methods=["POST"])
def import_tickets():
    upload = request.files.get("fichier")
    if not upload or not upload.filename or not upload.filename.lower().endswith(".csv"):
        flash("Sélectionne un fichier CSV valide.")
        return redirect(url_for("index"))
    try:
        raw = upload.stream.read(2_000_000)
        text_data = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text_data))
        rows = list(reader)
        if not rows:
            raise ValueError
        header = [cell.strip().lower() for cell in rows[0]]
        code_index = header.index("code") if "code" in header else 0
        start = 1 if "code" in header else 0
        imported = 0
        with db_conn() as con:
            for row in rows[start:]:
                if len(row) <= code_index:
                    continue
                code = row[code_index].strip()[:100]
                if not code or any(ch.isspace() for ch in code):
                    continue
                cur = con.execute("INSERT OR IGNORE INTO tickets(code,vente_id,cree_le,statut) VALUES(?,NULL,?,'valide')", (code, now_text()))
                imported += cur.rowcount
            con.execute("INSERT INTO import_log(date,fichier,importes) VALUES(?,?,?)", (now_text(), upload.filename[:150], imported))
        flash(f"Import terminé : {imported} code(s) ajouté(s). Les doublons ont été ignorés.")
    except (UnicodeDecodeError, csv.Error, ValueError):
        flash("Le fichier CSV n’a pas pu être lu. Utilise un CSV encodé en UTF-8.")
    return redirect(url_for("index"))

@app.route("/health")
def health():
    # Minimal health check for the hosting platform; no private data returned.
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
