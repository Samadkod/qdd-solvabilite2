"""Application Streamlit : démarrage sans erreur et guide « terre à terre » alimenté par la campagne N."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


@pytest.fixture(scope="module")
def app():
    return AppTest.from_file(str(APP), default_timeout=300).run()


def test_application_demarre_sans_erreur(app):
    assert not app.exception
    assert [t.label for t in app.tabs] == ["🧭 Guide terre à terre", "📚 Atelier (révision)", "⚙️ Campagne live",
                                          "🗂️ Gouvernance", "🧾 Code SAS / SQL"]


def test_guide_cite_les_valeurs_de_reference(app):
    guide = app.tabs[0]
    texte = " ".join(m.value for m in guide.markdown)
    # valeurs de référence de la campagne N (CLAUDE.md), reprises en direct du moteur
    assert "La note globale est de 97,45 % pour un objectif de 97,10 %" in texte
    assert "2 donnée(s) critique(s) sur 8" in " ".join(w.value for w in guide.warning)
    assert "10 vérification(s) conforme(s) sur 11" in texte
    assert "14 anomalie(s) ouverte(s)" in texte and "4 grave(s)" in texte
    assert "Provisions sinistres RC décennale" in texte and "Date de survenance des sinistres" in texte
    assert "Contrôles en cause : « Survenance avant date d'effet »" in texte
    for flux in ("F04", "F05", "F06", "F09", "F13"):
        assert f"**{flux}**" in texte
