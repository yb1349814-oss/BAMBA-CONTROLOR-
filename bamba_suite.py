
import os
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Blueprint, request, jsonify, session, render_template_string

suite = Blueprint("bamba_suite", __name__, url_prefix="/suite")
BASE_SUITE = Path(__file__).resolve().parent
DB_SUITE = Path(os.environ.get("BAMBA_DB", str(BASE_SUITE / "bamba.db")))

def db():
    c = sqlite3.connect(DB_SUITE, timeout=20)
    c.row_factory = sqlite3.Row
    return c

def heure():
    return datetime.now().isoformat(timespec="seconds")

def admin_suite(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"erreur": "Accès administrateur requis"}), 401
        return fn(*args, **kwargs)
    return wrapper

def init_suite():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS suite_sites(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            ville TEXT NOT NULL DEFAULT '',
            adresse TEXT NOT NULL DEFAULT '',
            statut TEXT NOT NULL DEFAULT 'actif',
            cree_le TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS suite_routeurs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            nom TEXT NOT NULL,
            adresse TEXT NOT NULL DEFAULT '',
            modele TEXT NOT NULL DEFAULT 'MikroTik',
            statut TEXT NOT NULL DEFAULT 'a_configurer',
            cree_le TEXT NOT NULL,
            FOREIGN KEY(site_id) REFERENCES suite_sites(id)
        );
        CREATE TABLE IF NOT EXISTS suite_revendeurs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            telephone TEXT NOT NULL DEFAULT '',
            commission REAL NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'actif',
            cree_le TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS suite_vouchers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            site_id INTEGER,
            revendeur_id INTEGER,
            prix_fcfa INTEGER NOT NULL DEFAULT 0,
            duree_minutes INTEGER NOT NULL DEFAULT 60,
            statut TEXT NOT NULL DEFAULT 'disponible',
            cree_le TEXT NOT NULL,
            FOREIGN KEY(site_id) REFERENCES suite_sites(id),
            FOREIGN KEY(revendeur_id) REFERENCES suite_revendeurs(id)
        );
        CREATE TABLE IF NOT EXISTS suite_journal(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            cree_le TEXT NOT NULL
        );
        """)

def journal(action, details=""):
    with db() as c:
        c.execute(
            "INSERT INTO suite_journal(action,details,cree_le) VALUES(?,?,?)",
            (action, str(details)[:500], heure())
        )

@ suite.get("/")
@admin_suite
def tableau():
    with db() as c:
        stats = {
            "sites": c.execute("SELECT COUNT(*) FROM suite_sites").fetchone()[0],
            "routeurs": c.execute("SELECT COUNT(*) FROM suite_routeurs").fetchone()[0],
            "revendeurs": c.execute("SELECT COUNT(*) FROM suite_revendeurs").fetchone()[0],
            "vouchers": c.execute("SELECT COUNT(*) FROM suite_vouchers").fetchone()[0],
            "disponibles": c.execute(
                "SELECT COUNT(*) FROM suite_vouchers WHERE statut='disponible'"
            ).fetchone()[0],
        }
        sites = [dict(x) for x in c.execute(
            "SELECT * FROM suite_sites ORDER BY id DESC LIMIT 100"
        )]
        routeurs = [dict(x) for x in c.execute("""
            SELECT r.*, s.nom AS site_nom FROM suite_routeurs r
            LEFT JOIN suite_sites s ON s.id=r.site_id
            ORDER BY r.id DESC LIMIT 100
        """)]
        revendeurs = [dict(x) for x in c.execute(
            "SELECT * FROM suite_revendeurs ORDER BY id DESC LIMIT 100"
        )]
        vouchers = [dict(x) for x in c.execute(
            "SELECT * FROM suite_vouchers ORDER BY id DESC LIMIT 100"
        )]
        logs = [dict(x) for x in c.execute(
            "SELECT * FROM suite_journal ORDER BY id DESC LIMIT 30"
        )]
    return render_template_string(PAGE, stats=stats, sites=sites,
        routeurs=routeurs, revendeurs=revendeurs, vouchers=vouchers, logs=logs)

@ suite.get("/api")
@admin_suite
def api_stats():
    with db() as c:
        return jsonify({
            "statistiques": {
                "sites": c.execute("SELECT COUNT(*) FROM suite_sites").fetchone()[0],
                "routeurs": c.execute("SELECT COUNT(*) FROM suite_routeurs").fetchone()[0],
                "revendeurs": c.execute("SELECT COUNT(*) FROM suite_revendeurs").fetchone()[0],
                "vouchers": c.execute("SELECT COUNT(*) FROM suite_vouchers").fetchone()[0],
                "vouchers_disponibles": c.execute(
                    "SELECT COUNT(*) FROM suite_vouchers WHERE statut='disponible'"
                ).fetchone()[0],
            },
            "note": "Les routeurs et paiements externes nécessitent une configuration réelle."
        })

@ suite.post("/api/sites")
@admin_suite
def ajouter_site():
    d = request.get_json(silent=True) or request.form
    nom = str(d.get("nom", "")).strip()[:120]
    if not nom:
        return jsonify({"erreur": "Le nom du site est obligatoire"}), 400
    ville = str(d.get("ville", "")).strip()[:100]
    adresse = str(d.get("adresse", "")).strip()[:250]
    with db() as c:
        cur = c.execute(
            "INSERT INTO suite_sites(nom,ville,adresse,cree_le) VALUES(?,?,?,?)",
            (nom, ville, adresse, heure())
        )
        ident = cur.lastrowid
    journal("site_cree", nom)
    return jsonify({"ok": True, "id": ident, "nom": nom}), 201

@ suite.post("/api/routeurs")
@admin_suite
def ajouter_routeur():
    d = request.get_json(silent=True) or request.form
    nom = str(d.get("nom", "")).strip()[:120]
    adresse = str(d.get("adresse", "")).strip()[:250]
    modele = str(d.get("modele", "MikroTik")).strip()[:80]
    try:
        site_id = int(d.get("site_id", 0)) or None
    except (TypeError, ValueError):
        return jsonify({"erreur": "Identifiant du site invalide"}), 400
    if not nom:
        return jsonify({"erreur": "Le nom du routeur est obligatoire"}), 400
    with db() as c:
        if site_id and not c.execute(
            "SELECT id FROM suite_sites WHERE id=?", (site_id,)
        ).fetchone():
            return jsonify({"erreur": "Site introuvable"}), 404
        cur = c.execute("""
            INSERT INTO suite_routeurs(site_id,nom,adresse,modele,cree_le)
            VALUES(?,?,?,?,?)
        """, (site_id, nom, adresse, modele, heure()))
        ident = cur.lastrowid
    journal("routeur_enregistre", nom)
    return jsonify({
        "ok": True, "id": ident,
        "statut": "a_configurer",
        "message": "Enregistré ; cela ne prouve pas que le routeur est connecté."
    }), 201

@ suite.post("/api/revendeurs")
@admin_suite
def ajouter_revendeur():
    d = request.get_json(silent=True) or request.form
    nom = str(d.get("nom", "")).strip()[:120]
    telephone = str(d.get("telephone", "")).strip()[:40]
    try:
        commission = float(d.get("commission", 0))
        if not 0 <= commission <= 100:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"erreur": "Commission attendue entre 0 et 100 %"}), 400
    if not nom:
        return jsonify({"erreur": "Le nom du revendeur est obligatoire"}), 400
    with db() as c:
        cur = c.execute("""
            INSERT INTO suite_revendeurs(nom,telephone,commission,cree_le)
            VALUES(?,?,?,?)
        """, (nom, telephone, commission, heure()))
        ident = cur.lastrowid
    journal("revendeur_cree", nom)
    return jsonify({"ok": True, "id": ident}), 201

@ suite.post("/api/vouchers")
@admin_suite
def ajouter_vouchers():
    d = request.get_json(silent=True) or request.form
    try:
        quantite = int(d.get("quantite", 1))
        prix = int(d.get("prix_fcfa", 0))
        duree = int(d.get("duree_minutes", 60))
        site_id = int(d.get("site_id", 0)) or None
        revendeur_id = int(d.get("revendeur_id", 0)) or None
        if not 1 <= quantite <= 500 or not 0 <= prix <= 100000000:
            raise ValueError()
        if not 1 <= duree <= 525600:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"erreur": "Quantité, prix ou durée invalide"}), 400
    with db() as c:
        if site_id and not c.execute(
            "SELECT id FROM suite_sites WHERE id=?", (site_id,)
        ).fetchone():
            return jsonify({"erreur": "Site introuvable"}), 404
        if revendeur_id and not c.execute(
            "SELECT id FROM suite_revendeurs WHERE id=?", (revendeur_id,)
        ).fetchone():
            return jsonify({"erreur": "Revendeur introuvable"}), 404
        codes = []
        for _ in range(quantite):
            for tentative in range(5):
                code = secrets.token_hex(5).upper()
                try:
                    c.execute("""
                        INSERT INTO suite_vouchers
                        (code,site_id,revendeur_id,prix_fcfa,duree_minutes,cree_le)
                        VALUES(?,?,?,?,?,?)
                    """, (code, site_id, revendeur_id, prix, duree, heure()))
                    codes.append(code)
                    break
                except sqlite3.IntegrityError:
                    if tentative == 4:
                        raise
    journal("vouchers_crees", "Quantité : " + str(len(codes)))
    return jsonify({"ok": True, "quantite": len(codes), "codes": codes}), 201

@ suite.post("/api/vouchers/<int:ident>/statut")
@admin_suite
def statut_voucher(ident):
    d = request.get_json(silent=True) or request.form
    statut = str(d.get("statut", "")).strip().lower()
    if statut not in ("disponible", "vendu", "utilise", "annule"):
        return jsonify({"erreur": "Statut non autorisé"}), 400
    with db() as c:
        cur = c.execute(
            "UPDATE suite_vouchers SET statut=? WHERE id=?", (statut, ident)
        )
        if not cur.rowcount:
            return jsonify({"erreur": "Voucher introuvable"}), 404
    journal("statut_voucher", str(ident) + ":" + statut)
    return jsonify({"ok": True, "id": ident, "statut": statut})

@ suite.get("/api/export-vouchers.csv")
@admin_suite
def export_vouchers():
    from flask import Response
    with db() as c:
        rows = c.execute("""
            SELECT code,site_id,revendeur_id,prix_fcfa,duree_minutes,statut,cree_le
            FROM suite_vouchers ORDER BY id
        """).fetchall()
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["code","site_id","revendeur_id","prix_fcfa",
                     "duree_minutes","statut","cree_le"])
    writer.writerows([tuple(r) for r in rows])
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=bamba_vouchers.csv"}
    )

PAGE = r"""<!doctype html>
<html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BAMBA CONTROLOR — Gestion</title>
<style>
body{margin:0;background:#0f172a;color:#e5e7eb;font:15px system-ui;padding:18px}
header,.card,section{background:#1e293b;border-radius:14px;padding:16px;margin-bottom:14px}
h1,h2{color:#facc15}a{color:#fde047}input,select,button{padding:10px;margin:4px;border-radius:7px;border:1px solid #64748b;max-width:100%}
button{background:#facc15;color:#111827;font-weight:bold;cursor:pointer}
input,select{background:#0f172a;color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
table{border-collapse:collapse;width:100%;min-width:500px}
td,th{padding:8px;border-bottom:1px solid #475569;text-align:left}
.scroll{overflow:auto}small{color:#cbd5e1}.notice{color:#fde68a}
</style>
<header><h1>BAMBA-CONTROLOR</h1>
<p>Gestion complémentaire des sites, routeurs, revendeurs et vouchers.</p>
<p><a href="/">Retour au tableau principal</a></p></header>
<div class="grid">
{% for k,v in stats.items() %}<div class="card">{{k}}<h2>{{v}}</h2></div>{% endfor %}
</div>
<section><h2>Ajouter un site</h2>
<form id="site"><input name="nom" placeholder="Nom du site" required>
<input name="ville" placeholder="Ville"><input name="adresse" placeholder="Adresse">
<button>Enregistrer</button></form></section>
<section><h2>Ajouter un routeur</h2>
<form id="routeur"><input name="nom" placeholder="Nom du routeur" required>
<input name="adresse" placeholder="Adresse IP ou URL">
<select name="site_id"><option value="">Sans site associé</option>
{% for s in sites %}<option value="{{s.id}}">{{s.nom}}</option>{% endfor %}
</select><input name="modele" value="MikroTik"><button>Enregistrer</button></form>
<p class="notice">L'enregistrement ne connecte pas automatiquement le routeur.</p></section>
<section><h2>Ajouter un revendeur</h2>
<form id="revendeur"><input name="nom" placeholder="Nom" required>
<input name="telephone" placeholder="Téléphone">
<input name="commission" type="number" min="0" max="100" step="0.1" value="0">
<button>Enregistrer</button></form></section>
<section><h2>Générer des vouchers</h2>
<form id="voucher"><input name="quantite" type="number" min="1" max="500" value="10" required>
<input name="prix_fcfa" type="number" min="0" value="500" required>
<input name="duree_minutes" type="number" min="1" value="60" required>
<select name="site_id"><option value="">Tous / aucun site</option>
{% for s in sites %}<option value="{{s.id}}">{{s.nom}}</option>{% endfor %}</select>
<select name="revendeur_id"><option value="">Aucun revendeur</option>
{% for r in revendeurs %}<option value="{{r.id}}">{{r.nom}}</option>{% endfor %}</select>
<button>Créer les codes</button></form>
<p id="resultat"></p><p><a href="/suite/api/export-vouchers.csv">Exporter les vouchers CSV</a></p></section>
<section><h2>Sites</h2><div class="scroll"><table><tr><th>ID</th><th>Nom</th><th>Ville</th><th>Statut</th></tr>
{% for s in sites %}<tr><td>{{s.id}}</td><td>{{s.nom}}</td><td>{{s.ville}}</td><td>{{s.statut}}</td></tr>{% else %}<tr><td colspan="4">Aucun site</td></tr>{% endfor %}
</table></div></section>
<section><h2>Routeurs</h2><div class="scroll"><table><tr><th>Nom</th><th>Site</th><th>Adresse</th><th>État</th></tr>
{% for r in routeurs %}<tr><td>{{r.nom}}</td><td>{{r.site_nom or '-'}}</td><td>{{r.adresse}}</td><td>{{r.statut}}</td></tr>{% else %}<tr><td colspan="4">Aucun routeur</td></tr>{% endfor %}
</table></div></section>
<section><h2>Revendeurs</h2><div class="scroll"><table><tr><th>Nom</th><th>Téléphone</th><th>Commission %</th><th>Statut</th></tr>
{% for r in revendeurs %}<tr><td>{{r.nom}}</td><td>{{r.telephone}}</td><td>{{r.commission}}</td><td>{{r.statut}}</td></tr>{% else %}<tr><td colspan="4">Aucun revendeur</td></tr>{% endfor %}
</table></div></section>
<section><h2>Derniers vouchers</h2><div class="scroll"><table><tr><th>Code</th><th>Prix</th><th>Durée</th><th>Statut</th></tr>
{% for v in vouchers %}<tr><td>{{v.code}}</td><td>{{v.prix_fcfa}} FCFA</td><td>{{v.duree_minutes}} min</td><td>{{v.statut}}</td></tr>{% else %}<tr><td colspan="4">Aucun voucher</td></tr>{% endfor %}
</table></div></section>
<section><h2>Journal d'activité</h2><div class="scroll"><table><tr><th>Date</th><th>Action</th><th>Détails</th></tr>
{% for j in logs %}<tr><td>{{j.cree_le}}</td><td>{{j.action}}</td><td>{{j.details}}</td></tr>{% else %}<tr><td colspan="3">Aucune activité</td></tr>{% endfor %}
</table></div></section>
<script>
async function envoyer(form, url, cible){
 const f=document.getElementById(form);
 f.addEventListener('submit',async e=>{
  e.preventDefault();
  const data=Object.fromEntries(new FormData(f).entries());
  try{
   const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
   const j=await r.json();
   if(!r.ok) throw new Error(j.erreur||'Erreur');
   if(cible) document.getElementById(cible).textContent=
     j.codes ? 'Codes créés : '+j.codes.join(', ') : 'Enregistré avec succès.';
   else alert('Enregistré avec succès.');
   location.reload();
  }catch(err){alert(err.message);}
 });
}
envoyer('site','/suite/api/sites');
envoyer('routeur','/suite/api/routeurs');
envoyer('revendeur','/suite/api/revendeurs');
envoyer('voucher','/suite/api/vouchers','resultat');
</script></html>"""
