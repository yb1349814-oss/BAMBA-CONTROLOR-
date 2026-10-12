import sqlite3
import os
import hashlib
import secrets
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone

DB = Path(os.environ.get("BAMBA_DB_PATH", str(Path(__file__).resolve().parent / "bamba.db")))


def hacher_mot_de_passe(mot_de_passe):
    sel = secrets.token_hex(16)
    iterations = 600000
    empreinte = hashlib.pbkdf2_hmac(
        "sha256",
        mot_de_passe.encode("utf-8"),
        sel.encode("utf-8"),
        iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${sel}${empreinte}"


def verifier_mot_de_passe(mot_de_passe, valeur_stockee):
    try:
        algorithme, iterations, sel, empreinte = valeur_stockee.split("$")
        if algorithme != "pbkdf2_sha256":
            return False

        resultat = hashlib.pbkdf2_hmac(
            "sha256",
            mot_de_passe.encode("utf-8"),
            sel.encode("utf-8"),
            int(iterations)
        ).hex()

        return secrets.compare_digest(resultat, empreinte)
    except (ValueError, TypeError):
        return False


def creer_compte_client(nom, email, mot_de_passe, telephone=None):
    nom = nom.strip()
    email = email.strip().lower()

    if not nom:
        raise ValueError("Le nom est obligatoire.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Adresse e-mail invalide.")

    if len(mot_de_passe) < 10:
        raise ValueError("Le mot de passe doit contenir au moins 10 caractères.")

    maintenant = datetime.now(timezone.utc)
    debut = maintenant.isoformat(timespec="seconds")
    fin = (maintenant + timedelta(days=30)).isoformat(timespec="seconds")
    cree_le = debut
    mot_de_passe_hash = hacher_mot_de_passe(mot_de_passe)

    con = sqlite3.connect(DB)
    try:
        max_existe = con.execute(
            "SELECT 1 FROM plans_abonnement WHERE code = 'MAX'"
        ).fetchone()

        if not max_existe:
            raise RuntimeError("Le forfait MAX n'existe pas.")

        curseur = con.execute("""
            INSERT INTO clients_plateforme
            (nom, email, telephone, mot_de_passe_hash, plan_code,
             debut_essai, fin_essai, statut, cree_le)
            VALUES (?, ?, ?, ?, 'MAX', ?, ?, 'essai', ?)
        """, (
            nom, email, telephone, mot_de_passe_hash,
            debut, fin, cree_le
        ))

        con.commit()
        return curseur.lastrowid

    except sqlite3.IntegrityError as erreur:
        con.rollback()
        if "email" in str(erreur).lower():
            raise ValueError("Cette adresse e-mail possède déjà un compte.") from erreur
        raise
    finally:
        con.close()


if __name__ == "__main__":
    print("Module de comptes clients prêt.")
    print("Essai gratuit : 30 jours, forfait MAX.")
    print("Aucun compte créé pendant ce test.")
