"""Fiche de l'assistant : son contenu suit le code de l'assistant."""
from __future__ import annotations

from pathlib import Path

import assistant_qdd as a
from fiche_assistant import contenu, nouveautes

RACINE = Path(__file__).resolve().parents[1]


def test_fiche_suit_le_code_de_l_assistant():
    c = contenu()
    assert c["modele"] == "Claude Opus 5.5" and a.MODELE == "claude-opus-5-5"
    assert c["budget"] == f"{a.BUDGET_VISITE:.2f} $".replace(".", ",")
    assert [n for n, _ in c["outils"]] == [a.NOMS_OUTILS[o["name"]] for o in a.OUTILS] and len(c["outils"]) == 15
    assert str(a.LIGNES_MAX) in c["fichiers"] and "PDF" in c["fichiers"]
    from assurance_feuille import tableau
    assert nouveautes(tableau()) == ["F40", "F39", "F35"]  # les trois dernières livraisons de l'assistant
    import fiche_assistant as f
    feuille = tableau().set_index("id")
    for chiffre in ("3 à 21 s", "0,02 à 0,10 $", "31 à 74 s", "0,14 à 0,27 $"):  # mesures reprises des évaluations
        assert chiffre in f.MESURES
    assert "3 à 21 s" in feuille.loc["F28", "pourquoi"] and "0,02 à 0,10 $" in feuille.loc["F28", "pourquoi"]
    assert "31 à 74 s" in feuille.loc["F27", "prerequis"] and "0,14 à 0,27 $" in feuille.loc["F27", "prerequis"]


def test_page_fiche_sans_cle(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(str(RACINE / "streamlit_app.py"), default_timeout=300)
    at.session_state["page"] = "fiche_assistant"
    at.run()
    assert not at.exception
    texte = " ".join(m.value for m in at.markdown)
    assert "Non activé sur cet environnement" in texte and "Claude Opus 5.5" in texte and "0,50 $ par visite" in texte
    at.button(key="fiche_ouvrir").click().run()
    assert at.session_state["page"] == "assistant"
