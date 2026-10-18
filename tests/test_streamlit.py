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
    onglets = [t.label for t in app.tabs]
    principaux = ["🧭 Guide terre à terre", "🧪 SAS pratique", "📚 Atelier (révision)", "⚙️ Campagne live",
                  "🗂️ Gouvernance", "🧾 Code SAS / SQL"]
    assert [o for o in onglets if o in principaux] == principaux
    for sous in ("L'essentiel", "Les chiffres", "Le poste", "L'assurance en clair", "Se former", "Calendrier",
                 "Glossaire"):
        assert sous in onglets


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


def test_calendrier_suit_la_date_de_prise_de_poste(app):
    texte = " ".join(i.value for i in app.tabs[0].info)
    # clôture annuelle 31/12/2026 : QRT trimestriels à 5 semaines, annuels à 14 semaines
    assert "**31/12/2026**" in texte and "**04/02/2027**" in texte and "**08/04/2027**" in texte
