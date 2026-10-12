import sys
import json
import subprocess

def scanner_wifi():
    print("\nRecherche des réseaux Wi-Fi...")
    try:
        resultat = subprocess.run(
            ["termux-wifi-scaninfo"],
            capture_output=True,
            text=True,
            timeout=20
        )
        if resultat.returncode != 0:
            print("Erreur lors du scan Wi-Fi.")
            print(resultat.stderr)
            return
        reseaux = json.loads(resultat.stdout)
        if not reseaux:
            print("Aucun réseau détecté.")
            return
        print("\n===== RÉSEAUX WI-FI DÉTECTÉS =====")
        for i, reseau in enumerate(reseaux, 1):
            nom = reseau.get("ssid") or "(réseau masqué)"
            signal = reseau.get("rssi", "inconnu")
            frequence = reseau.get("frequency_mhz", "inconnue")
            print(f"\n{i}. {nom}")
            print(f"   Signal : {signal} dBm")
            print(f"   Fréquence : {frequence} MHz")
    except Exception as erreur:
        print(f"Erreur : {erreur}")

def verifier_connexion():
    print("\nVérification de la connexion Wi-Fi...")
    try:
        resultat = subprocess.run(
            ["termux-wifi-connectioninfo"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if resultat.returncode != 0:
            print("Impossible de lire les informations Wi-Fi.")
            print(resultat.stderr)
            return
        infos = json.loads(resultat.stdout)
        print("Réseau connecté :", infos.get("ssid", "inconnu"))
        print("Adresse IP :", infos.get("ip", "inconnue"))
    except Exception as erreur:
        print(f"Erreur : {erreur}")

def menu_principal():
    while True:
        print("\n===== BAMBA CONTROLLOR =====")
        print("1. Scanner les réseaux Wi-Fi")
        print("2. Vérifier l'état du Wi-Fi")
        print("3. Quitter")
        choix = input("Choisis une option (1, 2 ou 3) : ").strip()
        if choix == "1":
            scanner_wifi()
        elif choix == "2":
            verifier_connexion()
        elif choix == "3":
            print("Fermeture de BAMBA CONTROLLOR. À bientôt !")
            sys.exit()
        else:
            print("Option invalide. Réessaie.")

if __name__ == "__main__":
    menu_principal()
