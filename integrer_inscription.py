from pathlib import Path
from datetime import datetime
import re
import shutil

base = Path(__file__).resolve().parent
app_file = base / "app.py"
client_file = base / "comptes_clients.py"

app = app_file.read_text(encoding="utf-8")
clients = client_file.read_text(encoding="utf-8")

# Vérifier les repères avant de toucher aux fichiers.
if "from datetime import datetime" not in app:
    raise SystemExit("Arrêt : import datetime introuvable dans app.py.")

if "@app.before_request" not in app or "@app.after_request" not in app:
    raise SystemExit("Arrêt : repères Flask introuvables.")

if "def creer_compte_client(" not in clients or "def verifier_mot_de_passe(" not in clients:
    raise SystemExit("Arrêt : fonctions clients introuvables.")

if "def inscription(" in app or '"/inscription"' in app:
    raise SystemExit("Arrêt : une route d'inscription semble déjà exister.")

# Sauvegardes supplémentaires.
tag = datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(app_file, base / f"app.py.avant_inscription_{tag}")
shutil.copy2(client_file, base / f"comptes_clients.py.avant_inscription_{tag}")

# Faire utiliser à chaque module le même chemin de base de données.
if "import os" not in clients:
    clients = clients.replace(
        "import sqlite3",
        "import sqlite3\nimport os",
        1
    )

clients = clients.replace(
    'DB = Path(__file__).resolve().parent / "bamba.db"',
    'DB = Path(os.environ.get("BAMBA_DB_PATH", str(Path(__file__).resolve().parent / "bamba.db")))',
    1
)

# Importer les fonctions de comptes clients.
app = app.replace(
    "from datetime import datetime",
    "from datetime import datetime, timezone\nfrom comptes_clients import creer_compte_client, verifier_mot_de_passe",
    1
)

routes = r'''
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


'''

# Ajouter les routes avant les contrôles d'accès.
marker = "@app.before_request\ndef require_login_for_admin():"
if marker not in app:
    raise SystemExit("Arrêt : le point d'insertion des routes est introuvable.")

app = app.replace(marker, routes + "\n" + marker, 1)

# Autoriser les pages publiques et protéger l'espace client séparément.
pattern = r'@app\.before_request\s+def require_login_for_admin\(\):.*?(?=@app\.after_request)'
nouveau_controle = '''@app.before_request
def require_login_for_admin():
    public_endpoints = {
        "login", "static", "inscription",
        "connexion_client", "deconnexion_client"
    }

    if request.endpoint == "espace_client":
        if not session.get("client_id"):
            return redirect(url_for("connexion_client"))
        return None

    if request.endpoint not in public_endpoints and not session.get("connecte"):
        return redirect(url_for("login", next=request.path))


'''
app, nombre = re.subn(pattern, nouveau_controle, app, count=1, flags=re.S)
if nombre != 1:
    raise SystemExit("Arrêt : contrôle d'accès non remplacé. Fichiers d'origine conservés.")

# Écrire seulement après validation de toutes les étapes.
client_file.write_text(clients, encoding="utf-8")
app_file.write_text(app, encoding="utf-8")

print("Intégration terminée.")
print("Sauvegardes créées :", tag)
print("Pages ajoutées : /inscription, /connexion-client, /espace-client")
print("Étape suivante : vérifier la syntaxe avant de lancer Flask.")
