import os, sqlite3, secrets, csv, io
from datetime import datetime, date
from flask import Flask, request, redirect, url_for, render_template_string, flash, send_file

app = Flask(__name__)
app.secret_key = os.environ.get('BAMBA_SECRET', secrets.token_hex(32))
DB = os.environ.get('BAMBA_DB', os.path.join(os.path.dirname(__file__), 'bamba_controlor.db'))

SCHEMA = {
 'sites': [('nom','Nom du site'),('ville','Ville / zone'),('statut','Statut')],
 'routeurs': [('nom','Nom du routeur'),('ip','Adresse IP'),('site','Site'),('modele','Modèle'),('statut','Statut')],
 'utilisateurs': [('nom','Nom complet'),('telephone','Téléphone'),('site','Site'),('statut','Statut')],
 'abonnements': [('client','Client'),('formule','Formule'),('prix','Prix FCFA'),('debut','Date de début'),('fin','Date de fin'),('statut','Statut')],
 'tickets': [('code','Code ticket'),('type','Durée / formule'),('prix','Prix FCFA'),('statut','Statut')],
 'vouchers': [('code','Code voucher'),('type','Durée / formule'),('prix','Prix FCFA'),('statut','Statut')],
 'codes': [('code','Code d’accès'),('source','Source / lot'),('statut','Statut')],
 'vendeurs': [('nom','Nom du vendeur'),('telephone','Téléphone'),('site','Site'),('commission','Commission %'),('statut','Statut')],
 'revendeurs': [('nom','Nom du revendeur'),('telephone','Téléphone'),('zone','Zone'),('solde','Solde FCFA'),('statut','Statut')],
 'paiements': [('reference','Référence'),('client','Client'),('montant','Montant FCFA'),('methode','Méthode'),('statut','Statut')],
 'operations': [('titre','Opération'),('details','Détails'),('montant','Montant FCFA'),('statut','Statut')],
 'roaming': [('nom','Nom / réseau partenaire'),('sites','Sites concernés'),('statut','Statut')],
 'mikrotik': [('nom','Nom du routeur'),('ip','Adresse IP'),('port','Port API'),('statut','Statut')],
}
LABELS = {
 'sites':'Sites','routeurs':'Routeurs','utilisateurs':'Utilisateurs','abonnements':'Abonnements','tickets':'Tickets Wi-Fi','vouchers':'Vouchers','codes':'Codes d’accès','vendeurs':'Vendeurs','revendeurs':'Revendeurs','paiements':'Paiements','operations':'Opérations','roaming':'Roaming inter-sites','mikrotik':'MikroTik','statistiques':'Statistiques','parametres':'Paramètres','importer':'Importer des codes'
}

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    for table, fields in SCHEMA.items():
        cols=', '.join('"%s" TEXT'%f[0] for f in fields)
        c.execute(f'CREATE TABLE IF NOT EXISTS "{table}" (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, {cols})')
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    if c.execute('SELECT COUNT(*) FROM sites').fetchone()[0] == 0:
        c.execute('INSERT INTO sites (created_at,nom,ville,statut) VALUES (?,?,?,?)',(datetime.now().isoformat(timespec='seconds'),'Abidjan Centre','Abidjan','En ligne'))
    c.commit(); c.close()
init_db()

