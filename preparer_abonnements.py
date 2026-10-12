import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent / "bamba.db"
con = sqlite3.connect(db)

con.execute("""
CREATE TABLE IF NOT EXISTS plans_abonnement (
code TEXT PRIMARY KEY,
nom TEXT NOT NULL,
prix_mensuel INTEGER NOT NULL,
sites_max INTEGER NOT NULL,
vendeurs_max INTEGER NOT NULL,
routeurs_par_site_max INTEGER NOT NULL,
connexions_max INTEGER NOT NULL,
mobile_money INTEGER NOT NULL DEFAULT 0,
import_csv INTEGER NOT NULL DEFAULT 0,
reseau_b2b INTEGER NOT NULL DEFAULT 0,
roaming INTEGER NOT NULL DEFAULT 0,
vouchers_personnalises INTEGER NOT NULL DEFAULT 0,
mac_ip_avance INTEGER NOT NULL DEFAULT 0,
support_prioritaire INTEGER NOT NULL DEFAULT 0
)
""")

plans = [
("DECOUVERTE", "Découverte", 4000, 1, 3, 1, 100, 1, 0, 0, 0, 0, 0, 0),
("STARTER", "Starter", 8000, 3, 6, 2, 200, 1, 1, 0, 0, 0, 0, 0),
("PRO", "Pro", 15000, 6, 12, 5, 500, 1, 1, 1, 1, 1, 0, 0),
("BUSINESS", "Business", 25800, 15, 35, 10, 1200, 1, 1, 1, 1, 1, 1, 0),
("MAX", "Max", 40000, 30, 80, 15, 3000, 1, 1, 1, 1, 1, 1, 1)
]

con.executemany("""
INSERT OR IGNORE INTO plans_abonnement
(code, nom, prix_mensuel, sites_max, vendeurs_max,
routeurs_par_site_max, connexions_max, mobile_money,
import_csv, reseau_b2b, roaming, vouchers_personnalises,
mac_ip_avance, support_prioritaire)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", plans)

con.commit()
print("Tables d'abonnement préparées.")
print(con.execute("SELECT nom, prix_mensuel FROM plans_abonnement ORDER BY prix_mensuel").fetchall())
con.close()
