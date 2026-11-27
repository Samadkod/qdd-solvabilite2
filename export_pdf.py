"""Export PDF des réponses et conversations de l'assistant, à partir du Markdown déjà produit.

Le Markdown reste la source (export_markdown, export_reponse) : le PDF n'en est qu'une mise en page.
Rendu : titres, paragraphes, gras et italique, listes à puces et numérotées, tableaux, filets.
Police embarquée : Liberation Sans (licence SIL OFL, assets/polices/) pour les accents et symboles.
"""
from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

POLICES = Path(__file__).parent / "assets" / "polices"
MARINE, ENCRE, GRIS, LIGNE, FOND_TETE = (15, 39, 64), (20, 32, 46), (90, 104, 120), (217, 222, 229), (238, 242, 247)
# Glyphes absents de Liberation Sans : remplacés plutôt que d'imprimer un carré vide.
REMPLACEMENTS = {"✓": "•", "✔": "•", "✗": "×", "✘": "×"}

_TABLE = re.compile(r"^\s*\|.*\|\s*$")
_SEPARATEUR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_LISTE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")


def _en_ligne(texte: str) -> str:
    """Markdown en ligne → balisage de fpdf2 (**gras**, __italique__) ; le code en ligne devient du texte."""
    for a, b in REMPLACEMENTS.items():
        texte = texte.replace(a, b)
    texte = texte.replace("__", "_ _").replace("--", "–")  # neutralise les marqueurs propres à fpdf2
    texte = re.sub(r"`([^`]*)`", r"\1", texte)
    texte = re.sub(r"(?<![*\w])\*(?!\s)([^*]+?)(?<!\s)\*(?![*\w])", r"__\1__", texte)  # *italique*
    texte = re.sub(r"(?<!\w)_(?!\s)([^_]+?)(?<!\s)_(?!\w)", r"__\1__", texte)          # _italique_
    return texte


def _cellules(ligne: str) -> list[str]:
    return [c.strip() for c in ligne.strip().strip("|").split("|")]


ENTETE = "ATELIER QDD · ASSISTANT QDD"
PIED = "Données 100 % fictives · réponse générée par l'assistant à partir du moteur de l'application"


class _Pdf(FPDF):
    def __init__(self, titre: str, entete: str = ENTETE, pied: str = PIED):
        super().__init__(format="A4")
        self.titre_doc, self.entete, self.pied = titre, entete, pied
        for style, fichier in (("", "Regular"), ("B", "Bold"), ("I", "Italic"), ("BI", "BoldItalic")):
            self.add_font("Liberation", style, POLICES / f"LiberationSans-{fichier}.ttf")
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(True, 18)
        self.set_title(titre)
        self.set_creator("Atelier QDD · Assistant QDD")

    def header(self):
        self.set_font("Liberation", "B", 8)
        self.set_text_color(*MARINE)
        self.cell(0, 5, self.entete, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*MARINE)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(5)

    def footer(self):
        self.set_y(-12)
        self.set_font("Liberation", "", 7.5)
        self.set_text_color(*GRIS)
        self.cell(0, 5, self.pied, align="L")
        self.set_x(self.l_margin)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="R")


def pdf_depuis_markdown(md: str, titre: str = "Assistant QDD", entete: str = ENTETE, pied: str = PIED) -> bytes:
    """Met en page le Markdown d'un export (assistant, dossier de comité) ; renvoie les octets du PDF."""
    pdf = _Pdf(titre, entete, pied)
    pdf.alias_nb_pages()
    pdf.add_page()
    largeur = pdf.w - pdf.l_margin - pdf.r_margin
    lignes = md.splitlines()
    paragraphe: list[str] = []

    def texte(t: str, taille: float = 10, style: str = "", couleur=ENCRE, apres: float = 2.2, retrait: float = 0):
        pdf.set_font("Liberation", style, taille)
        pdf.set_text_color(*couleur)
        pdf.set_x(pdf.l_margin + retrait)
        pdf.multi_cell(largeur - retrait, taille * 0.5, _en_ligne(t), markdown=True, align="L",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(apres)

    def vider():
        if paragraphe:
            texte(" ".join(s.strip() for s in paragraphe))
            paragraphe.clear()

    i = 0
    while i < len(lignes):
        ligne = lignes[i]
        brut = ligne.strip()
        if _TABLE.match(ligne) and i + 1 < len(lignes) and _SEPARATEUR.match(lignes[i + 1]):
            vider()
            tete, corps = _cellules(ligne), []
            i += 2
            while i < len(lignes) and _TABLE.match(lignes[i]):
                c = _cellules(lignes[i])
                corps.append((c + [""] * len(tete))[:len(tete)])
                i += 1
            pdf.set_font("Liberation", "", 8.5)
            pdf.set_text_color(*ENCRE)
            pdf.set_draw_color(*LIGNE)
            pdf.set_line_width(0.2)
            with pdf.table(width=largeur, align="LEFT", text_align="LEFT", markdown=True, line_height=4.4,
                           padding=1.4, headings_style=FontFace(emphasis="BOLD", color=MARINE, fill_color=FOND_TETE),
                           ) as tableau:
                for rang in [tete] + corps:
                    r = tableau.row()
                    for cellule in rang:
                        r.cell(_en_ligne(cellule))
            pdf.ln(3)
            continue
        if not brut:
            vider()
        elif re.fullmatch(r"-{3,}|\*{3,}|_{3,}", brut):
            vider()
            pdf.set_draw_color(*LIGNE)
            pdf.set_line_width(0.3)
            pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
            pdf.ln(4)
        elif m := re.match(r"^(#{1,6})\s+(.*)$", brut):
            vider()
            niveau = len(m.group(1))
            taille = {1: 16, 2: 13, 3: 11.5}.get(niveau, 10.5)
            pdf.ln(1.5 if niveau > 1 else 0)
            texte(m.group(2).replace("**", ""), taille, "B", MARINE if niveau <= 2 else ENCRE, 2.5)
        elif m := _LISTE.match(ligne):
            vider()
            retrait = 4 + 5 * (len(m.group(1).expandtabs(4)) // 2)
            puce = "•" if m.group(2) in "-*+" else m.group(2)
            pdf.set_font("Liberation", "", 10)
            pdf.set_text_color(*GRIS if puce == "•" else ENCRE)
            pdf.set_x(pdf.l_margin + retrait - 4)
            y = pdf.get_y()
            pdf.cell(4, 5, puce)
            pdf.set_y(y)
            texte(m.group(3), apres=1.2, retrait=retrait + (1 if puce == "•" else 2))
        elif re.fullmatch(r"\*[^*].*[^*]\*", brut):  # ligne de méta en italique sous le titre
            vider()
            texte(brut, 8.5, "", GRIS, 3)
        else:
            paragraphe.append(ligne)
        i += 1
    vider()
    return bytes(pdf.output())