CSS = r'''*{box-sizing:border-box} :root{--bg:#020a20;--panel:#06183b;--line:#087dff;--cyan:#00eaff;--blue:#087cff;--text:#eafaff;--muted:#83c9ff;--green:#00f5a0}body{margin:0;background:radial-gradient(ellipse at 65% 0%,#062b70 0,#020a20 48%,#010617 100%);color:var(--text);font-family:Arial,sans-serif;min-height:100vh}a{color:inherit;text-decoration:none}.layout{display:grid;grid-template-columns:270px 1fr;min-height:100vh}.side{background:linear-gradient(180deg,#031538,#01091e);border-right:1px solid #008cff;box-shadow:0 0 24px #006dff44;padding:18px 13px;position:sticky;top:0;height:100vh;overflow:auto}.brand{display:flex;align-items:center;gap:10px;padding:8px 4px 20px;border-bottom:1px solid #007dff88;margin-bottom:14px}.wifi{font-size:43px;color:var(--cyan);text-shadow:0 0 10px #00eaff,0 0 24px #008cff}.brand strong{font-size:23px;color:var(--cyan);text-shadow:0 0 12px #00bfff;letter-spacing:1px}.brand small{display:block;color:#d7faff;letter-spacing:3px}.navtitle{color:#4aafff;text-transform:uppercase;font-size:10px;letter-spacing:2px;padding:14px 9px 5px}.nav a{display:flex;gap:10px;align-items:center;padding:10px;border-radius:9px;margin:3px 0;color:#d9efff;font-size:13px;border:1px solid transparent}.nav a:hover,.nav a.active{background:linear-gradient(90deg,#007cff,#00b7ff);box-shadow:0 0 16px #008cff88;border-color:#49eaff;color:white}.ico{width:20px;text-align:center;color:var(--cyan);font-size:17px}.main{min-width:0}.top{height:76px;border-bottom:1px solid #007dff88;display:flex;align-items:center;justify-content:space-between;padding:0 24px;background:#041431bb;gap:12px}.search{max-width:560px;flex:1;border:1px solid #078bff;border-radius:12px;background:#041c45;padding:12px 16px;color:white}.topright{color:#b8eaff;font-size:13px}.content{padding:22px;max-width:1800px;margin:auto}.hero{border:1px solid #007cff;border-radius:15px;background:linear-gradient(110deg,#031438,#073a88 62%,#031432);padding:24px;display:flex;align-items:center;justify-content:space-between;gap:18px;box-shadow:inset 0 0 24px #007dff33,0 0 22px #007dff22;margin-bottom:18px}.hero h1{margin:0 0 8px;font-size:25px}.hero p{margin:0;color:#8eeeff}.heroBrand{font-size:30px;font-weight:900;color:var(--cyan);text-shadow:0 0 14px #00cfff}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin-bottom:18px}.stat,.panel{background:linear-gradient(145deg,#061b42ee,#03102c);border:1px solid #087dff;border-radius:13px;padding:17px;box-shadow:inset 0 0 16px #006dff19}.stat{position:relative;overflow:hidden}.stat:after{content:'';position:absolute;right:-22px;top:-22px;width:100px;height:100px;border-radius:50%;background:#008cff1b}.stat .label{color:#a8dfff;font-size:12px}.stat .num{font-size:28px;font-weight:800;margin:10px 0;color:white;text-shadow:0 0 12px #008cff}.stat .sub{color:var(--green);font-size:11px}.twocol{display:grid;grid-template-columns:1.35fr 1fr;gap:14px;margin-bottom:18px}.panel h2{font-size:16px;margin:0 0 15px}.chart{height:205px;width:100%;display:block}.legend{display:flex;gap:14px;color:#9fdcff;font-size:11px;flex-wrap:wrap;margin-top:8px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--cyan);margin-right:5px}.quick{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}.quick a,.btn{border:1px solid #00bfff;background:linear-gradient(100deg,#006bff,#00a9e9);border-radius:9px;padding:12px 8px;text-align:center;color:white;font-weight:bold;font-size:12px;box-shadow:0 0 12px #008cff44}.quick a:hover,.btn:hover{filter:brightness(1.2)}.lower{display:grid;grid-template-columns:1fr 1fr;gap:14px}.statusline,.rowitem{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid #124a82;font-size:12px;gap:8px}.pill{color:#00ffb1;background:#003e42;border:1px solid #00dca5;border-radius:20px;padding:4px 9px;font-size:10px}.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px}th,td{text-align:left;padding:12px 10px;border-bottom:1px solid #124a82;white-space:nowrap}th{color:#6edbff;font-weight:600;background:#06204a}td{color:#dff6ff}tr:hover td{background:#0a2b58}.formgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}label{display:block;color:#9fdcff;font-size:12px;margin-bottom:6px}input,select,textarea{width:100%;padding:12px;border-radius:8px;border:1px solid #126bc0;background:#020d25;color:white;margin-bottom:13px}button{cursor:pointer}.actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.danger{background:#651c38;border-color:#ff4f9a}.flash{background:#064e58;border:1px solid #00eaff;padding:10px 14px;border-radius:9px;margin-bottom:14px}.empty{color:#85b9dd;padding:18px 0}.footer{border-top:1px solid #087dff;margin-top:18px;padding:16px 0;color:#65bde9;font-size:11px;display:flex;justify-content:space-between}.tagline{color:#6ceeff;text-shadow:0 0 10px #00bfff}@media(max-width:1100px){.layout{grid-template-columns:220px 1fr}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.twocol{grid-template-columns:1fr}.quick{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:720px){.layout{grid-template-columns:1fr}.side{position:relative;height:auto;max-height:none}.nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.navtitle{grid-column:1/-1}.top{padding:12px;height:auto;flex-wrap:wrap}.content{padding:12px}.hero{padding:16px;align-items:flex-start;flex-direction:column}.heroBrand{font-size:23px}.grid{gap:8px}.stat{padding:12px}.stat .num{font-size:22px}.quick{grid-template-columns:repeat(2,minmax(0,1fr))}.lower{grid-template-columns:1fr}.formgrid{grid-template-columns:1fr}.footer{gap:8px;flex-wrap:wrap}}'''

