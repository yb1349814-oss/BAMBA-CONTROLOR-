import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent / "bamba.db"
con = sqlite3.connect(db)

try:
    existe = con.execute(
        "SELECT 1 FROM plans_abonnement WHERE code = 'MAX'"
    ).fetchone()

    if not existe:
        raise RuntimeError(
            "Le forfait MAX est introuvable. Aucun changement effectué."
        )

    con.execute("""
        CREATE TABLE IF NOT EXISTS clients_plateforme (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            telephone TEXT,
            mot_de_passe_hash TEXT NOT NULL,
            plan_code TEXT NOT NULL DEFAULT 'MAX'
                REFERENCES plans_abonnement(code),
            debut_essai TEXT NOT NULL,
            fin_essai TEXT NOT NULL,
            statut TEXT NOT NULL DEFAULT 'essai',
            cree_le TEXT NOT NULL,
            email_verifie INTEGER NOT NULL DEFAULT 0
        )
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_clients_email
        ON clients_plateforme(email)
    """)

    con.commit()
    print("Table des comptes clients prête.")

    colonnes = con.execute(
        "PRAGMA table_info(clients_plateforme)"
    ).fetchall()

    print("Colonnes créées :")
    for colonne in colonnes:
        print("-", colonne[1])

    print("Aucun compte client créé pour le moment.")

except Exception:
    con.rollback()
    raise
finally:
    con.close()
