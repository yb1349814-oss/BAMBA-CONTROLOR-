from PIL import Image, ImageDraw, ImageFont
import math

DOSSIER = "."

def police(taille, gras=False):
    chemins = [
        "/system/fonts/Roboto-Bold.ttf" if gras
        else "/system/fonts/Roboto-Regular.ttf",
        "/data/data/com.termux/files/usr/share/fonts/DejaVuSans-Bold.ttf"
        if gras else
        "/data/data/com.termux/files/usr/share/fonts/DejaVuSans.ttf"
    ]
    for chemin in chemins:
        try:
            return ImageFont.truetype(chemin, taille)
        except OSError:
            pass
    return ImageFont.load_default()

BLEU = (12, 25, 48)
TURQUOISE = (0, 220, 190)
OR = (255, 190, 75)
BLANC = (255, 255, 255)

def dessiner_logo(taille, chemin, horizontal=False):
    w, h = taille
    im = Image.new("RGB", (w, h), BLEU)
    d = ImageDraw.Draw(im)

    if horizontal:
        cx, cy = int(h * 0.5), int(h * 0.5)
        rayon = int(h * 0.34)
        d.ellipse((cx-rayon, cy-rayon, cx+rayon, cy+rayon),
                  fill=TURQUOISE)
        centre = (cx, cy)
        echelle = h / 300
        d.text((int(h*0.88), int(h*0.28)), "BAMBA",
               font=police(int(h*0.25), True), fill=BLANC)
        d.text((int(h*0.90), int(h*0.58)),
               "WI-FI  •  CONTROLOR",
               font=police(int(h*0.085)), fill=TURQUOISE)
    else:
        cx, cy = w//2, int(h*0.38)
        rayon = int(w*0.25)
        d.ellipse((cx-rayon, cy-rayon, cx+rayon, cy+rayon),
                  fill=TURQUOISE)
        centre = (cx, cy)
        d.text((w//2, int(h*0.69)), "BAMBA",
               font=police(int(w*0.15), True),
               fill=BLANC, anchor="mm")
        d.text((w//2, int(h*0.81)), "CONTROLOR",
               font=police(int(w*0.065), True),
               fill=OR, anchor="mm")

    cx, cy = centre
    epaisseur = max(3, int(min(w, h)*0.018))
    for r in (0.11, 0.19, 0.27):
        bbox = (cx-rayon*r*3, cy-rayon*r*3,
                cx+rayon*r*3, cy+rayon*r*3)
        d.arc(bbox, 225, 315, fill=BLEU, width=epaisseur)

    d.ellipse((cx-epaisseur, cy+rayon*0.12,
               cx+epaisseur, cy+rayon*0.12+epaisseur*2),
              fill=OR)

    im.save(chemin, "PNG")
    print("Créé :", chemin, "-", im.size)

dessiner_logo((1200, 360), "logo_bamba.png", horizontal=True)
dessiner_logo((600, 600), "icone_bamba.png")

print("LOGO BAMBA : TERMINÉ")
