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
    assert nouveautes(tableau()) == ["F35", "F28", "F27"]  # les trois dernières livraisons de l'assistant


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
