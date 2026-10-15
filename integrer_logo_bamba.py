from pathlib import Path
import re
import sys

f = Path("app.py")
code = f.read_text(encoding="utf-8")

nouvelle_fonction = r'''
def page(title, body, active='/', wide=False):
    navigation = [
        ("Tableau de bord", "/", "⌂"),
        ("Routeurs", "/routeurs", "⌁"),
        ("Sites", "/sites", "◈"),
        ("Abonnements", "/abonnements", "◷"),
        ("Utilisateurs", "/utilisateurs", "♙"),
        ("Tickets Wi-Fi", "/tickets", "▤"),
        ("Vouchers", "/vouchers", "◇"),
        ("Codes d'accès", "/codes", "⌘"),
        ("Importer des codes", "/importer", "⇧"),
        ("Vendeurs", "/vendeurs", "♧"),
        ("Revendeurs", "/revendeurs", "♧"),
        ("Paiements", "/paiements", "₣"),
        ("Opérations", "/operations", "⇄"),
        ("MikroTik", "/mikrotik", "⌁"),
        ("Roaming inter-sites", "/roaming", "⌘"),
        ("Statistiques", "/statistiques", "▥"),
        ("Paramètres", "/parametres", "⚙"),
    ]
    menu = "".join(
        '<a class="nav-item%s" href="%s"><span class="nav-icon">%s</span><span>%s</span></a>'
        % (' active' if active == url else '', url, icon, label)
        for label, url, icon in navigation
    )
    template = r"""
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#061326">
<title>{{ title }} — BAMBA CONTROLOR</title>
<style>
:root{color-scheme:dark;--bg:#06101f;--panel:#0b1b31;--line:#123d60;--cyan:#00e5ff;--blue:#168cff;--text:#eaf7ff;--muted:#8ba9c5}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(ellipse at 20% 0%,#0d2d4c 0,transparent 45%),var(--bg);color:var(--text);font-family:Inter,Arial,sans-serif}
.layout{display:flex;min-height:100vh}
.sidebar{width:255px;flex-shrink:0;background:rgba(4,14,29,.97);border-right:1px solid #123d60;padding:22px 14px;box-shadow:5px 0 35px #001b3544}
.brand{display:flex;align-items:center;gap:12px;padding:10px 8px 24px;border-bottom:1px solid #153752;margin-bottom:20px}
.brand-mark{width:52px;height:52px;flex-shrink:0;border:1px solid #00dfff;border-radius:15px;display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#102e4c,#061326);box-shadow:0 0 12px #00cfff88,inset 0 0 15px #008cff33}
.brand-mark svg{width:39px;height:39px;filter:drop-shadow(0 0 5px #00eaff)}
.brand-name{font-size:24px;font-weight:900;letter-spacing:2px;color:#f2fcff;text-shadow:0 0 9px #00bfff,0 0 20px #0077ff}
.brand-name span{color:#00e5ff}
.brand-sub{font-size:9px;letter-spacing:2.1px;color:#8fcfff;margin-top:4px}
.menu-label{font-size:10px;letter-spacing:2px;color:#6289aa;padding:10px 12px}
.nav-item{display:flex;align-items:center;gap:12px;padding:11px 12px;margin:3px 0;border:1px solid transparent;border-radius:9px;text-decoration:none;color:#aac2d9;font-size:13px;transition:.2s}
.nav-item:hover,.nav-item.active{color:#eafcff;background:linear-gradient(90deg,#063b5b,#0a2440);border-color:#087da8;box-shadow:inset 3px 0 #00e5ff,0 0 12px #008cff20}
.nav-icon{width:22px;text-align:center;font-size:18px;color:#00dfff}
.main{flex:1;min-width:0;padding:26px clamp(14px,3vw,34px)}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:15px;flex-wrap:wrap;border-bottom:1px solid #12304b;padding-bottom:20px;margin-bottom:25px}
.eyebrow{font-size:10px;letter-spacing:2px;color:#00dfff;text-transform:uppercase}
h1{font-size:clamp(23px,3vw,32px);margin:7px 0 0;color:#f0faff;text-shadow:0 0 14px #0077ff35}
.status{border:1px solid #087c8d;border-radius:30px;padding:8px 12px;color:#69f7ff;font-size:11px;background:#052331}
.status:before{content:"";display:inline-block;width:7px;height:7px;background:#00f0b5;border-radius:50%;margin-right:8px;box-shadow:0 0 8px #00f0b5}
.content{width:100%;max-width:{% if wide %}1500px{% else %}1100px{% endif %};margin:auto}
.content a{color:#55dfff}
.content input,.content select,.content textarea{max-width:100%;background:#07182a;color:#eaf7ff;border:1px solid #1b5277;border-radius:7px;padding:9px}
.content button,.content input[type=submit]{background:linear-gradient(100deg,#0878dc,#00aeca);color:white;border:1px solid #20cfff;border-radius:8px;padding:10px 15px;cursor:pointer;font-weight:700}
.content table{width:100%;border-collapse:collapse}
.content th,.content td{padding:10px;border-bottom:1px solid #153653;text-align:left}
.content th{color:#6feaff}
.content section,.content .card,.content article{border-color:#164768}
@media(max-width:760px){.layout{display:block}.sidebar{width:100%;padding:12px;border-right:0;border-bottom:1px solid #123d60}.brand{padding:5px 7px 13px;margin-bottom:10px}.brand-mark{width:44px;height:44px}.brand-name{font-size:21px}.menu-label{padding:6px}.sidebar nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px}.nav-item{font-size:11px;padding:9px 6px;gap:7px}.main{padding:18px 12px}.topbar{margin-bottom:18px}}
</style>
</head>
<body>
<div class="layout">
<aside class="sidebar">
  <div class="brand">
    <div class="brand-mark">
      <svg viewBox="0 0 48 48" fill="none" aria-label="Symbole Wi-Fi">
        <path d="M5 17C16 7 32 7 43 17" stroke="#00E5FF" stroke-width="3.5" stroke-linecap="round"/>
        <path d="M11 24C19 17 29 17 37 24" stroke="#00E5FF" stroke-width="3.5" stroke-linecap="round"/>
        <path d="M17 31C21 27.5 27 27.5 31 31" stroke="#39A9FF" stroke-width="3.5" stroke-linecap="round"/>
        <circle cx="24" cy="38" r="3.5" fill="#00F0FF"/>
      </svg>
    </div>
    <div><div class="brand-name">BAMBA<span>.</span></div><div class="brand-sub">CONTROLOR</div></div>
  </div>
  <div class="menu-label">MENU PRINCIPAL</div>
  <nav>""" + menu + r"""</nav>
</aside>
<main class="main">
  <header class="topbar">
    <div><div class="eyebrow">BAMBA CONTROLOR / ESPACE DE GESTION</div><h1>{{ title }}</h1></div>
    <div class="status">Interface locale active</div>
  </header>
  <div class="content">{{ body|safe }}</div>
</main>
</div>
</body>
</html>
"""
    return render_template_string(
        template, title=title, body=body, active=active, wide=wide
    )
'''

motif = r"(?ms)^def page\(title, body, active='/', wide=False\):.*?(?=^def count\()"
nouveau_code, n = re.subn(motif, nouvelle_fonction + "\n\n", code, count=1)

if n != 1:
    print("ERREUR : fonction page() introuvable. Aucun changement effectué.")
    sys.exit(1)

f.write_text(nouveau_code, encoding="utf-8")
print("Logo Wi-Fi BAMBA intégré au modèle de page.")
