"""Inventaire des tâches manuelles de l'équipe (prise de poste) : un gabarit vide, à remplir avec l'équipe.

Répond à « qu'est-ce qui vous prend du temps chaque trimestre ? » : pour chaque tâche, sa fréquence, le temps passé,
ce qui est automatisable et la fonction de l'application qui la couvre déjà ; le temps annuel et le temps
récupérable sont calculés. Aucune donnée n'est inventée ni conservée : le tableau part vide et se télécharge.
"""
from __future__ import annotations

import pandas as pd

FREQUENCES = {"Quotidienne": 250, "Hebdomadaire": 52, "Mensuelle": 12, "Trimestrielle": 4, "Semestrielle": 2,
              "Annuelle": 1, "Ponctuelle": 1}
AUTOMATISABLE = {"Oui": 1.0, "En partie": 0.5, "Non": 0.0}
# Fonctions de l'application qui automatisent tout ou partie d'une tâche, et la page où les voir.
FONCTIONS = {
    "Contrôles automatisés (20 règles SQL / SAS)": "regles",
    "Note QDD et statuts calculés": "synthese",
    "Lignes en anomalie, message en clair": "lignes",
    "Registre des anomalies (cycle de vie)": "anomalies",
    "Relances par responsable": "relances",
    "Dossier de comité (PDF)": "dossier",
    "Dossier de preuves (ZIP, SHA-256)": "dossier",
    "Gain de note avant correction": "donnees",
    "Contrôles de chargement (niveau 0)": "chargement",
    "Lignage et dictionnaire": "lignage",
    "Avis QDD sur un projet informatique": "projet",
    "Assistant (questions, diagnostic)": "assistant",
    "Aucune pour l'instant": "",
}
COLONNES = ["Tâche", "Qui la fait", "Fréquence", "Heures par occurrence", "Outil utilisé", "Automatisable",
            "Fonction de l'application", "Commentaire"]


def gabarit() -> pd.DataFrame:
    """Le tableau vide, avec les bons types de colonnes."""
    return pd.DataFrame({c: pd.Series(dtype="float" if c == "Heures par occurrence" else "object") for c in COLONNES})


def calculer(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les heures par an et les heures récupérables (part automatisable : oui = tout, en partie = moitié)."""
    d = df.dropna(subset=["Tâche"]).copy()
    d = d[d["Tâche"].astype(str).str.strip() != ""]
    occ = d["Fréquence"].map(FREQUENCES).fillna(0)
    h = pd.to_numeric(d["Heures par occurrence"], errors="coerce").fillna(0)
    d["Heures par an"] = (occ * h).round(1)
    d["Heures récupérables par an"] = (d["Heures par an"] * d["Automatisable"].map(AUTOMATISABLE).fillna(0)).round(1)
    return d


def afficher() -> None:
    import streamlit as st

    st.markdown("#### :material/checklist: Inventaire des tâches de l'équipe")
    st.markdown("À remplir **avec l'équipe**, à la prise de poste : chaque tâche faite à la main, sa fréquence, le "
                "temps passé, et ce qui peut être automatisé. Le temps par an et le temps récupérable se calculent "
                "tout seuls.")
    st.caption("Le tableau part vide : aucune donnée n'est inventée, et rien n'est conservé par l'application. "
               "Téléchargez-le avant de quitter la page ; les données réelles restent en interne.")
    saisie = st.data_editor(gabarit(), num_rows="dynamic", width="stretch", key="inventaire_taches",
                            column_config={
                                "Fréquence": st.column_config.SelectboxColumn(options=list(FREQUENCES)),
                                "Heures par occurrence": st.column_config.NumberColumn(min_value=0.0, step=0.5),
                                "Automatisable": st.column_config.SelectboxColumn(options=list(AUTOMATISABLE)),
                                "Fonction de l'application": st.column_config.SelectboxColumn(options=list(FONCTIONS)),
                            })
    res = calculer(saisie)
    a, b, c = st.columns(3)
    a.metric("Tâches", len(res), border=True)
    b.metric("Heures par an", f"{res['Heures par an'].sum():.0f}".replace(".", ","), border=True)
    c.metric("Heures récupérables par an", f"{res['Heures récupérables par an'].sum():.0f}", border=True,
             help="Automatisable « Oui » : tout le temps ; « En partie » : la moitié ; « Non » : rien. Estimation à "
                  "affiner avec l'équipe.")
    if len(res):
        st.dataframe(res.sort_values("Heures récupérables par an", ascending=False), hide_index=True,
                     width="stretch")
    st.download_button("Télécharger l'inventaire (CSV)", res.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="inventaire_taches_equipe.csv", mime="text/csv", icon=":material/download:",
                       key="inventaire_csv", disabled=not len(res))
