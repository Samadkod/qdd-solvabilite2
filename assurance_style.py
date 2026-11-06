"""Habillage assurance, sans modification du moteur original."""
from pathlib import Path
from html import escape
import streamlit as st
from style_app import CSS
from langue import t

def appliquer_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    habillage = Path(__file__).parent / "assets" / "design.css"
    st.markdown(f"<style>{habillage.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    if theme_sombre():
        sombre = Path(__file__).parent / "assets" / "design_sombre.css"
        st.markdown(f"<style>{sombre.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def theme_sombre() -> bool:
    """Thème choisi par l'utilisateur (menu ⋮ > Settings) ; clair si l'information n'est pas disponible."""
    try:
        return st.context.theme.type == "dark"
    except Exception:  # noqa: BLE001
        return False


def couleur_texte() -> str:
    """Couleur des étiquettes de graphiques, lisible sur le fond du thème."""
    return "#E3EAF0" if theme_sombre() else "#15202A"

def bandeau(campagne: str, date) -> None:
    st.markdown(
        f"""
<div class="qdd-hero">
  <div class="qdd-surtitre">{t("SOLVABILITÉ II / PILOTAGE DE LA QUALITÉ DES DONNÉES")}</div>
  <h1>{t("Pilotage de la qualité des données")}</h1>
  <p>{t("Campagne")} {escape(str(campagne))} · {t("Arrêté du")} {date:%d/%m/%Y}<br>
  {t("Identifier les écarts. Prioriser la revue. Documenter les contrôles.")}</p>
  <div class="qdd-badges">
    <span class="qdd-badge">{t("Environnement de démonstration · données fictives")}</span>
    <span class="qdd-badge">{t("Assurance dommages · BTP")}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

def entete_page(rubrique: str, titre: str, description: str, contexte: str) -> None:
    st.markdown(
        f"""
<div class="qdd-entete">
  <div class="qdd-surtitre">{escape(rubrique)} · {escape(contexte)}</div>
  <h1>{escape(titre)}</h1>
  <p>{escape(description)}</p>
</div>
""",
        unsafe_allow_html=True,
    )
