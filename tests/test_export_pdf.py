"""Export PDF de l'assistant : mise en page du Markdown déjà produit, police embarquée, aucun glyphe manquant."""
from __future__ import annotations

import logging
from datetime import datetime

from assistant_qdd import export_reponse
from export_pdf import POLICES, pdf_depuis_markdown

REPONSE = """**En bref :** deux données critiques sont hors tolérance (campagne N, 30/09/2026).

| Donnée | Note | Minimum | Statut |
|---|---|---|---|
| Provisions sinistres RC décennale | 97,02 % | 99,32 % | Bloquant |
| Date de survenance des sinistres | 96,71 % | 97,10 % | À corriger |

**Qui doit agir**
1. Direction sinistres : corriger → recontrôler, note ≥ minimum, écart − 0,39 point, « *à vérifier* » ✓.
   - sous-point : `donnees_critiques(campagne=N)` — fin…
"""


def test_pdf_genere_avec_police_embarquee_et_sans_glyphe_manquant(caplog):
    m = {"date": datetime(2026, 11, 26, 9, 31), "texte": REPONSE,
         "consultations": [{"appel": "donnees_critiques(campagne=N)", "nom": "Données et leur note",
                            "elements": 11}]}
    md = export_reponse(m, "Quelles données critiques sont hors tolérance ?")
    with caplog.at_level(logging.WARNING):
        pdf = pdf_depuis_markdown(md, "Données hors tolérance")
    assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    assert b"LiberationSans" in pdf  # police embarquée : accents et symboles identiques partout
    assert not [r for r in caplog.records if "glyph" in r.getMessage().lower()]
    assert (POLICES / "LICENCE_OFL.txt").exists()


def test_pdf_longue_conversation_sur_plusieurs_pages():
    md = "# Conversation\n\n" + "\n\n".join(f"## Vous · question {i}\n\nTexte de réponse numéro {i}. " * 3
                                            for i in range(60))
    pdf = pdf_depuis_markdown(md)
    assert pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ") + pdf.count(b"/Type /Page>") >= 1
    assert len(pdf) > 10_000
