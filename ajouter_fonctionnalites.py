from pathlib import Path
import sqlite3
import re
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
DB = ROOT / "bamba.db"
MODULE = ROOT / "bamba_features.py"

if not APP.exists() or not DB.exists():
    sys.exit("ERREUR : app.py ou bamba.db introuvable. Aucun changement effectué.")

source = APP.read_text(encoding="utf-8")
marker = "# BAMBA_FEATURES_REGISTERED"

if marker in source:
    print("Le module semble déjà intégré. Vérification de la base...")
else:
    if "if __name__ == '__main__':" not in source and 'if __name__ == "__main__":' not in source:
        sys.exit("Point d'intégration introuvable. Sauvegardes conservées ; app.py non modifié.")

    module_code = r'''
import os
import json
import sqlite3
import secrets
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template_string

bamba_bp = Blueprint("bamba_features", __name__, url_prefix="/bamba")
BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("BAMBA_DB", str(BASE / "bamba.db")))

def conn():
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    return c

def init_features():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS bamba_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            prix INTEGER NOT NULL CHECK(prix >= 0),
            duree_jours INTEGER NOT NULL DEFAULT 30,
            actif INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS bamba_abonnements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            nom_client TEXT,
            plan_code TEXT NOT NULL,
            debut TEXT,
            fin TEXT,
            statut TEXT NOT NULL DEFAULT 'en_attente',
            transaction_id TEXT UNIQUE,
            cree_le TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bamba_paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            plan_code TEXT NOT NULL,
            montant INTEGER NOT NULL,
            statut TEXT NOT NULL DEFAULT 'en_attente',
            payment_url TEXT,
            cree_le TEXT NOT NULL,
            confirme_le TEXT
        );
        CREATE TABLE IF NOT EXISTS bamba_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            montant INTEGER NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'valide',
            cree_le TEXT NOT NULL,
            expire_le TEXT
        );
        CREATE TABLE IF NOT EXISTS bamba_config (
            cle TEXT PRIMARY KEY,
            valeur TEXT NOT NULL DEFAULT ''
        );
        """)
        plans = [
            ("decouverte", "Découverte", 4000, 30),
            ("starter", "Starter", 8000, 30),
            ("pro", "Pro", 15000, 30),
            ("business", "Business", 25000, 30),
        ]
        for p in plans:
            c.execute(
                "INSERT OR IGNORE INTO bamba_plans(code,nom,prix,duree_jours) VALUES(?,?,?,?)",
                p
            )
        c.execute("INSERT OR IGNORE INTO bamba_config(cle,valeur) VALUES('nom','BAMBA-CONTROLOR')")
        c.execute("INSERT OR IGNORE INTO bamba_config(cle,valeur) VALUES('mikrotik_url','')")
        c.execute("INSERT OR IGNORE INTO bamba_config(cle,valeur) VALUES('mikrotik_user','')")
        # Ne jamais enregistrer de mot de passe ou de clé API par défaut.
        c.commit()

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("connecte"):
            return jsonify({"erreur":"Connexion administrateur requise"}), 401
        return fn(*args, **kwargs)
    return wrapped

def now():
    return datetime.now().isoformat(timespec="seconds")

def cinetpay_call(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))

@bamba_bp.get("/")
@admin_required
def accueil():
    with conn() as c:
        plans = [dict(r) for r in c.execute("SELECT * FROM bamba_plans ORDER BY prix")]
        paiements = [dict(r) for r in c.execute("SELECT * FROM bamba_paiements ORDER BY id DESC LIMIT 20")]
        abonnements = [dict(r) for r in c.execute("SELECT * FROM bamba_abonnements ORDER BY id DESC LIMIT 20")]
        tickets = c.execute("SELECT COUNT(*) FROM bamba_tickets").fetchone()[0]
        total = c.execute("SELECT COALESCE(SUM(montant),0) FROM bamba_paiements WHERE statut='paye'").fetchone()[0]
    return render_template_string("""
    <!doctype html><html lang="fr"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>BAMBA-CONTROLOR</title>
    <style>
    body{font-family:system-ui;background:#101827;color:#eef2ff;margin:0;padding:20px}
    header{background:#16243a;padding:20px;border-radius:16px;border-left:5px solid #eab308}
    h1{margin:0;color:#facc15}h2{margin-top:26px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px}
    .card{background:#1e293b;padding:16px;border-radius:12px;overflow-wrap:anywhere}
    a{color:#facc15}table{border-collapse:collapse;width:100%;background:#1e293b}
    td,th{padding:9px;border-bottom:1px solid #475569;text-align:left}
    .scroll{overflow:auto}small{color:#cbd5e1}
    </style>
    <header><h1>◈ BAMBA</h1><p>Gestion Wi-Fi • Abonnements • Paiements</p></header>
    <h2>Statistiques</h2><div class="grid">
    <div class="card">Paiements confirmés<h2>{{ total }} FCFA</h2></div>
    <div class="card">Tickets créés<h2>{{ tickets }}</h2></div>
    <div class="card">Formules<h2>{{ plans|length }}</h2></div></div>
    <h2>Formules d'abonnement</h2><div class="scroll"><table><tr><th>Nom</th><th>Prix</th><th>Durée</th><th>État</th></tr>
    {% for p in plans %}<tr><td>{{p.nom}}</td><td>{{p.prix}} FCFA</td><td>{{p.duree_jours}} jours</td><td>{{'Active' if p.actif else 'Désactivée'}}</td></tr>{% endfor %}
    </table></div>
    <h2>Créer un ticket</h2><form method="post" action="{{url_for('bamba_features.creer_ticket')}}">
    <label>Montant FCFA <input name="montant" type="number" min="0" value="100" required></label>
    <button>Créer le ticket</button></form>
    <h2>Derniers paiements</h2><div class="scroll"><table><tr><th>Transaction</th><th>Montant</th><th>Statut</th></tr>
    {% for p in paiements %}<tr><td>{{p.transaction_id}}</td><td>{{p.montant}} FCFA</td><td>{{p.statut}}</td></tr>{% else %}<tr><td colspan="3">Aucun paiement enregistré</td></tr>{% endfor %}
    </table></div>
    <h2>Derniers abonnements</h2><div class="scroll"><table><tr><th>Client</th><th>Formule</th><th>Statut</th><th>Fin</th></tr>
    {% for a in abonnements %}<tr><td>{{a.nom_client or a.client_id or 'Client'}}</td><td>{{a.plan_code}}</td><td>{{a.statut}}</td><td>{{a.fin or '-'}}</td></tr>{% else %}<tr><td colspan="4">Aucun abonnement</td></tr>{% endfor %}
    </table></div><p><small>Les paiements et le routeur restent en mode non configuré tant que leurs accès ne sont pas fournis.</small></p>
    </html>
    """, plans=plans, paiements=paiements, abonnements=abonnements, tickets=tickets, total=total)

@bamba_bp.get("/api/plans")
def liste_plans():
    with conn() as c:
        rows = [dict(r) for r in c.execute("SELECT code,nom,prix,duree_jours FROM bamba_plans WHERE actif=1 ORDER BY prix")]
    return jsonify(rows)

@bamba_bp.post("/tickets")
@admin_required
def creer_ticket():
    try:
        montant = int(request.form.get("montant", request.json.get("montant", 0) if request.is_json else 0))
        if montant < 0 or montant > 100000000:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"erreur":"Montant invalide"}), 400
    code = secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12].upper()
    with conn() as c:
        c.execute("INSERT INTO bamba_tickets(code,montant,cree_le) VALUES(?,?,?)", (code,montant,now()))
        c.commit()
    return jsonify({"code":code,"montant":montant,"verification":"/bamba/tickets/"+code,"qr":"/bamba/tickets/"+code+"/qr","impression":"/bamba/tickets/"+code+"/imprimer"}), 201

@bamba_bp.get("/tickets/<code>")
def verifier_ticket(code):
    with conn() as c:
        row = c.execute("SELECT code,montant,statut,cree_le,expire_le FROM bamba_tickets WHERE code=?", (code.upper(),)).fetchone()
    if not row:
        return jsonify({"valide":False,"message":"Ticket introuvable"}), 404
    valide = row["statut"] == "valide" and (not row["expire_le"] or row["expire_le"] > now())
    return jsonify({"valide":valide,"ticket":dict(row)})

@bamba_bp.get("/tickets/<code>/qr")
def qr_ticket(code):
    with conn() as c:
        row = c.execute("SELECT code FROM bamba_tickets WHERE code=?", (code.upper(),)).fetchone()
    if not row:
        return jsonify({"erreur":"Ticket introuvable"}), 404
    try:
        import qrcode
        from io import BytesIO
        from flask import send_file
        import socket
        # Utiliser l'URL publique si elle est définie pour que le QR soit scannable.
        base = os.environ.get("BAMBA_PUBLIC_URL", request.url_root.rstrip("/"))
        img = qrcode.make(base + "/bamba/tickets/" + code.upper())
        bio = BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        return send_file(bio, mimetype="image/png")
    except ImportError:
        return jsonify({"erreur":"Installez qrcode[pil] pour générer les images QR","code":code}), 503

@bamba_bp.get("/tickets/<code>/imprimer")
def imprimer_ticket(code):
    with conn() as c:
        row = c.execute("SELECT * FROM bamba_tickets WHERE code=?", (code.upper(),)).fetchone()
    if not row:
        return jsonify({"erreur":"Ticket introuvable"}), 404
    return render_template_string("""
    <!doctype html><html lang="fr"><meta charset="utf-8"><title>Ticket BAMBA</title>
    <style>body{font-family:Arial;text-align:center;padding:24px}.ticket{border:2px dashed #222;max-width:350px;margin:auto;padding:20px}img{width:180px}</style>
    <div class="ticket"><h1>◈ BAMBA</h1><h2>Ticket Wi-Fi</h2><p>Code : <b>{{t.code}}</b></p>
    <p>Valeur : {{t.montant}} FCFA</p><p>Créé le : {{t.cree_le}}</p>
    <img src="{{url_for('bamba_features.qr_ticket',code=t.code)}}" alt="QR code"><p>Scannez pour vérifier</p></div>
    <script>window.print()</script></html>
    """, t=dict(row))

@bamba_bp.post("/paiements/initialiser")
def initier_paiement():
    if not session.get("client_id"):
        return jsonify({"erreur":"Connectez-vous à votre espace client avant de payer"}), 401
    apikey = os.environ.get("CINETPAY_APIKEY", "")
    site_id = os.environ.get("CINETPAY_SITE_ID", "")
    public_url = os.environ.get("BAMBA_PUBLIC_URL", "").rstrip("/")
    if not apikey or not site_id or not public_url.startswith("https://"):
        return jsonify({"erreur":"Configuration CinetPay incomplète : API key, site ID et URL HTTPS publique requis"}), 503
    data = request.get_json(silent=True) or request.form
    plan_code = str(data.get("plan_code","")).lower()
    with conn() as c:
        plan = c.execute("SELECT * FROM bamba_plans WHERE code=? AND actif=1", (plan_code,)).fetchone()
        if not plan:
            return jsonify({"erreur":"Formule inconnue"}), 400
        transaction = "BAMBA" + secrets.token_hex(12).upper()
        payload = {
            "apikey":apikey, "site_id":site_id, "transaction_id":transaction,
            "amount":int(plan["prix"]), "currency":"XOF",
            "description":"Abonnement "+plan["nom"],
            "customer_id":str(session["client_id"]),
            "customer_name":str(data.get("nom","Client"))[:100],
            "customer_email":str(data.get("email","client@example.com"))[:150],
            "customer_phone_number":str(data.get("telephone","00000000"))[:30],
            "notify_url":public_url+"/bamba/paiements/notification",
            "return_url":public_url+"/bamba/paiements/retour",
            "channels":"ALL","lang":"FR"
        }
        c.execute("INSERT INTO bamba_paiements(transaction_id,client_id,plan_code,montant,cree_le) VALUES(?,?,?,?,?)",
                  (transaction,session["client_id"],plan_code,int(plan["prix"]),now()))
        c.commit()
    try:
        result = cinetpay_call("https://api-checkout.cinetpay.com/v2/payment", payload)
        if result.get("code") != "201" or not result.get("data",{}).get("payment_url"):
            return jsonify({"erreur":"CinetPay n'a pas fourni de lien de paiement","details":result}), 502
        pay_url = result["data"]["payment_url"]
        with conn() as c:
            c.execute("UPDATE bamba_paiements SET payment_url=? WHERE transaction_id=?", (pay_url,transaction))
            c.commit()
        return jsonify({"transaction_id":transaction,"payment_url":pay_url})
    except Exception:
        return jsonify({"erreur":"Impossible de contacter CinetPay. Vérifiez la configuration et réessayez."}), 502

def confirmer_paiement(transaction):
    apikey = os.environ.get("CINETPAY_APIKEY", "")
    site_id = os.environ.get("CINETPAY_SITE_ID", "")
    if not apikey or not site_id:
        return False
    with conn() as c:
        payment = c.execute("SELECT * FROM bamba_paiements WHERE transaction_id=?", (transaction,)).fetchone()
        if not payment or payment["statut"] == "paye":
            return bool(payment and payment["statut"] == "paye")
    result = cinetpay_call("https://api-checkout.cinetpay.com/v2/payment/check",
                           {"apikey":apikey,"site_id":site_id,"transaction_id":transaction})
    data = result.get("data",{})
    if result.get("code") != "00" or data.get("status") != "ACCEPTED":
        return False
    if int(float(data.get("amount",0))) != int(payment["montant"]):
        return False
    with conn() as c:
        current = c.execute("SELECT * FROM bamba_paiements WHERE transaction_id=?", (transaction,)).fetchone()
        if current["statut"] == "paye":
            return True
        c.execute("UPDATE bamba_paiements SET statut='paye',confirme_le=? WHERE transaction_id=?", (now(),transaction))
        plan = c.execute("SELECT duree_jours FROM bamba_plans WHERE code=?", (current["plan_code"],)).fetchone()
        debut = datetime.now()
        fin = debut + timedelta(days=int(plan["duree_jours"] if plan else 30))
        c.execute("""INSERT INTO bamba_abonnements(client_id,plan_code,debut,fin,statut,transaction_id,cree_le)
                     VALUES(?,?,?,?,?,?,?)""",
                  (current["client_id"],current["plan_code"],debut.isoformat(timespec="seconds"),
                   fin.isoformat(timespec="seconds"),"actif",transaction,now()))
        c.commit()
    return True

@bamba_bp.post("/paiements/notification")
def notification_paiement():
    data = request.form or request.get_json(silent=True) or {}
    transaction = str(data.get("cpm_trans_id") or data.get("transaction_id") or "")
    if not transaction:
        return "transaction_id manquant", 400
    try:
        confirmer_paiement(transaction)
    except Exception:
        return "Vérification différée", 503
    return "OK", 200

@bamba_bp.get("/paiements/retour")
def retour_paiement():
    transaction = request.args.get("transaction_id","")
    if transaction:
        try:
            ok = confirmer_paiement(transaction)
        except Exception:
            ok = False
        if ok:
            return "Paiement confirmé par vérification serveur. Vous pouvez retourner à votre espace client."
    return "Retour reçu. Le paiement doit encore être vérifié côté serveur ; consultez votre espace client."

@bamba_bp.get("/api/statistiques")
@admin_required
def statistiques():
    with conn() as c:
        return jsonify({
            "paiements_confirmes_fcfa": c.execute("SELECT COALESCE(SUM(montant),0) FROM bamba_paiements WHERE statut='paye'").fetchone()[0],
            "paiements_en_attente": c.execute("SELECT COUNT(*) FROM bamba_paiements WHERE statut='en_attente'").fetchone()[0],
            "abonnements_actifs": c.execute("SELECT COUNT(*) FROM bamba_abonnements WHERE statut='actif' AND fin>?", (now(),)).fetchone()[0],
            "tickets": c.execute("SELECT COUNT(*) FROM bamba_tickets").fetchone()[0]
        })

@bamba_bp.get("/mikrotik/etat")
@admin_required
def etat_mikrotik():
    url = os.environ.get("MIKROTIK_URL","").rstrip("/")
    user = os.environ.get("MIKROTIK_USER","")
    password = os.environ.get("MIKROTIK_PASSWORD","")
    if not url.startswith("https://") or not user or not password:
        return jsonify({"configure":False,"message":"Configurer MIKROTIK_URL, MIKROTIK_USER et MIKROTIK_PASSWORD. Utilisez HTTPS."}), 503
    import base64
    req = urllib.request.Request(url+"/rest/system/resource",
        headers={"Authorization":"Basic "+base64.b64encode((user+":"+password).encode()).decode()})
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            return jsonify({"configure":True,"ressources":json.loads(response.read().decode())})
    except Exception:
        return jsonify({"configure":True,"connecte":False,"message":"Routeur inaccessible ou authentification refusée"}), 502
'''
    MODULE.write_text(module_code, encoding="utf-8")

    # Enregistrer le blueprint avant le démarrage Flask.
    pos = source.rfind("if __name__ == '__main__':")
    if pos < 0:
        pos = source.rfind('if __name__ == "__main__":')
    insertion = """
# BAMBA_FEATURES_REGISTERED
try:
    from bamba_features import bamba_bp, init_features
    app.register_blueprint(bamba_bp)
    init_features()
except Exception as exc:
    print("Module complémentaire BAMBA non initialisé :", exc)
"""
    source = source[:pos] + insertion + "\n" + source[pos:]
    APP.write_text(source, encoding="utf-8")
    print("Module ajouté et blueprint enregistré.")

# Vérifier que la base s'ouvre et que les nouvelles tables existent.
try:
    from bamba_features import init_features
    init_features()
except Exception as exc:
    sys.exit("Module créé mais initialisation impossible : " + str(exc))

print("Installation terminée.")
print("Routes complémentaires : /bamba/ ; /bamba/api/plans ; /bamba/api/statistiques ; /bamba/mikrotik/etat")
print("Tickets : POST /bamba/tickets ; vérification /bamba/tickets/CODE ; QR /bamba/tickets/CODE/qr")
print("Paiements : POST /bamba/paiements/initialiser ; notification /bamba/paiements/notification")
print("IMPORTANT : les clés CinetPay, l'URL HTTPS publique et les identifiants MikroTik restent à configurer.")
