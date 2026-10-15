
import re

def installer_theme_bamba(app):
    css = """
<style id="bamba-neon-theme">
:root {
  color-scheme: dark;
  --bamba-bg: #061225;
  --bamba-panel: #0b1d35;
  --bamba-cyan: #00eaff;
  --bamba-blue: #168bff;
  --bamba-text: #eaf8ff;
}
html { background: var(--bamba-bg); }
body {
  background: radial-gradient(ellipse at top, #102d50 0%, #061225 62%, #030914 100%) !important;
  color: var(--bamba-text) !important;
  font-family: system-ui, sans-serif !important;
}
h1, h2, h3 {
  color: var(--bamba-cyan) !important;
  text-shadow: 0 0 14px #00bfff55;
}
a { color: var(--bamba-cyan) !important; }
button, input[type=submit], .btn, a.button {
  border: 1px solid var(--bamba-cyan) !important;
  border-radius: 10px !important;
  background: linear-gradient(110deg, #0755a8, #087dba) !important;
  color: white !important;
  box-shadow: 0 0 12px #00cfff30;
}
input, select, textarea {
  background: #07182b !important;
  color: white !important;
  border: 1px solid #2375a8 !important;
  border-radius: 8px !important;
}
table, section, article, .card, .panel, .container, .dashboard-card {
  border-color: #164b70;
}
.card, .panel, .dashboard-card {
  background: #0b1d35 !important;
  border: 1px solid #145b83 !important;
  border-radius: 14px !important;
  box-shadow: 0 0 18px #00bfff12;
}
.bamba-neon-brand {
  margin: 0 0 18px;
  padding: 15px 18px;
  border-bottom: 1px solid #00dfff66;
  background: linear-gradient(90deg, #061225, #0a2a4a, #061225);
  color: #fff;
  font-size: 21px;
  font-weight: 800;
  letter-spacing: 2px;
  text-shadow: 0 0 12px #00dfff;
}
.bamba-neon-brand .wifi {
  color: #00eaff;
  margin-right: 9px;
  text-shadow: 0 0 14px #00eaff;
}
.bamba-neon-brand small {
  display: block;
  font-size: 10px;
  letter-spacing: 4px;
  color: #7eefff;
}
</style>
"""

    @app.after_request
    def bamba_neon_response(response):
        if "text/html" not in (response.content_type or ""):
            return response
        try:
            html = response.get_data(as_text=True)
            if 'id="bamba-neon-theme"' in html:
                return response
            if re.search(r"</head\s*>", html, re.I):
                html = re.sub(r"</head\s*>", css + "</head>", html,
                              count=1, flags=re.I)
            else:
                html = css + html

            marque = (
                '<div class="bamba-neon-brand">'
                '<span class="wifi">◉〰</span>BAMBA'
                '<small>CONTROLOR</small></div>'
            )
            if not re.search(r'class=["\'][^"\']*bamba-neon-brand', html):
                html = re.sub(r"(<body\b[^>]*>)",
                              r"\1" + marque, html, count=1, flags=re.I)
            response.set_data(html)
        except Exception:
            app.logger.exception("Theme BAMBA : erreur d'affichage")
        return response
