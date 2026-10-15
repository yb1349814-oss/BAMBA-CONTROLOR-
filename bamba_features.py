import re
import io
import csv

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
        ("business", "Business", 25800, 30),
        ("max", "Max", 40000, 30),
    ]
    for p in plans:
        c.execute(
            "INSERT OR IGNORE INTO bamba_plans(code,nom,prix,duree_jours) VALUES(?,?,?,?)",
            p
        )
        c.execute(
            "UPDATE bamba_plans SET nom=?, prix=?, duree_jours=? WHERE code=?",
            (p[1], p[2], p[3], p[0])
        )
        c.execute("INSERT OR IGNORE INTO bamba_config(cle,valeur) VALUES('nom','BAMBA-CONTROLOR')")
        c.execute("INSERT OR IGNORE INTO bamba_config(cle,valeur) VALUES('mikrotik_url','')")
        c.execute("INSERT OR IGNORE INTO bamba_config(cle,valeur) VALUES('mikrotik_user','')")
        # Ne jamais enregistrer de mot de passe ou de clé API par défaut.
        c.commit()

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
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
    <header><div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;"><img src="/static/icone_bamba.png" alt="Icône BAMBA" style="width:64px;height:64px;object-fit:contain;"><img src="/static/logo_bamba.png" alt="BAMBA" style="width:min(100%,420px);height:auto;"></div><p>Gestion Wi-Fi • Abonnements • Paiements</p></header>
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
    transaction = str(transaction or "").strip()
    if not transaction or len(transaction) > 120:
        return False

    apikey = os.environ.get("CINETPAY_APIKEY", "")
    site_id = os.environ.get("CINETPAY_SITE_ID", "")
    if not apikey or not site_id:
        return False

    with conn() as c:
        payment = c.execute(
            "SELECT * FROM bamba_paiements WHERE transaction_id=?",
            (transaction,)
        ).fetchone()

        if not payment:
            return False
        if payment["statut"] == "paye":
            return True

    result = cinetpay_call(
        "https://api-checkout.cinetpay.com/v2/payment/check",
        {
            "apikey": apikey,
            "site_id": site_id,
            "transaction_id": transaction
        }
    )

    data = result.get("data", {})
    if result.get("code") != "00" or data.get("status") != "ACCEPTED":
        return False

    try:
        montant_verifie = float(data.get("amount", ""))
    except (TypeError, ValueError):
        return False

    if not montant_verifie.is_integer():
        return False
    if int(montant_verifie) != int(payment["montant"]):
        return False

    devise = data.get("currency")
    if devise and str(devise).upper() != "XOF":
        return False

    with conn() as c:
        c.execute("BEGIN IMMEDIATE")

        current = c.execute(
            "SELECT * FROM bamba_paiements WHERE transaction_id=?",
            (transaction,)
        ).fetchone()

        if not current:
            return False
        if current["statut"] == "paye":
            return True

        plan = c.execute(
            "SELECT duree_jours FROM bamba_plans WHERE code=?",
            (current["plan_code"],)
        ).fetchone()

        if not plan:
            return False

        abonnement_existant = c.execute(
            "SELECT id FROM bamba_abonnements WHERE transaction_id=?",
            (transaction,)
        ).fetchone()

        if not abonnement_existant:
            debut = datetime.now()
            fin = debut + timedelta(days=int(plan["duree_jours"]))

            c.execute("""
                INSERT INTO bamba_abonnements
                (client_id, plan_code, debut, fin, statut, transaction_id, cree_le)
                VALUES (?, ?, ?, ?, 'actif', ?, ?)
            """, (
                current["client_id"],
                current["plan_code"],
                debut.isoformat(timespec="seconds"),
                fin.isoformat(timespec="seconds"),
                transaction,
                now()
            ))

        c.execute("""
            UPDATE bamba_paiements
            SET statut='paye', confirme_le=?
            WHERE transaction_id=?
        """, (now(), transaction))

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


@bamba_bp.get("/api/abonnements")
@admin_required
def liste_abonnements_bamba():
    with conn() as c:
        c.execute(
            """UPDATE bamba_abonnements
               SET statut='expire'
               WHERE statut='actif' AND fin<=?""",
            (now(),)
        )
        rows = c.execute("""
            SELECT a.id, a.client_id, a.nom_client, a.plan_code,
                   p.nom AS plan_nom, a.debut, a.fin, a.statut,
                   a.transaction_id, a.cree_le
            FROM bamba_abonnements a
            LEFT JOIN bamba_plans p ON p.code=a.plan_code
            ORDER BY a.id DESC
            LIMIT 100
        """).fetchall()
        return jsonify({"abonnements": [dict(r) for r in rows]})



