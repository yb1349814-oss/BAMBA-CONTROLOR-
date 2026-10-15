
import csv
import io
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, request, jsonify, session, Response

bamba_extra_bp = Blueprint("bamba_extra", __name__, url_prefix="/api/bamba")
DB_PATH = Path(__file__).resolve().with_name("bamba_extra.db")


def db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def init_extra():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            category TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'info'
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'info',
            is_read INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            plan TEXT NOT NULL,
            amount INTEGER NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'XOF',
            status TEXT NOT NULL DEFAULT 'pending',
            starts_at TEXT,
            ends_at TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT NOT NULL UNIQUE,
            customer TEXT NOT NULL DEFAULT '',
            amount INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'XOF',
            status TEXT NOT NULL DEFAULT 'pending',
            provider TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)


def admin_required_extra(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("connecte"):
            return jsonify({
                "ok": False,
                "erreur": "Connexion administrateur requise"
            }), 401
        return fn(*args, **kwargs)
    return wrapper


def log_event(category, message, status="info"):
    with db() as con:
        con.execute(
            "INSERT INTO activity_log(created_at,category,message,status)"
            " VALUES(?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(),
             str(category)[:80], str(message)[:500], str(status)[:30])
        )


@bamba_extra_bp.get("/extras/etat")
def extra_health():
    return jsonify({
        "ok": True,
        "module": "BAMBA CONTROLOR Extras",
        "heure_utc": datetime.now(timezone.utc).isoformat()
    })


@bamba_extra_bp.get("/extras/tableau-de-bord")
@admin_required_extra
def extra_dashboard():
    with db() as con:
        result = {}
        for table in (
            "activity_log", "alerts", "subscriptions", "payment_records"
        ):
            result[table] = con.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

        result["alertes_non_lues"] = con.execute(
            "SELECT COUNT(*) FROM alerts WHERE is_read=0"
        ).fetchone()[0]

        result["paiements_en_attente"] = con.execute(
            "SELECT COUNT(*) FROM payment_records WHERE status='pending'"
        ).fetchone()[0]

    return jsonify({"ok": True, "donnees": result})


@bamba_extra_bp.get("/extras/activites")
@admin_required_extra
def extra_activities():
    limite = request.args.get("limite", default=50, type=int)
    limite = max(1, min(limite or 50, 200))
    with db() as con:
        rows = con.execute(
            "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?",
            (limite,)
        ).fetchall()
    return jsonify({"ok": True, "activites": [dict(r) for r in rows]})


@bamba_extra_bp.post("/extras/activites")
@admin_required_extra
def extra_add_activity():
    data = request.get_json(silent=True) or {}
    category = str(data.get("categorie", "")).strip()
    message = str(data.get("message", "")).strip()
    status = str(data.get("statut", "info")).strip()

    if not category or not message:
        return jsonify({
            "ok": False,
            "erreur": "categorie et message sont obligatoires"
        }), 400

    log_event(category, message, status)
    return jsonify({"ok": True}), 201


@bamba_extra_bp.get("/extras/alertes")
@admin_required_extra
def extra_alerts():
    with db() as con:
        rows = con.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT 200"
        ).fetchall()
    return jsonify({"ok": True, "alertes": [dict(r) for r in rows]})


@bamba_extra_bp.post("/extras/alertes")
@admin_required_extra
def extra_create_alert():
    data = request.get_json(silent=True) or {}
    title = str(data.get("titre", "")).strip()
    message = str(data.get("message", "")).strip()
    level = str(data.get("niveau", "info")).strip().lower()

    if not title or not message:
        return jsonify({
            "ok": False,
            "erreur": "titre et message sont obligatoires"
        }), 400

    if level not in {"info", "warning", "critical"}:
        return jsonify({"ok": False, "erreur": "niveau invalide"}), 400

    with db() as con:
        cur = con.execute(
            "INSERT INTO alerts(created_at,title,message,level) VALUES(?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(),
             title[:150], message[:1000], level)
        )
        alert_id = cur.lastrowid

    log_event("alerte", f"Alerte créée : {title}", level)
    return jsonify({"ok": True, "id": alert_id}), 201


