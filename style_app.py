"""Habillage de l'application : feuille de style et bandeau d'accueil.

Les couleurs reprennent celles de l'atelier HTML (app/template.html) et du thème
(.streamlit/config.toml). Les sélecteurs visent les attributs data-testid de Streamlit :
si une version future les renomme, l'application reste fonctionnelle, seul l'habillage se perd.
"""
from __future__ import annotations

import streamlit as st

CSS = """
<style>
:root{
  --qdd-accent:#0E5A69; --qdd-accent-fonce:#0A4350; --qdd-accent-doux:#DDEDF0;
  --qdd-encre:#15202A; --qdd-gris:#566370; --qdd-ligne:#D3DAE0; --qdd-surface:#FFFFFF;
  --qdd-or:#8E6210; --qdd-or-doux:#F6ECD8;
}
.block-container{max-width:1320px; padding-top:2.2rem; padding-bottom:4rem;}
header[data-testid="stHeader"]{background:transparent;}

/* bandeau d'accueil */
.qdd-hero{background:linear-gradient(120deg,var(--qdd-accent-fonce) 0%,var(--qdd-accent) 55%,#1F7A86 100%);
  color:#fff; border-radius:1.1rem; padding:1.6rem 1.9rem 1.4rem; margin-bottom:1.1rem;
  box-shadow:0 10px 30px -18px rgba(10,67,80,.8);}
.qdd-hero h1{font-family:Spectral,serif; font-weight:600; font-size:2.1rem; line-height:1.15; margin:0 0 .35rem;
  color:#fff; padding:0;}
.qdd-hero p{margin:0; opacity:.9; font-size:1.02rem; max-width:62rem;}
.qdd-badges{display:flex; flex-wrap:wrap; gap:.45rem; margin-top:.9rem;}
.qdd-badge{display:inline-block; font-size:.78rem; font-weight:600; letter-spacing:.01em; padding:.22rem .65rem;
  border-radius:999px; background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.28); color:#fff;}
.qdd-pistes{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:.75rem; margin:0 0 1.2rem;}
h5{font-family:Spectral,serif; color:var(--qdd-accent); margin-top:.6rem !important;}
.qdd-piste{background:var(--qdd-surface); border:1px solid var(--qdd-ligne); border-radius:.9rem; padding:.85rem 1rem;}
.qdd-piste b{display:block; font-family:Spectral,serif; font-size:1.08rem; color:var(--qdd-accent); margin-bottom:.15rem;}
.qdd-piste span{color:var(--qdd-gris); font-size:.9rem;}

/* onglets */
.stTabs [data-baseweb="tab-list"]{gap:.25rem; border-bottom:1px solid var(--qdd-ligne);}
.stTabs [data-baseweb="tab"]{font-weight:600; padding:.55rem .9rem; border-radius:.6rem .6rem 0 0;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{background:var(--qdd-surface);}

/* compteurs en cartes */
[data-testid="stMetric"]{background:var(--qdd-surface); border:1px solid var(--qdd-ligne); border-radius:.9rem;
  padding:.8rem 1rem .7rem; box-shadow:0 1px 2px rgba(21,32,42,.04);}
[data-testid="stMetricLabel"]{color:var(--qdd-gris); min-height:2.4em;}
[data-testid="stMetricLabel"] *{white-space:normal !important; overflow:visible !important; text-overflow:clip !important;
  word-break:normal !important; overflow-wrap:normal !important;
  line-height:1.2;}
[data-testid="stMetricValue"]{font-family:Spectral,serif; font-weight:600; color:var(--qdd-encre); font-size:1.65rem;}
[data-testid="stMetricValue"] *{overflow:visible !important; text-overflow:clip !important;}

/* cadres (st.container(border=True)) et volets dépliables */
[data-testid="stVerticalBlockBorderWrapper"]{background:var(--qdd-surface);}
[data-testid="stExpander"] details{background:var(--qdd-surface); border-radius:.8rem;}
[data-testid="stExpander"] summary{font-weight:600;}

/* étiquettes des exercices */
.qdd-etiquettes{display:flex; flex-wrap:wrap; gap:.4rem; margin:.1rem 0 .4rem;}
.qdd-tag{font-size:.75rem; font-weight:600; padding:.15rem .55rem; border-radius:999px;
  background:var(--qdd-accent-doux); color:var(--qdd-accent);}
.qdd-tag.or{background:var(--qdd-or-doux); color:var(--qdd-or);}
.qdd-tag.gris{background:#E3E7EB; color:var(--qdd-gris);}

/* barre latérale */
section[data-testid="stSidebar"] h2{font-family:Spectral,serif;}
</style>
"""


def appliquer_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def bandeau() -> None:
    st.markdown(
        """
<div class="qdd-hero">
  <h1>Atelier QDD Solvabilité 2</h1>
  <p>Mesurer, expliquer et améliorer la qualité des données qui alimentent le SCR et les états réglementaires,
  sur un assureur dommages BTP entièrement fictif.</p>
  <div class="qdd-badges">
    <span class="qdd-badge">Données 100 % fictives</span>
    <span class="qdd-badge">Méthode C. Motard (ISFA / Grant Thornton, 2024), corrigée</span>
    <span class="qdd-badge">Python · SAS · SQL · Qlik Sense</span>
  </div>
</div>
<div class="qdd-pistes">
  <div class="qdd-piste"><b>🧭 Comprendre</b><span>Guide terre à terre : le métier, les chiffres et le poste, sans jargon.</span></div>
  <div class="qdd-piste"><b>🧪 Pratiquer</b><span>SAS pratique : 13 exercices progressifs, corrigés, avec le résultat attendu.</span></div>
  <div class="qdd-piste"><b>⚙️ Analyser</b><span>Campagne live : le calcul tourne en direct, paramètres à gauche.</span></div>
</div>
""",
        unsafe_allow_html=True,
    )


def etiquettes(*items: tuple[str, str]) -> None:
    """items : (texte, classe) avec classe parmi '', 'or', 'gris'."""
    html = "".join(f'<span class="qdd-tag {cls}">{txt}</span>' for txt, cls in items)
    st.markdown(f'<div class="qdd-etiquettes">{html}</div>', unsafe_allow_html=True)
