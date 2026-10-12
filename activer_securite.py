from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

if "auth_config.json" in s:
    print("Une configuration de sécurité semble déjà présente. Aucune modification faite.")
    raise SystemExit(0)

ancien = "from flask import Flask, render_template_string, request, redirect"
nouveau = """from flask import Flask, render_template_string, request, redirect, session, url_for
import json
import hashlib
import hmac
from functools import wraps

CONFIG = Path(__file__).with_name("auth_config.json")
with open(CONFIG, encoding="utf-8") as f:
    AUTH = json.load(f)
"""

if ancien not in s:
    print("Ligne Flask introuvable. Aucune modification faite.")
    raise SystemExit(1)

s = s.replace(ancien, nouveau, 1)
s = s.replace(
    "app = Flask(__name__)",
    """app = Flask(__name__)
app.secret_key = AUTH["secret_key"]

LOGIN_PAGE = '''
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Connexion - BAMBA-CONTROLOR</title>
<style>
body{font-family:Arial;background:#0b1220;color:#eef4ff;display:grid;place-items:center;min-height:100vh;margin:0}
form{background:#17233b;padding:28px;border-radius:16px;width:min(320px,85vw)}
input,button{box-sizing:border-box;width:100%;padding:13px;margin-top:12px;border-radius:8px;border:0}
button{background:#38bdf8;color:#082f49;font-weight:bold}
p{color:#fca5a5}
</style></head><body><form method="post">
<h2>BAMBA-CONTROLOR</h2><p>Connexion sécurisée</p>
<input type="password" name="mot" placeholder="Mot de passe" required autofocus>
<button type="submit">Se connecter</button>
{% if erreur %}<p>Mot de passe incorrect.</p>{% endif %}
</form></body></html>
'''

@app.before_request
def proteger_application():
    if request.endpoint == "login":
        return None
    if not session.get("connecte"):
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    erreur = False
    if request.method == "POST":
        mot = request.form.get("mot", "")
        sel = bytes.fromhex(AUTH["salt"])
        empreinte = hashlib.pbkdf2_hmac(
            "sha256", mot.encode(), sel, 300000
        ).hex()
        if hmac.compare_digest(empreinte, AUTH["password_hash"]):
            session.clear()
            session["connecte"] = True
            return redirect(url_for("accueil"))
        erreur = True
    return render_template_string(LOGIN_PAGE, erreur=erreur)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
""",
    1
)

Path("app.py.temp").write_text(s, encoding="utf-8")
Path("app.py.temp").replace(p)
print("Protection par mot de passe ajoutée.")
