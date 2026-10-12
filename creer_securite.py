import os
import json
import secrets
import hashlib
import getpass

mot = getpass.getpass("Entre ton mot de passe : ")
confirmation = getpass.getpass("Confirme ton mot de passe : ")

if not mot or mot != confirmation:
    print("Erreur : les mots de passe ne correspondent pas.")
    raise SystemExit(1)

sel = secrets.token_bytes(16)
empreinte = hashlib.pbkdf2_hmac(
    "sha256", mot.encode(), sel, 300000
).hex()

config = {
    "salt": sel.hex(),
    "password_hash": empreinte,
    "secret_key": secrets.token_hex(32)
}

with open("auth_config.json", "w") as f:
    json.dump(config, f)

os.chmod("auth_config.json", 0o600)
print("Configuration sécurisée créée.")
