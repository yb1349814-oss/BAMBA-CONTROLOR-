from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")
marker = '@app.route("/health")'

if "def favicon_bamba():" in s:
    print("La route favicon existe déjà.")
elif marker not in s:
    print("Route health introuvable. Aucun changement.")
else:
    ajout = '''@app.route("/favicon.ico")
def favicon_bamba():
    return redirect(url_for("static", filename="icone_bamba.png"))


'''
    nouveau = s.replace(marker, ajout + marker, 1)
    compile(nouveau, "app.py", "exec")
    Path("app.py.sauvegarde_favicon").write_text(s, encoding="utf-8")
    p.write_text(nouveau, encoding="utf-8")
    print("Route favicon ajoutée. Sauvegarde créée.")
