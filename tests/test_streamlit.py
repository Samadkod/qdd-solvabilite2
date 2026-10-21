"""Application Streamlit : chaque page démarre sans erreur, et les pages expliquées citent les valeurs de référence."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
PAGES = ["synthese", "donnees", "controles", "anomalies", "lignes", "regles", "lignage", "comprendre", "guide", "sas", "atelier", "code"]


def ouvrir(page: str) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=300)
    at.session_state["page"] = page
    return at.run()


@pytest.fixture(scope="module")
def guide():
    return ouvrir("guide")


@pytest.mark.parametrize("page", PAGES)
def test_chaque_page_demarre_sans_erreur(page):
    at = ouvrir(page)
    assert not at.exception, page
    # le menu propose toutes les pages, la page ouverte est mise en avant
    menu = {b.key: b for b in at.sidebar.button}
    assert all(f"menu_{p}" in menu for p in PAGES)
    assert menu[f"menu_{page}"].proto.type == "primary"


def test_menu_change_de_page():
    at = ouvrir("synthese")
    at.sidebar.button(key="menu_anomalies").click().run()
    assert at.session_state["page"] == "anomalies" and not at.exception
    assert any("anomalie(s) affichée(s)" in c.value for c in at.caption)


def test_action_ouvre_les_controles_filtres():
    at = ouvrir("synthese")
    next(b for b in at.button if b.key and b.key.startswith("action_controles_Voir les contrôles en rouge")).click().run()
    assert at.session_state["page"] == "controles" and not at.exception
    assert any(c.value.startswith("4 point(s) de contrôle affiché(s)") for c in at.caption)


def test_sous_onglets_du_guide(guide):
    onglets = [t.label for t in guide.tabs]
    for sous in ("L'essentiel", "🔎 D'où sortent les chiffres", "Les chiffres", "Le poste", "L'assurance en clair",
                 "Se former", "Calendrier", "Glossaire"):
        assert sous in onglets


def test_guide_cite_les_valeurs_de_reference(guide):
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


def test_calendrier_suit_la_date_de_prise_de_poste(guide):
    texte = " ".join(i.value for i in guide.info)
    # clôture annuelle 31/12/2026 : QRT trimestriels à 5 semaines, annuels à 14 semaines
    assert "**31/12/2026**" in texte and "**04/02/2027**" in texte and "**08/04/2027**" in texte