@bamba_extra_bp.post("/extras/alertes/<int:alert_id>/lire")
@admin_required_extra
def extra_read_alert(alert_id):
    with db() as con:
        cur = con.execute(
            "UPDATE alerts SET is_read=1 WHERE id=?", (alert_id,)
        )
    if cur.rowcount == 0:
        return jsonify({"ok": False, "erreur": "Alerte introuvable"}), 404
    return jsonify({"ok": True})


@bamba_extra_bp.get("/extras/abonnements")
@admin_required_extra
def extra_subscriptions():
    with db() as con:
        rows = con.execute(
            "SELECT * FROM subscriptions ORDER BY id DESC LIMIT 200"
        ).fetchall()
    return jsonify({"ok": True, "abonnements": [dict(r) for r in rows]})


@bamba_extra_bp.post("/extras/abonnements")
@admin_required_extra
def extra_create_subscription():
    data = request.get_json(silent=True) or {}
    customer = str(data.get("client", "")).strip()
    plan = str(data.get("plan", "")).strip()
    status = str(data.get("statut", "pending")).strip().lower()

    try:
        amount = int(data.get("montant", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erreur": "montant invalide"}), 400

    if not customer or not plan or amount < 0:
        return jsonify({
            "ok": False,
            "erreur": "client, plan et montant valide sont obligatoires"
        }), 400

    if status not in {"pending", "active", "expired", "cancelled"}:
        return jsonify({"ok": False, "erreur": "statut invalide"}), 400

    now = datetime.now(timezone.utc).isoformat()
    with db() as con:
        cur = con.execute(
            """INSERT INTO subscriptions
            (customer,plan,amount,currency,status,starts_at,ends_at,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",
            (customer[:150], plan[:150], amount, "XOF", status,
             data.get("debut"), data.get("fin"), now)
        )
        sub_id = cur.lastrowid

    log_event("abonnement", f"Abonnement #{sub_id} créé", "info")
    return jsonify({"ok": True, "id": sub_id}), 201


@bamba_extra_bp.get("/extras/paiements")
@admin_required_extra
def extra_payments():
    with db() as con:
        rows = con.execute(
            "SELECT * FROM payment_records ORDER BY id DESC LIMIT 200"
        ).fetchall()
    return jsonify({"ok": True, "paiements": [dict(r) for r in rows]})


@bamba_extra_bp.post("/extras/paiements")
@admin_required_extra
def extra_register_payment():
    data = request.get_json(silent=True) or {}
    reference = str(data.get("reference", "")).strip()
    customer = str(data.get("client", "")).strip()

    try:
        amount = int(data.get("montant"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erreur": "montant invalide"}), 400

    if not reference or amount <= 0:
        return jsonify({
            "ok": False,
            "erreur": "reference et montant positif obligatoires"
        }), 400

    now = datetime.now(timezone.utc).isoformat()
    try:
        with db() as con:
            con.execute(
                """INSERT INTO payment_records
                (reference,customer,amount,currency,status,provider,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (reference[:150], customer[:150], amount, "XOF",
                 "pending", str(data.get("prestataire", ""))[:80], now, now)
            )
    except sqlite3.IntegrityError:
        return jsonify({
            "ok": False, "erreur": "Cette référence existe déjà"
        }), 409

    log_event("paiement", f"Référence de paiement enregistrée : {reference}", "info")
    return jsonify({
        "ok": True,
        "reference": reference,
        "statut": "pending",
        "message": "Enregistré pour suivi; aucun paiement réel n'a été exécuté."
    }), 201


@bamba_extra_bp.get("/extras/export/activites.csv")
@admin_required_extra
def extra_export_activities():
    with db() as con:
        rows = con.execute(
            "SELECT id,created_at,category,message,status "
            "FROM activity_log ORDER BY id DESC"
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "date_utc", "categorie", "message", "statut"])
    for row in rows:
        writer.writerow([row[k] for k in row.keys()])

    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition":
                 "attachment; filename=bamba_activites.csv"}
    )
