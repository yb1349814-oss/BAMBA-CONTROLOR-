
import os
import sqlite3
from pathlib import Path
from functools import wraps
from flask import Blueprint, request, jsonify, session

bamba_ext = Blueprint("bamba_ext", __name__, url_prefix="/api/bamba")
BASE_EXT = Path(__file__).resolve().parent
DB_EXT = Path(os.environ.get(
    "BAMBA_DB_PATH", str(BASE_EXT / "bamba.db")
))

def ext_conn():
    con = sqlite3.connect(DB_EXT, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def ext_init():
    with ext_conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS organisations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            compte_id INTEGER UNIQUE,
            nom TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'actif',
            cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sites_wifi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organisation_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            adresse TEXT DEFAULT '',
            statut TEXT NOT NULL DEFAULT 'actif',
            cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(organisation_id) REFERENCES organisations(id),
            UNIQUE(organisation_id, nom)
        );

        CREATE TABLE IF NOT EXISTS routeurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organisation_id INTEGER NOT NULL,
            site_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            adresse_api TEXT DEFAULT '',
            type TEXT NOT NULL DEFAULT 'mikrotik',
            statut TEXT NOT NULL DEFAULT 'a_configurer',
            cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(organisation_id) REFERENCES organisations(id),
            FOREIGN KEY(site_id) REFERENCES sites_wifi(id)
        );

        CREATE TABLE IF NOT EXISTS revendeurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organisation_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            telephone TEXT DEFAULT '',
            taux_commission REAL NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'actif',
            cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(organisation_id) REFERENCES organisations(id)
        );

        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organisation_id INTEGER NOT NULL,
            revendeur_id INTEGER NOT NULL,
            vente_id INTEGER,
            montant INTEGER NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'en_attente',
            cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(organisation_id) REFERENCES organisations(id),
            FOREIGN KEY(revendeur_id) REFERENCES revendeurs(id)
        );

        CREATE TABLE IF NOT EXISTS sessions_wifi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organisation_id INTEGER NOT NULL,
            site_id INTEGER NOT NULL,
            ticket_code TEXT DEFAULT '',
            adresse_mac TEXT DEFAULT '',
            adresse_ip TEXT DEFAULT '',
            debut TEXT,
            fin TEXT,
            statut TEXT NOT NULL DEFAULT 'inconnue',
            FOREIGN KEY(organisation_id) REFERENCES organisations(id),
            FOREIGN KEY(site_id) REFERENCES sites_wifi(id)
        );

        CREATE TABLE IF NOT EXISTS itinerance_wifi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organisation_id INTEGER NOT NULL,
            site_source_id INTEGER NOT NULL,
            site_cible_id INTEGER NOT NULL,
            actif INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(organisation_id) REFERENCES organisations(id),
            FOREIGN KEY(site_source_id) REFERENCES sites_wifi(id),
            FOREIGN KEY(site_cible_id) REFERENCES sites_wifi(id),
            UNIQUE(organisation_id, site_source_id, site_cible_id)
        );

        CREATE TABLE IF NOT EXISTS imports_csv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organisation_id INTEGER NOT NULL,
            nom_fichier TEXT NOT NULL,
            lignes_total INTEGER NOT NULL DEFAULT 0,
            lignes_importees INTEGER NOT NULL DEFAULT 0,
            statut TEXT NOT NULL DEFAULT 'prepare',
            cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(organisation_id) REFERENCES organisations(id)
        );

        CREATE TABLE IF NOT EXISTS journaux_securite (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organisation_id INTEGER,
            evenement TEXT NOT NULL,
            details TEXT DEFAULT '',
            cree_le TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_sites_org
            ON sites_wifi(organisation_id);
        CREATE INDEX IF NOT EXISTS idx_routeurs_org
            ON routeurs(organisation_id);
        CREATE INDEX IF NOT EXISTS idx_revendeurs_org
            ON revendeurs(organisation_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_org
            ON sessions_wifi(organisation_id);
        """)

def api_login(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("connecte"):
            return jsonify({"erreur": "Connexion requise"}), 401
        if session.get("role") not in ("admin", "utilisateur"):
            return jsonify({"erreur": "Acces refuse"}), 403
        return fn(*args, **kwargs)
    return wrapped

def get_org(con, create=False):
    role = session.get("role")
    if role == "admin":
        oid = request.args.get("organisation_id", type=int)
        if oid is None and request.is_json:
            oid = (request.get_json(silent=True) or {}).get("organisation_id")
        if oid:
            return con.execute(
                "SELECT * FROM organisations WHERE id=?", (oid,)
            ).fetchone()
        return None

    uid = session.get("user_id")
    if not uid:
        return None

    org = con.execute(
        "SELECT * FROM organisations WHERE compte_id=?", (uid,)
    ).fetchone()
    if org or not create:
        return org

    compte = con.execute(
        "SELECT nom, statut FROM comptes_application WHERE id=?", (uid,)
    ).fetchone()
    if not compte or compte["statut"] != "approuve":
        return None

    con.execute(
        "INSERT OR IGNORE INTO organisations(compte_id,nom) VALUES(?,?)",
        (uid, compte["nom"])
    )
    return con.execute(
        "SELECT * FROM organisations WHERE compte_id=?", (uid,)
    ).fetchone()

def org_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with ext_conn() as con:
            org = get_org(con, create=True)
            if not org:
                return jsonify({
                    "erreur": "Organisation introuvable ou compte non approuve",
                    "conseil": "Pour l'administrateur, fournir organisation_id."
                }), 403
            request.environ["bamba_org_id"] = str(org["id"])
        return fn(*args, **kwargs)
    return wrapped

def current_org():
    return int(request.environ["bamba_org_id"])

@bamba_ext.get("/etat")
@api_login
def etat_api():
    return jsonify({
        "application": "BAMBA-CONTROLOR",
        "module": "extensions",
        "etat": "actif"
    })

@bamba_ext.get("/sites")
@api_login
@org_required
def sites_liste():
    with ext_conn() as con:
        rows = con.execute(
            "SELECT * FROM sites_wifi WHERE organisation_id=? ORDER BY id DESC",
            (current_org(),)
        ).fetchall()
        return jsonify([dict(r) for r in rows])

@bamba_ext.post("/sites")
@api_login
@org_required
def site_creer():
    data = request.get_json(silent=True) or request.form
    nom = str(data.get("nom", "")).strip()[:100]
    adresse = str(data.get("adresse", "")).strip()[:200]
    if not nom:
        return jsonify({"erreur": "Nom du site obligatoire"}), 400
    with ext_conn() as con:
        try:
            cur = con.execute(
                "INSERT INTO sites_wifi(organisation_id,nom,adresse) VALUES(?,?,?)",
                (current_org(), nom, adresse)
            )
            return jsonify({"id": cur.lastrowid, "nom": nom}), 201
        except sqlite3.IntegrityError:
            return jsonify({"erreur": "Ce nom de site existe deja"}), 409

@bamba_ext.get("/routeurs")
@api_login
@org_required
def routeurs_liste():
    with ext_conn() as con:
        rows = con.execute("""
            SELECT r.*, s.nom AS site_nom
            FROM routeurs r JOIN sites_wifi s ON s.id=r.site_id
            WHERE r.organisation_id=? ORDER BY r.id DESC
        """, (current_org(),)).fetchall()
        return jsonify([dict(r) for r in rows])

@bamba_ext.post("/routeurs")
@api_login
@org_required
def routeur_creer():
    data = request.get_json(silent=True) or request.form
    nom = str(data.get("nom", "")).strip()[:100]
    adresse = str(data.get("adresse_api", "")).strip()[:250]
    typ = str(data.get("type", "mikrotik")).strip()[:30]
    try:
        site_id = int(data.get("site_id", ""))
    except (ValueError, TypeError):
        return jsonify({"erreur": "site_id invalide"}), 400
    with ext_conn() as con:
        site = con.execute(
            "SELECT id FROM sites_wifi WHERE id=? AND organisation_id=?",
            (site_id, current_org())
        ).fetchone()
        if not site or not nom:
            return jsonify({"erreur": "Site ou nom invalide"}), 400
        cur = con.execute("""
            INSERT INTO routeurs(organisation_id,site_id,nom,adresse_api,type)
            VALUES(?,?,?,?,?)
        """, (current_org(), site_id, nom, adresse, typ))
        return jsonify({
            "id": cur.lastrowid,
            "statut": "a_configurer",
            "message": "Routeur enregistre; connexion MikroTik non activee."
        }), 201

@bamba_ext.get("/revendeurs")
@api_login
@org_required
def revendeurs_liste():
    with ext_conn() as con:
        rows = con.execute(
            "SELECT * FROM revendeurs WHERE organisation_id=? ORDER BY id DESC",
            (current_org(),)
        ).fetchall()
        return jsonify([dict(r) for r in rows])

@bamba_ext.post("/revendeurs")
@api_login
@org_required
def revendeur_creer():
    data = request.get_json(silent=True) or request.form
    nom = str(data.get("nom", "")).strip()[:100]
    tel = str(data.get("telephone", "")).strip()[:40]
    try:
        taux = float(data.get("taux_commission", 0))
        if not 0 <= taux <= 100:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"erreur": "Taux de commission invalide"}), 400
    if not nom:
        return jsonify({"erreur": "Nom obligatoire"}), 400
    with ext_conn() as con:
        cur = con.execute("""
            INSERT INTO revendeurs(
                organisation_id,nom,telephone,taux_commission
            ) VALUES(?,?,?,?)
        """, (current_org(), nom, tel, taux))
        return jsonify({"id": cur.lastrowid, "nom": nom}), 201

@bamba_ext.get("/sessions-wifi")
@api_login
@org_required
def sessions_liste():
    with ext_conn() as con:
        rows = con.execute("""
            SELECT w.*, s.nom AS site_nom
            FROM sessions_wifi w JOIN sites_wifi s ON s.id=w.site_id
            WHERE w.organisation_id=? ORDER BY w.id DESC LIMIT 200
        """, (current_org(),)).fetchall()
        return jsonify([dict(r) for r in rows])

@bamba_ext.post("/sessions-wifi")
@api_login
@org_required
def session_wifi_enregistrer():
    data = request.get_json(silent=True) or request.form
    try:
        site_id = int(data.get("site_id", ""))
    except (ValueError, TypeError):
        return jsonify({"erreur": "site_id invalide"}), 400
    with ext_conn() as con:
        site = con.execute(
            "SELECT id FROM sites_wifi WHERE id=? AND organisation_id=?",
            (site_id, current_org())
        ).fetchone()
        if not site:
            return jsonify({"erreur": "Site inconnu"}), 404
        cur = con.execute("""
            INSERT INTO sessions_wifi(
                organisation_id,site_id,ticket_code,adresse_mac,
                adresse_ip,debut,statut
            ) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP,'enregistree')
        """, (
            current_org(), site_id,
            str(data.get("ticket_code", ""))[:100],
            str(data.get("adresse_mac", ""))[:80],
            str(data.get("adresse_ip", ""))[:80]
        ))
        return jsonify({
            "id": cur.lastrowid,
            "message": "Session enregistree; cela ne connecte pas un appareil au Wi-Fi."
        }), 201

@bamba_ext.get("/commissions")
@api_login
@org_required
def commissions_liste():
    with ext_conn() as con:
        rows = con.execute("""
            SELECT c.*, r.nom AS revendeur_nom
            FROM commissions c JOIN revendeurs r ON r.id=c.revendeur_id
            WHERE c.organisation_id=? ORDER BY c.id DESC LIMIT 200
        """, (current_org(),)).fetchall()
        return jsonify([dict(r) for r in rows])

@bamba_ext.get("/itinerance")
@api_login
@org_required
def itinerance_liste():
    with ext_conn() as con:
        rows = con.execute("""
            SELECT i.*, a.nom AS site_source, b.nom AS site_cible
            FROM itinerance_wifi i
            JOIN sites_wifi a ON a.id=i.site_source_id
            JOIN sites_wifi b ON b.id=i.site_cible_id
            WHERE i.organisation_id=? ORDER BY i.id DESC
        """, (current_org(),)).fetchall()
        return jsonify([dict(r) for r in rows])

@bamba_ext.post("/itinerance")
@api_login
@org_required
def itinerance_creer():
    data = request.get_json(silent=True) or request.form
    try:
        source = int(data.get("site_source_id", ""))
        cible = int(data.get("site_cible_id", ""))
    except (ValueError, TypeError):
        return jsonify({"erreur": "Identifiants de sites invalides"}), 400
    if source == cible:
        return jsonify({"erreur": "Choisir deux sites differents"}), 400
    with ext_conn() as con:
        for sid in (source, cible):
            if not con.execute(
                "SELECT 1 FROM sites_wifi WHERE id=? AND organisation_id=?",
                (sid, current_org())
            ).fetchone():
                return jsonify({"erreur": "Site inconnu"}), 404
        try:
            cur = con.execute("""
                INSERT INTO itinerance_wifi(
                    organisation_id,site_source_id,site_cible_id,actif
                ) VALUES(?,?,?,0)
            """, (current_org(), source, cible))
            return jsonify({
                "id": cur.lastrowid,
                "actif": False,
                "message": "Regle enregistree; itinerance effective non activee."
            }), 201
        except sqlite3.IntegrityError:
            return jsonify({"erreur": "Cette regle existe deja"}), 409

@bamba_ext.get("/statistiques")
@api_login
@org_required
def statistiques_extensions():
    with ext_conn() as con:
        result = {}
        for table in ("sites_wifi", "routeurs", "revendeurs",
                      "commissions", "sessions_wifi"):
            result[table] = con.execute(
                f"SELECT COUNT(*) FROM {table} WHERE organisation_id=?",
                (current_org(),)
            ).fetchone()[0]
        return jsonify(result)