NAV = [
 ('Tableau de bord','/','⌂'),('Gestion des connexions',None,'◉'),('Routeurs','/routeurs','▣'),('Sites','/sites','⌖'),('Abonnements','/abonnements','◷'),('Utilisateurs','/utilisateurs','♟'),('Vente Wi-Fi',None,'▱'),('Tickets','/tickets','▤'),('Vouchers','/vouchers','◇'),('Codes d’accès','/codes','⌑'),('Importation anciens codes','/importer','⇧'),('Gestion commerciale',None,'♧'),('Vendeurs','/vendeurs','♙'),('Revendeurs','/revendeurs','♧'),('Paiements','/paiements','＄'),('Opérations','/operations','◷'),('Fonctions avancées',None,'⚙'),('MikroTik','/mikrotik','⌁'),('Roaming inter-sites','/roaming','⇄'),('Statistiques','/statistiques','▥'),('Paramètres','/parametres','⚙')]


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


def count(table):
    c=db(); n=c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]; c.close(); return n

def money_total():
    c=db(); rows=c.execute("SELECT montant FROM paiements WHERE lower(statut) IN ('payé','paye','confirmé','confirme','reçu','recu')").fetchall(); c.close()
    return sum(float(r[0] or 0) for r in rows)

@app.route('/')
def home():
    c=db(); sales=c.execute('SELECT * FROM paiements ORDER BY id DESC LIMIT 5').fetchall(); users=c.execute('SELECT * FROM utilisateurs ORDER BY id DESC LIMIT 5').fetchall(); sites=c.execute('SELECT * FROM sites ORDER BY id DESC LIMIT 5').fetchall(); c.close()
    total=money_total()
    cards=[('Sites actifs',count('sites'),'sur les sites enregistrés'),('Routeurs',count('routeurs'),'routeurs configurés'),('Utilisateurs connectés',count('utilisateurs'),'utilisateurs enregistrés'),('Ventes du jour',f'{total:,.0f} FCFA'.replace(',',' '),'paiements confirmés')]
    stats=''.join(f'<div class="stat"><div class="label">◉　{a}</div><div class="num">{b}</div><div class="sub">↗ {d}</div></div>' for a,b,d in cards)
    chart='''<svg class="chart" viewBox="0 0 600 220" preserveAspectRatio="none"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00eaff" stop-opacity=".45"/><stop offset="1" stop-color="#007cff" stop-opacity="0"/></linearGradient></defs>'''
    for y in range(30,201,34): chart+=f'<line x1="45" y1="{y}" x2="590" y2="{y}" stroke="#164c84" stroke-width="1"/><text x="4" y="{y+4}" fill="#9bcfff" font-size="11">{(200-y)*2500:,.0f}</text>'
    points='50,175 120,158 190,139 260,145 330,112 400,95 470,100 540,65 585,48'
    chart+=f'<polygon points="{points} 585,200 50,200" fill="url(#g)"/><polyline points="{points}" fill="none" stroke="#00eaff" stroke-width="3" stroke-linejoin="round"/>'
    for x,label in zip([50,120,190,260,330,400,470,540,585],['06/10','07/10','08/10','09/10','10/10','11/10','12/10','13/10','14/10']): chart+=f'<text x="{x}" y="216" text-anchor="middle" fill="#a8dfff" font-size="10">{label}</text>'
    chart+='</svg>'
    sales_rows=''.join(f'<div class="rowitem"><span>{r["reference"] or "Paiement"}<br><small style="color:#76cfff">{r["client"] or "Client"}</small></span><b>{r["montant"] or "0"} FCFA</b><span class="pill">{r["statut"] or "En attente"}</span></div>' for r in sales) or '<div class="empty">Aucun paiement enregistré. Ajoutez un paiement pour commencer.</div>'
    site_rows=''.join(f'<div class="statusline"><span>⌖　{r["nom"]}</span><span>{r["ville"] or "—"}</span><span class="pill">{r["statut"] or "À configurer"}</span></div>' for r in sites) or '<div class="empty">Aucun site enregistré.</div>'
    user_rows=''.join(f'<div class="statusline"><span>♟　{r["nom"]}</span><span>{r["site"] or "—"}</span><span class="pill">{r["statut"] or "Actif"}</span></div>' for r in users) or '<div class="empty">Aucun utilisateur enregistré.</div>'
    body=f'''<div class="grid">{stats}</div><div class="twocol"><div class="panel"><h2>▥　Évolution des ventes</h2>{chart}<div class="legend"><span><i class="dot"></i>Ventes / paiements</span><span>Montants selon les données enregistrées</span></div></div><div class="panel"><h2>◉　Statut du réseau</h2><div class="statusline"><span>Internet</span><span class="pill">À vérifier sur le routeur</span></div><div class="statusline"><span>Routeurs enregistrés</span><b>{count('routeurs')}</b></div><div class="statusline"><span>Sites enregistrés</span><b>{count('sites')}</b></div><div class="statusline"><span>Utilisateurs</span><b>{count('utilisateurs')}</b></div><h2 style="margin-top:18px">⚡　Raccourcis rapides</h2><div class="quick"><a href="/vouchers">＋ Vendre voucher</a><a href="/vendeurs">＋ Vendeur</a><a href="/routeurs">＋ Routeur</a><a href="/importer">⇧ Importer codes</a><a href="/statistiques">▥ Statistiques</a></div></div></div><div class="lower"><div class="panel"><h2>◉　Derniers paiements <a style="float:right;color:#00eaff" href="/paiements">Voir tout →</a></h2>{sales_rows}</div><div class="panel"><h2>♟　Utilisateurs actifs <a style="float:right;color:#00eaff" href="/utilisateurs">Voir tout →</a></h2>{user_rows}</div><div class="panel"><h2>⌖　Réseau & Sites <a style="float:right;color:#00eaff" href="/sites">Voir tout →</a></h2>{site_rows}</div><div class="panel"><h2>⚙　Fonctions disponibles</h2>{''.join(f'<div class="statusline"><a href="{href}">{label}</a><span class="pill">Ouvrir</span></div>' for label,href in [('Gestion des routeurs','/routeurs'),('Abonnements','/abonnements'),('Tickets Wi-Fi','/tickets'),('Codes d’accès','/codes'),('MikroTik','/mikrotik'),('Roaming inter-sites','/roaming')])}</div></div>'''
    _bamba_neon_style = '<style>\n.grid{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:14px!important;margin:16px 0 20px!important}\n.stat,.panel{background:linear-gradient(145deg,#0b2340,#07162b)!important;border:1px solid #164b75!important;border-radius:15px!important;color:#e9f7ff!important;box-shadow:0 0 18px #00cfff12!important}\n.stat{padding:18px!important;overflow:hidden}\n.stat .label{color:#9ac9eb!important;font-size:12px!important}\n.stat .num{color:#fff!important;font-size:clamp(20px,2.5vw,29px)!important;font-weight:800!important;text-shadow:0 0 12px #00cfff35!important;overflow-wrap:anywhere}\n.stat .sub{color:#63c9f7!important;font-size:11px!important}\n.panel{padding:18px!important;margin-bottom:16px!important;min-width:0}\n.panel h2{color:#e5f8ff!important;font-size:16px!important;border-bottom:1px solid #153c5d;padding-bottom:10px}\n.twocol{display:grid!important;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)!important;gap:16px!important;margin-bottom:16px!important}\n.lower{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:16px!important}\n.chart{max-width:100%;height:auto;min-height:170px}\n.quick{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:9px!important}\n.quick a{display:block;padding:11px!important;border:1px solid #17486d!important;border-radius:10px!important;background:#081b31!important;color:#00eaff!important;text-decoration:none!important;font-size:12px}\n.panel a{color:#00eaff!important}\n.rowitem,.statusline{border-bottom:1px solid #14324f!important;padding:11px 0!important;color:#dff4ff!important;gap:10px}\n.pill{display:inline-block!important;border:1px solid #176185!important;border-radius:20px!important;padding:5px 8px!important;color:#8deaff!important;background:#06243b!important;font-size:10px!important}\n.empty{color:#80afd0!important;padding:15px 0!important}\n.bamba-neon-hero{display:flex;align-items:center;gap:14px;padding:20px;margin:0 0 18px;border:1px solid #087eaf;border-radius:18px;background:radial-gradient(ellipse at top right,#073e6b 0%,#071a32 52%,#061225 100%);box-shadow:0 0 25px #00bfff18;color:#fff}\n.bamba-neon-logo{width:58px;height:58px;flex-shrink:0;display:grid;place-items:center;border:1px solid #00eaff;border-radius:16px;background:#062747;box-shadow:0 0 18px #00cfff40}\n.bamba-neon-logo svg{width:43px;height:43px}\n.bamba-neon-title{font-size:24px;font-weight:900;letter-spacing:2px;text-shadow:0 0 14px #00cfff}\n.bamba-neon-title span{color:#00eaff}\n.bamba-neon-caption{margin-top:5px;color:#92c9ed;font-size:11px;letter-spacing:1px}\n@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))!important}.twocol,.lower{grid-template-columns:1fr!important}}\n@media(max-width:520px){.stat,.panel{padding:12px!important}.quick{grid-template-columns:1fr!important}.bamba-neon-title{font-size:18px;letter-spacing:1px}.bamba-neon-hero{padding:14px}.bamba-neon-logo{width:48px;height:48px}}\n</style>\n<div class="bamba-neon-hero"><div class="bamba-neon-logo"><svg viewBox="0 0 48 48" fill="none" aria-label="Wi-Fi BAMBA"><path d="M5 17C16 7 32 7 43 17M11 24C19 17 29 17 37 24M18 31C22 28 26 28 30 31" stroke="#00eaff" stroke-width="3.5" stroke-linecap="round"/><circle cx="24" cy="38" r="3" fill="#00eaff"/></svg></div><div><div class="bamba-neon-title">BAMBA <span>CONTROLOR</span></div><div class="bamba-neon-caption">TABLEAU DE BORD · GESTION DU RÉSEAU WI-FI</div></div></div>\n'
    body = _bamba_neon_style + body
    return page('Tableau de bord',body,'/')

