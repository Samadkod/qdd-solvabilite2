"""Habillage assurance, sans modification du moteur original."""
from pathlib import Path
from html import escape
import streamlit as st
from style_app import CSS

def appliquer_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    habillage = Path(__file__).parent / "assets" / "design.css"
    st.markdown(f"<style>{habillage.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

def bandeau(campagne: str, date) -> None:
    st.markdown(
        f"""
<div class="qdd-hero">
  <div class="qdd-surtitre">SOLVABILITÉ II / PILOTAGE DE LA QUALITÉ DES DONNÉES</div>
  <h1>Pilotage de la qualité des données</h1>
  <p>Campagne {escape(str(campagne))} · Arrêté du {date:%d/%m/%Y}<br>
  Identifier les écarts. Prioriser la revue. Documenter les contrôles.</p>
  <div class="qdd-badges">
    <span class="qdd-badge">Environnement de démonstration · données fictives</span>
    <span class="qdd-badge">Assurance dommages · BTP</span>
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