@bamba_bp.route("/tickets/importer-csv", methods=["GET", "POST"])
@admin_required
def importer_tickets_csv():
    if request.method == "GET":
        return """<!doctype html>
<html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Import CSV - BAMBA</title>
<h1>Import des codes Wi-Fi BAMBA</h1>
<p>Colonnes obligatoires : code, duree_minutes, prix_fcfa, mikrotik_user</p>
<form method="post" enctype="multipart/form-data">
<input type="file" name="fichier" accept=".csv,text/csv" required>
<button type="submit">Importer le CSV</button>
</form></html>"""

    fichier = request.files.get("fichier")
    if not fichier or not fichier.filename:
        return jsonify({"erreur": "Sélectionnez un fichier CSV."}), 400
    if not fichier.filename.lower().endswith(".csv"):
        return jsonify({"erreur": "Le fichier doit avoir l'extension .csv."}), 400
    if request.content_length and request.content_length > 2_000_000:
        return jsonify({"erreur": "Fichier trop volumineux : maximum 2 Mo."}), 413

    try:
        contenu = fichier.read(2_000_001)
        if len(contenu) > 2_000_000:
            return jsonify({"erreur": "Fichier trop volumineux : maximum 2 Mo."}), 413
        texte = contenu.decode("utf-8-sig")
        lecteur = csv.DictReader(io.StringIO(texte))
        requis = {"code", "duree_minutes", "prix_fcfa", "mikrotik_user"}
        entetes = {h.strip().lower() for h in (lecteur.fieldnames or []) if h}
        if not requis.issubset(entetes):
            return jsonify({
                "erreur": "Colonnes requises : code,duree_minutes,prix_fcfa,mikrotik_user"
            }), 400

        lignes = []
        erreurs = []
        for numero, ligne in enumerate(lecteur, start=2):
            if len(lignes) + len(erreurs) >= 1000:
                return jsonify({"erreur": "Maximum 1000 lignes par import."}), 400

            ligne = {(k or "").strip().lower(): (v or "").strip()
                     for k, v in ligne.items() if k is not None}
            code = ligne.get("code", "")
            utilisateur = ligne.get("mikrotik_user", "")
            try:
                duree = int(ligne.get("duree_minutes", ""))
                prix = int(ligne.get("prix_fcfa", ""))
                if not re.fullmatch(r"[A-Za-z0-9_-]{3,80}", code):
                    raise ValueError("code invalide")
                if not 1 <= duree <= 525600:
                    raise ValueError("durée hors limites")
                if not 0 <= prix <= 100_000_000:
                    raise ValueError("prix hors limites")
                if len(utilisateur) > 100:
                    raise ValueError("identifiant MikroTik trop long")
                lignes.append((numero, code, duree, prix, utilisateur))
            except (ValueError, TypeError) as exc:
                erreurs.append({"ligne": numero, "raison": str(exc)})

        importes = 0
        doublons = 0
        with conn() as c:
            colonnes = {
                r["name"] for r in c.execute("PRAGMA table_info(bamba_tickets)")
            }
            migrations = {
                "duree_minutes": "INTEGER",
                "mikrotik_user": "TEXT",
                "mikrotik_statut": "TEXT NOT NULL DEFAULT 'a_importer'"
            }
            for nom, definition in migrations.items():
                if nom not in colonnes:
                    c.execute(
                        f"ALTER TABLE bamba_tickets ADD COLUMN {nom} {definition}"
                    )

            for numero, code, duree, prix, utilisateur in lignes:
                existe = c.execute(
                    "SELECT 1 FROM bamba_tickets WHERE code=?", (code,)
                ).fetchone()
                if existe:
                    doublons += 1
                    continue
                c.execute("""
                    INSERT INTO bamba_tickets
                    (code, montant, statut, cree_le, expire_le,
                     duree_minutes, mikrotik_user, mikrotik_statut)
                    VALUES (?, ?, 'a_importer', ?, NULL, ?, ?, 'a_importer')
                """, (code, prix, now(), duree, utilisateur))
                importes += 1

        return jsonify({
            "message": "Import terminé. Les codes restent à importer sur le routeur.",
            "importes": importes,
            "doublons_ignores": doublons,
            "lignes_invalides": erreurs
        }), 200
    except UnicodeDecodeError:
        return jsonify({"erreur": "Le CSV doit être encodé en UTF-8."}), 400
    except Exception:
        return jsonify({"erreur": "Erreur pendant l'import. Vérifiez le CSV et les journaux."}), 500


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
