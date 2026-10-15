import os
import json
import hmac
import hashlib
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from comptes_clients import creer_compte_client, verifier_mot_de_passe
from functools import wraps

from flask import (
    Flask, render_template_string, request, redirect, url_for,
    session, abort, flash
)

BASE_DIR = Path(__file__).resolve().parent
DB = Path(os.environ.get("BAMBA_DB_PATH", str(BASE_DIR / "bamba.db")))
AUTH_FILE = Path(os.environ.get("BAMBA_AUTH_FILE", str(BASE_DIR / "auth_config.json")))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "")
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
AUTH = {}

def load_auth():
    """Use private environment values on a hosted server, or local auth_config.json."""
    global AUTH
    if os.environ.get("ADMIN_PASSWORD_HASH") and os.environ.get("ADMIN_PASSWORD_SALT"):
        AUTH = {
            "password_hash": os.environ["ADMIN_PASSWORD_HASH"],
            "salt": os.environ["ADMIN_PASSWORD_SALT"],
        }
        if not app.config["SECRET_KEY"]:
            raise RuntimeError("FLASK_SECRET_KEY must be set when using hosted environment secrets.")
    else:
        if not AUTH_FILE.exists():
            raise RuntimeError(
                "Configuration absente. Lancez `python creer_securite.py` pour créer auth_config.json."
            )
        with AUTH_FILE.open(encoding="utf-8") as f:
            AUTH = json.load(f)
        if not app.config["SECRET_KEY"]:
            app.config["SECRET_KEY"] = AUTH.get("secret_key", "")
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Clé de session absente. Configurez FLASK_SECRET_KEY ou auth_config.json.")

load_auth()

DEFAULTS = {
    "ticket_price": "100",
    "commission_percent": "10",
    "event_name": "BAMBA-CONTROLOR",
    "currency": "FCFA",
}