@app.route('/<section>', methods=['GET','POST'])
def section(section):
    if section not in SCHEMA and section not in ('statistiques','parametres','importer','recherche'):
        return redirect('/')
    if section=='recherche':
        q=request.args.get('q','').strip(); results=[]; c=db()
        for table, fields in SCHEMA.items():
            try:
                clauses=' OR '.join(f'CAST("{f[0]}" AS TEXT) LIKE ?' for f in fields)
                rows=c.execute(f'SELECT * FROM "{table}" WHERE {clauses} LIMIT 8',tuple([f'%{q}%']*len(fields))).fetchall() if q else []
                results.extend((LABELS.get(table,table),dict(r)) for r in rows)
            except sqlite3.Error: pass
        c.close(); body='<div class="panel"><h2>Résultats de recherche</h2>'+''.join(f'<div class="statusline"><span>{t}: {r.get("nom") or r.get("code") or r.get("reference") or r.get("client") or "Élément"}</span><span>{r.get("statut", "")}</span></div>' for t,r in results) + ('<div class="empty">Aucun résultat trouvé.</div>' if not results else '')+'</div>'
        return page('Recherche',body)
    if section=='statistiques':
        body='<div class="grid">'+''.join(f'<div class="stat"><div class="label">{LABELS.get(t,t)}</div><div class="num">{count(t)}</div><div class="sub">enregistrés</div></div>' for t in ('sites','routeurs','utilisateurs','abonnements','tickets','vouchers','vendeurs','revendeurs'))+'</div><div class="panel"><h2>Chiffre des paiements confirmés</h2><div class="num" style="font-size:34px">'+f'{money_total():,.0f}'.replace(',',' ')+' FCFA</div><p class="tagline">Les chiffres affichés proviennent de la base de données locale.</p></div>'
        return page('Statistiques',body,'/statistiques')
    if section=='parametres':
        if request.method=='POST':
            c=db(); c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)',('nom_application',request.form.get('nom_application','BAMBA CONTROLOR'))); c.commit(); c.close(); flash('Paramètres enregistrés.'); return redirect('/parametres')
        c=db(); s=c.execute('SELECT value FROM settings WHERE key=?',('nom_application',)).fetchone(); c.close()
        body=f'<div class="panel"><h2>Paramètres de l’application</h2><form method="post"><label>Nom de l’application</label><input name="nom_application" value="{s[0] if s else "BAMBA CONTROLOR"}"><button class="btn">Enregistrer les paramètres</button></form><p style="color:#8bcfff">Base SQLite locale : {os.path.basename(DB)}. Configurez vos accès routeur séparément avant toute connexion réelle.</p></div>'
        return page('Paramètres',body,'/parametres')
    if section=='importer':
        if request.method=='POST':
            f=request.files.get('fichier')
            if not f or not f.filename.lower().endswith('.csv'): flash('Choisissez un fichier CSV valide.')
            else:
                try:
                    stream=io.StringIO(f.stream.read().decode('utf-8-sig'),newline=''); reader=csv.DictReader(stream); c=db(); n=0
                    for row in reader:
                        code=(row.get('code') or row.get('Code') or row.get('voucher') or row.get('ticket') or '').strip()
                        if code:
                            c.execute('INSERT INTO codes(created_at,code,source,statut) VALUES (?,?,?,?)',(datetime.now().isoformat(timespec='seconds'),code,f.filename,'Disponible')); n+=1
                    c.commit(); c.close(); flash(f'Import terminé : {n} code(s) importé(s).')
                except Exception as e: flash('Import impossible : vérifiez que le CSV est encodé en UTF-8 et contient une colonne code.')
            return redirect('/importer')
        body='''<div class="panel"><h2>⇧ Importer les anciens codes Wi-Fi</h2><p style="color:#9fdcff">Importez un fichier CSV UTF-8 contenant une colonne <b>code</b> (ou Code, voucher, ticket). Les codes seront ajoutés à la liste Codes d’accès.</p><form method="post" enctype="multipart/form-data"><label>Fichier CSV</label><input type="file" name="fichier" accept=".csv,text/csv" required><button class="btn">Importer les codes</button></form><a href="/codes" class="btn">Consulter les codes importés</a></div>'''
        return page('Importation anciens codes',body,'/importer')
    table=section; fields=SCHEMA[table]; label=LABELS.get(table,table.title())
    if request.method=='POST':
        c=db(); values=[request.form.get(f[0],'').strip() for f in fields]
        if request.form.get('action')=='delete':
            c.execute(f'DELETE FROM "{table}" WHERE id=?',(request.form.get('id'),)); flash('Élément supprimé.')
        else:
            cols=', '.join('"%s"'%f[0] for f in fields); marks=', '.join('?' for _ in fields)
            c.execute(f'INSERT INTO "{table}" (created_at,{cols}) VALUES (?,{marks})',[datetime.now().isoformat(timespec='seconds')]+values); flash(label+' : enregistrement ajouté.')
        c.commit(); c.close(); return redirect('/'+table)
    c=db(); rows=c.execute(f'SELECT * FROM "{table}" ORDER BY id DESC LIMIT 200').fetchall(); c.close()
    inputs=''.join(f'<div><label>{lab}</label><input name="{key}" placeholder="{lab}" {"required" if key in ("nom","code","reference","titre") else ""}></div>' for key,lab in fields)
    headers=''.join(f'<th>{lab}</th>' for _,lab in fields)
    rows_html=''
    for r in rows:
        cells=''.join(f'<td>{(r[k] or "—")}</td>' for k,_ in fields)
        rows_html+=f'<tr>{cells}<td><form method="post" onsubmit="return confirm(\'Supprimer cet élément ?\')"><input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{r["id"]}"><button class="btn danger" style="padding:6px 9px">Supprimer</button></form></td></tr>'
    body=f'''<div class="panel" style="margin-bottom:16px"><h2>＋ Ajouter : {label}</h2><form method="post"><div class="formgrid">{inputs}</div><button class="btn">Enregistrer</button></form></div><div class="panel"><h2>{label} enregistrés ({len(rows)})</h2><div class="tablewrap"><table><thead><tr>{headers}<th>Action</th></tr></thead><tbody>{rows_html}</tbody></table></div>{'<div class="empty">Aucun élément pour le moment. Utilisez le formulaire ci-dessus pour commencer.</div>' if not rows else ''}</div>'''
    return page(label,body,'/'+table)

@app.errorhandler(500)
def server_error(e):
    return page('Erreur', '<div class="panel"><h2>Une erreur est survenue</h2><p>Vérifiez les données saisies puis réessayez.</p><a class="btn" href="/">Retour au tableau de bord</a></div>'),500

if __name__=='__main__':
    print('\nBAMBA CONTROLOR est prêt : http://127.0.0.1:5000\nArrêt : CTRL+C\n')
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT','5000')), debug=False)