def db_conn():
    con = sqlite3.connect(DB, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with db_conn() as con:
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
        con.execute("""CREATE TABLE IF NOT EXISTS comptes_application(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            identifiant TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'en_attente'
                CHECK(statut IN ('en_attente','approuve','refuse')),
            cree_le TEXT NOT NULL
        )""")
        for key, value in DEFAULTS.items():
            con.execute("INSERT OR IGNORE INTO parametres(cle,valeur) VALUES(?,?)", (key, value))
        con.execute("INSERT OR IGNORE INTO vendeurs(nom,actif) VALUES(?,1)", ("Vendeur principal",))
        con.commit()

init_db()

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
        if not session.get("connecte"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def now_text():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def make_ticket_code():
    return secrets.token_hex(5).upper()

def verify_password(candidate):
    try:
        salt = bytes.fromhex(AUTH["salt"])
        expected = AUTH["password_hash"]
        actual = hashlib.pbkdf2_hmac("sha256", candidate.encode(), salt, 300000).hex()
        return hmac.compare_digest(actual, expected)
    except (KeyError, ValueError, TypeError):
        return False

LOGIN_PAGE = """
<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connexion — BAMBA-CONTROLOR</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0b1220;color:#eef4ff;font-family:Arial}
form{width:min(370px,92vw);padding:26px;background:#17233b;border:1px solid #2b3d59;border-radius:18px}
input,button{width:100%;padding:13px;margin-top:12px;border:0;border-radius:9px;font-size:16px}
input{background:#0b1220;color:white;border:1px solid #344761}button{background:#38bdf8;color:#082f49;font-weight:bold}
.error{color:#fca5a5}small{color:#b5c4d9}


/* BAMBA_UI_THEME_V1 */
:root {
  color-scheme: dark;
  --bamba-bg: #071426;
  --bamba-panel: #10223b;
  --bamba-panel2: #142b49;
  --bamba-border: #294565;
  --bamba-blue: #0878f9;
  --bamba-cyan: #28c4f5;
  --bamba-text: #f2f7ff;
  --bamba-muted: #a9bdd7;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  background:
    radial-gradient(ellipse at 15% 0%, #123b70 0, transparent 42%),
    linear-gradient(145deg, #06101f, var(--bamba-bg) 60%, #0b2340);
  color: var(--bamba-text);
  font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif;
}
header {
  position: relative;
  overflow: hidden;
  border-bottom: 1px solid #2e5b8a;
  background: linear-gradient(115deg, #063a86, #087cc0 58%, #082650);
  box-shadow: 0 12px 35px #0004;
}
header h1 {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: clamp(21px, 3vw, 30px);
  letter-spacing: .3px;
}
header h1::before {
  content: "✦";
  display: inline-grid;
  place-items: center;
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  border: 2px solid #77d9ff;
  border-radius: 15px;
  background: linear-gradient(145deg, #0c86ff, #071c46);
  color: white;
  box-shadow: 0 0 20px #1c9dff66, inset 0 0 12px #ffffff24;
  font-size: 27px;
}
header p { color: #d8efff; }
main { max-width: 1440px; padding: 22px; }
h2 {
  color: #f5f9ff;
  font-size: 19px;
  letter-spacing: .1px;
}
.card, .panel {
  background: linear-gradient(145deg, #142943, #0d1b30);
  border: 1px solid var(--bamba-border);
  border-radius: 16px;
  box-shadow: 0 10px 28px #0002;
  transition: border-color .2s, transform .2s;
}
.card:hover, .panel:hover {
  border-color: #398edb;
}
.label, small { color: var(--bamba-muted); }
input, select, textarea {
  max-width: 100%;
  background: #09182b !important;
  color: var(--bamba-text) !important;
  border: 1px solid #355477 !important;
  border-radius: 10px !important;
  padding: 12px !important;
}
button {
  border: 1px solid #278ce5;
  border-radius: 10px;
  background: linear-gradient(120deg, #0879f9, #0754b8);
  color: white;
  font-weight: 700;
  padding: 11px 15px;
  cursor: pointer;
  transition: filter .2s, transform .2s;
}
button:hover { filter: brightness(1.15); }
button:active { transform: scale(.98); }
a { color: #68d5ff; }
table { width: 100%; border-collapse: collapse; }
th {
  color: #b9d7f7;
  background: #102947;
  text-align: left;
}
th, td {
  border-bottom: 1px solid #29415d;
  padding: 11px 10px;
}
tr:hover td { background: #ffffff06; }
.scroll { max-width: 100%; overflow-x: auto; }
.warning {
  border-left: 3px solid #f4b942;
  padding-left: 12px;
  color: #f8dca0;
}
.danger { background: linear-gradient(120deg, #c03955, #8f203d); }
.muted { background: #294563; border-color: #496a8c; }
form { max-width: 100%; }
button:focus-visible, input:focus-visible, a:focus-visible {
  outline: 2px solid #58d7ff;
  outline-offset: 3px;
}
@media (min-width: 900px) {
  .cards { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 650px) {
  main { padding: 13px; }
  header { padding: 18px 14px; }
  header h1::before {
    flex-basis: 42px; width: 42px; height: 42px;
  }
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .card, .panel { padding: 12px; }
  th, td { padding: 9px 8px; white-space: nowrap; }
}

</style></head><body><form method="post"><h2>◈ BAMBA-CONTROLOR</h2>
<p>Connexion administrateur</p><input type="password" name="mot" required autofocus placeholder="Mot de passe">
<button>Se connecter</button>{% if erreur %}<p class="error">Mot de passe incorrect.</p>{% endif %}
<small>Ne partage jamais ton mot de passe.</small>
<p><a href="{{ url_for('inscription_application') }}">Créer un compte</a> ·
<a href="{{ url_for('connexion_utilisateur') }}">Connexion utilisateur</a></p>
</form></body></html>
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
<div>
{% if session.get('role') == 'admin' %}
<a href="{{ url_for('gestion_comptes') }}">Gestion des comptes</a> ·
{% endif %}
<a href="{{ url_for('logout') }}">Déconnexion</a>
</div></header><main>
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


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    erreur = None
    if request.method == "POST":
        nom = request.form.get("nom", "")
        email = request.form.get("email", "")
        telephone = request.form.get("telephone", "").strip() or None
        mot = request.form.get("mot_de_passe", "")
        confirmation = request.form.get("confirmation", "")

        if mot != confirmation:
            erreur = "Les deux mots de passe ne correspondent pas."
        else:
            try:
                creer_compte_client(nom, email, mot, telephone)
                flash("Compte créé. Connectez-vous pour accéder à votre espace client.")
                return redirect(url_for("connexion_client"))
            except (ValueError, RuntimeError) as e:
                erreur = str(e)

    return render_template_string("""
    <!doctype html><html lang="fr"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Créer un compte — WiFiControl</title>
    <style>
    body{font-family:Arial,sans-serif;background:#f1f5f9;margin:0;padding:24px}
    main{max-width:480px;margin:30px auto;background:white;padding:24px;border-radius:16px}
    input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0}
    button{background:#075985;color:white;border:0;border-radius:8px;font-weight:bold}
    .erreur{color:#b91c1c}.info{background:#e0f2fe;padding:12px;border-radius:8px}
    </style><main>
    <h1>Créer mon compte</h1>
    <p class="info">30 jours d’essai gratuit du forfait Max, sans carte bancaire.</p>
    {% if erreur %}<p class="erreur">{{ erreur }}</p>{% endif %}
    <form method="post">
      <label>Nom complet</label><input name="nom" maxlength="100" required>
      <label>Adresse e-mail</label><input type="email" name="email" maxlength="254" required>
      <label>Téléphone (facultatif)</label><input name="telephone" maxlength="30">
      <label>Mot de passe (10 caractères minimum)</label>
      <input type="password" name="mot_de_passe" minlength="10" required>
      <label>Confirmer le mot de passe</label>
      <input type="password" name="confirmation" minlength="10" required>
      <button type="submit">Créer mon compte</button>
    </form>
    <p><a href="{{ url_for('connexion_client') }}">J’ai déjà un compte</a></p>
    </main></html>
    """, erreur=erreur)


@app.route("/connexion-client", methods=["GET", "POST"])
def connexion_client():
    erreur = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        mot = request.form.get("mot_de_passe", "")
        with db_conn() as con:
            client = con.execute(
                """SELECT id, mot_de_passe_hash
                   FROM clients_plateforme WHERE email = ?""",
                (email,)
            ).fetchone()

        if client and verifier_mot_de_passe(mot, client["mot_de_passe_hash"]):
            session.clear()
            session["client_id"] = client["id"]
            return redirect(url_for("espace_client"))

        erreur = "Adresse e-mail ou mot de passe incorrect."

    return render_template_string("""
    <!doctype html><html lang="fr"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Connexion client — WiFiControl</title>
    <style>
    body{font-family:Arial,sans-serif;background:#f1f5f9;padding:24px}
    main{max-width:440px;margin:40px auto;background:white;padding:24px;border-radius:16px}
    input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0}
    button{background:#075985;color:white;border:0;border-radius:8px}
    .erreur{color:#b91c1c}
    </style><main><h1>Connexion client</h1>
    {% for message in get_flashed_messages() %}<p>{{ message }}</p>{% endfor %}
    {% if erreur %}<p class="erreur">{{ erreur }}</p>{% endif %}
    <form method="post">
      <label>Adresse e-mail</label>
      <input type="email" name="email" required>
      <label>Mot de passe</label>
      <input type="password" name="mot_de_passe" required>
      <button type="submit">Me connecter</button>
    </form>
    <p><a href="{{ url_for('inscription') }}">Créer un compte</a></p>
    </main></html>
    """, erreur=erreur)


@app.route("/espace-client")
def espace_client():
    with db_conn() as con:
        client = con.execute("""
            SELECT c.nom, c.email, c.plan_code, c.fin_essai,
                   p.nom AS plan_nom, p.prix_mensuel
            FROM clients_plateforme c
            JOIN plans_abonnement p ON p.code = c.plan_code
            WHERE c.id = ?
        """, (session["client_id"],)).fetchone()

    if client is None:
        session.clear()
        return redirect(url_for("connexion_client"))

    fin = datetime.fromisoformat(client["fin_essai"])
    if fin.tzinfo is None:
        fin = fin.replace(tzinfo=timezone.utc)

    maintenant = datetime.now(timezone.utc)
    jours_restants = max(0, (fin - maintenant).days)
    essai_actif = maintenant < fin

    return render_template_string("""
    <!doctype html><html lang="fr"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Mon espace — WiFiControl</title>
    <style>
    body{font-family:Arial,sans-serif;background:#f1f5f9;padding:24px}
    main{max-width:600px;margin:30px auto;background:white;padding:24px;border-radius:16px}
    .info{background:#e0f2fe;padding:16px;border-radius:8px}
    </style><main>
    <h1>Bienvenue, {{ client["nom"] }}</h1>
    <p>{{ client["email"] }}</p>
    <section class="info">
    <h2>Forfait {{ client["plan_nom"] }}</h2>
    <p>Prix après l’essai : {{ client["prix_mensuel"] }} FCFA/mois</p>
    {% if essai_actif %}
      <p>Essai gratuit en cours : {{ jours_restants }} jour(s) restant(s).</p>
      <p>Fin de l’essai : {{ client["fin_essai"] }}</p>
    {% else %}
      <p>Votre période d’essai est terminée. Choisissez un forfait pour continuer.</p>
    {% endif %}
    </section>
    <p>La gestion des sites et les paiements en ligne seront ajoutés dans les prochaines étapes.</p>
    <form method="post" action="{{ url_for('deconnexion_client') }}">
      <button>Se déconnecter</button>
    </form>
    </main></html>
    """, client=client, jours_restants=jours_restants, essai_actif=essai_actif)


@app.route("/deconnexion-client", methods=["POST"])
def deconnexion_client():
    session.clear()
    return redirect(url_for("connexion_client"))



@app.before_request
def require_login_for_admin():
    public_endpoints = {
        # BAMBA_PUBLIC_ROUTES
        "bamba_features.liste_plans",
        "bamba_features.verifier_ticket",
        "bamba_features.qr_ticket",
        "bamba_features.imprimer_ticket",
        "bamba_features.notification_paiement",
        "bamba_features.retour_paiement",

        "health", "login", "static", "favicon_bamba", "service_worker_bamba", "inscription",
        "inscription_application", "connexion_utilisateur",
        "connexion_client", "deconnexion_client"
    }

    if request.endpoint == "espace_client":
        if not session.get("client_id"):
            return redirect(url_for("connexion_client"))
        return None

    if request.endpoint not in public_endpoints and not session.get("connecte"):
        return redirect(url_for("login", next=request.path))


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


@app.route("/inscription-application", methods=["GET", "POST"])
def inscription_application():
    erreur = None
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        identifiant = request.form.get("identifiant", "").strip()
        mot = request.form.get("mot", "")
        confirmation = request.form.get("confirmation", "")

        if not nom or len(nom) > 100:
            erreur = "Saisis un nom valide."
        elif len(identifiant) < 3 or len(identifiant) > 40:
            erreur = "L'identifiant doit contenir entre 3 et 40 caractères."
        elif len(mot) < 10:
            erreur = "Le mot de passe doit contenir au moins 10 caractères."
        elif mot != confirmation:
            erreur = "Les deux mots de passe ne correspondent pas."
        else:
            salt = secrets.token_bytes(16)
            password_hash = hashlib.pbkdf2_hmac(
                "sha256", mot.encode(), salt, 300000
            ).hex()
            try:
                with db_conn() as con:
                    con.execute(
                        """INSERT INTO comptes_application
                        (nom, identifiant, password_hash, salt, statut, cree_le)
                        VALUES (?, ?, ?, ?, 'en_attente', ?)""",
                        (nom, identifiant, password_hash, salt.hex(),
                         datetime.now(timezone.utc).isoformat())
                    )
                flash("Demande envoyée. Attends l'approbation de l'administrateur.")
                return redirect(url_for("connexion_utilisateur"))
            except sqlite3.IntegrityError:
                erreur = "Cet identifiant est déjà utilisé."

    return render_template_string("""
    <!doctype html><html lang="fr"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Créer un compte — BAMBA-CONTROLOR</title>
    <style>
    body{font-family:Arial;background:#0b1220;color:#eef4ff;padding:24px}
    main{max-width:440px;margin:30px auto;background:#17233b;padding:24px;border-radius:16px}
    input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:8px}
    input{background:#0b1220;color:white;border:1px solid #344761}
    button{background:#38bdf8;border:0;font-weight:bold}
    .erreur{color:#fca5a5}
    </style><main>
    <h1>Créer un compte</h1>
    <p>Ton accès sera activé après approbation de l'administrateur.</p>
    {% if erreur %}<p class="erreur">{{ erreur }}</p>{% endif %}
    <form method="post">
      <label>Nom complet</label><input name="nom" maxlength="100" required>
      <label>Identifiant</label><input name="identifiant" minlength="3" maxlength="40" required>
      <label>Mot de passe (10 caractères minimum)</label>
      <input type="password" name="mot" minlength="10" required>
      <label>Confirmer le mot de passe</label>
      <input type="password" name="confirmation" minlength="10" required>
      <button type="submit">Envoyer ma demande</button>
    </form>
    <a href="{{ url_for('connexion_utilisateur') }}">J'ai déjà un compte</a>
    </main></html>
    """, erreur=erreur)


@app.route("/connexion-utilisateur", methods=["GET", "POST"])
def connexion_utilisateur():
    erreur = None
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        mot = request.form.get("mot", "")

        with db_conn() as con:
            compte = con.execute(
                """SELECT id, nom, identifiant, password_hash, salt, statut
                   FROM comptes_application WHERE identifiant = ?""",
                (identifiant,)
            ).fetchone()

        valide = False
        if compte:
            salt = bytes.fromhex(compte["salt"])
            candidat = hashlib.pbkdf2_hmac(
                "sha256", mot.encode(), salt, 300000
            ).hex()
            valide = hmac.compare_digest(candidat, compte["password_hash"])

        if not valide:
            erreur = "Identifiant ou mot de passe incorrect."
        elif compte["statut"] == "en_attente":
            erreur = "Ton compte est en attente d'approbation."
        elif compte["statut"] != "approuve":
            erreur = "Ce compte n'est pas autorisé à accéder à l'application."
        else:
            session.clear()
            session.permanent = True
            session["connecte"] = True
            session["role"] = "utilisateur"
            session["user_id"] = compte["id"]
            session["identifiant"] = compte["identifiant"]
            return redirect(url_for("index"))

    return render_template_string("""
    <!doctype html><html lang="fr"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Connexion utilisateur — BAMBA-CONTROLOR</title>
    <style>
    body{font-family:Arial;background:#0b1220;color:#eef4ff;padding:24px}
    main{max-width:440px;margin:30px auto;background:#17233b;padding:24px;border-radius:16px}
    input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:8px}
    input{background:#0b1220;color:white;border:1px solid #344761}
    button{background:#38bdf8;border:0;font-weight:bold}
    .erreur{color:#fca5a5}
    </style><main>
    <h1>BAMBA-CONTROLOR</h1>
    {% for message in get_flashed_messages() %}<p>{{ message }}</p>{% endfor %}
    {% if erreur %}<p class="erreur">{{ erreur }}</p>{% endif %}
    <form method="post">
      <label>Identifiant</label><input name="identifiant" required>
      <label>Mot de passe</label><input type="password" name="mot" required>
      <button type="submit">Se connecter</button>
    </form>
    <a href="{{ url_for('inscription_application') }}">Créer un compte</a>
    </main></html>
    """, erreur=erreur)


@app.route("/comptes", methods=["GET", "POST"])
def gestion_comptes():
    if session.get("role") != "admin":
        abort(403)

    if request.method == "POST":
        fourni = request.form.get("csrf_token", "")
        attendu = session.get("csrf_comptes", "")
        if not attendu or not hmac.compare_digest(fourni, attendu):
            abort(400)

        try:
            compte_id = int(request.form.get("compte_id", ""))
        except ValueError:
            abort(400)

        action = request.form.get("action", "")
        if action not in ("approuve", "refuse"):
            abort(400)

        with db_conn() as con:
            con.execute(
                "UPDATE comptes_application SET statut=? WHERE id=?",
                (action, compte_id)
            )
        flash("Compte approuvé." if action == "approuve" else "Compte refusé.")
        return redirect(url_for("gestion_comptes"))

    jeton = session.setdefault("csrf_comptes", secrets.token_urlsafe(32))
    with db_conn() as con:
        comptes = con.execute(
            """SELECT id, nom, identifiant, statut, cree_le
               FROM comptes_application
               ORDER BY CASE statut WHEN 'en_attente' THEN 0
               WHEN 'approuve' THEN 1 ELSE 2 END, id DESC"""
        ).fetchall()

    return render_template_string("""
    <!doctype html><html lang="fr"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Demandes de comptes — BAMBA-CONTROLOR</title>
    <style>
    body{font-family:Arial;background:#0b1220;color:#eef4ff;padding:20px}
    main{max-width:900px;margin:auto}article{background:#17233b;padding:16px;margin:12px 0;border-radius:12px}
    button{padding:10px;border:0;border-radius:7px;margin:5px;cursor:pointer}
    .ok{background:#16a34a;color:white}.non{background:#b9384b;color:white}
    a{color:#8edcff}
    </style><main>
    <h1>Demandes de comptes</h1>
    <p><a href="{{ url_for('index') }}">Retour au tableau de bord</a></p>
    {% for message in get_flashed_messages() %}<p>{{ message }}</p>{% endfor %}
    {% for c in comptes %}
      <article>
        <strong>{{ c['nom'] }}</strong> — {{ c['identifiant'] }}<br>
        Statut : <strong>{{ c['statut'] }}</strong><br>
        Demande : {{ c['cree_le'] }}
        <form method="post">
          <input type="hidden" name="csrf_token" value="{{ jeton }}">
          <input type="hidden" name="compte_id" value="{{ c['id'] }}">
          <button class="ok" name="action" value="approuve">Approuver</button>
          <button class="non" name="action" value="refuse">Refuser</button>
        </form>
      </article>
    {% else %}
      <p>Aucune demande de compte.</p>
    {% endfor %}
    </main></html>
    """, comptes=comptes, jeton=jeton)



@app.route("/login", methods=["GET", "POST"])
def login():
    erreur = False
    if request.method == "POST":
        if verify_password(request.form.get("mot", "")):
            session.clear()
            session.permanent = True
            session["connecte"] = True
            session["role"] = "admin"
            return redirect(url_for("index"))
        erreur = True
    return render_template_string(LOGIN_PAGE, erreur=erreur)

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
        tickets=tickets, operations=operations)

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
    global AUTH
    old = request.form.get("ancien", "")
    new = request.form.get("nouveau", "")
    confirm = request.form.get("confirmation", "")
    if not verify_password(old):
        flash("Le mot de passe actuel est incorrect.")
        return redirect(url_for("index"))
    if len(new) < 10:
        flash("Le nouveau mot de passe doit contenir au moins 10 caractères.")
        return redirect(url_for("index"))
    if new != confirm:
        flash("Les deux nouveaux mots de passe ne correspondent pas.")
        return redirect(url_for("index"))
    if os.environ.get("ADMIN_PASSWORD_HASH"):
        flash("Sur le serveur hébergé, change le mot de passe en mettant à jour les variables secrètes du serveur. Aucun secret ne sera affiché ici.")
        return redirect(url_for("index"))
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", new.encode(), salt, 300000).hex()
    AUTH = {"salt": salt.hex(), "password_hash": hashed, "secret_key": app.config["SECRET_KEY"]}
    temp = AUTH_FILE.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(AUTH, f)
    try:
        os.chmod(temp, 0o600)
    except OSError:
        pass
    temp.replace(AUTH_FILE)
    session.clear()
    flash("Mot de passe changé. Reconnecte-toi avec le nouveau mot de passe.")
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

@app.route("/favicon.ico")
def favicon_bamba():
    return redirect(url_for("static", filename="icone_bamba.png"))


@app.route("/health")
def health():
    # Minimal health check for the hosting platform; no private data returned.
    return {"status": "ok"}



# Extensions API BAMBA-CONTROLOR
try:
    from bamba_extensions import bamba_ext, ext_init
    ext_init()
    app.register_blueprint(bamba_ext)
except Exception as exc:
    print("Extensions BAMBA non initialisees :", exc)

# BAMBA_FEATURES_REGISTERED
try:
    from bamba_features import bamba_bp, init_features
    app.register_blueprint(bamba_bp)
    init_features()
except Exception as exc:
    print("Module complémentaire BAMBA non initialisé :", exc)


# Extension complémentaire BAMBA CONTROLOR
from bamba_extra import bamba_extra_bp, init_extra
init_extra()
app.register_blueprint(bamba_extra_bp)


# Module complémentaire BAMBA (sites, routeurs, revendeurs, vouchers)
try:
    from bamba_suite import suite, init_suite
    init_suite()
    app.register_blueprint(suite)
except Exception as exc:
    print("Module BAMBA SUITE non initialisé :", exc)



# Theme visuel BAMBA bleu lumineux
from theme_bamba import installer_theme_bamba
installer_theme_bamba(app)

if __name__ == "__main__":
    with db_conn() as con:
        con.execute("INSERT OR IGNORE INTO vendeurs(nom,actif) VALUES(?,1)", ("Vendeur principal",))
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)


# Installation PWA BAMBA-CONTROLOR
@app.route("/service-worker.js")
def service_worker_bamba():
    fichier = BASE_DIR / "static" / "service-worker.js"
    response = app.response_class(
        fichier.read_text(encoding="utf-8"),
        mimetype="application/javascript"
    )
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.after_request
def ajouter_installation_pwa(response):
    if response.mimetype != "text/html":
        return response

    html = response.get_data(as_text=True)
    if "</head>" not in html.lower() or 'rel="manifest"' in html:
        return response

    balises = """
<link rel="manifest" href="/static/manifest.webmanifest">
<meta name="theme-color" content="#101827">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">
<script>
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/service-worker.js").catch(function (err) {
      console.warn("Installation PWA indisponible :", err);
    });
  });
}
</script>
"""
    position = html.lower().find("</head>")
    html = html[:position] + balises + html[position:]
    response.set_data(html)
    return response
