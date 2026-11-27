"""Constats de l'ACPR : ce qu'elle relève le plus souvent sur la qualité des données, sources à l'appui, face à ce que
l'application couvre et à ce qui reste à faire en entreprise.

Sources (publiques, lues en entier ; citations vérifiées mot pour mot) : communiqué de presse du 11/01/2021,
enquêtes déclaratives 2022 (Analyses et synthèses n°144) et 2024 (n°167), notice « Exigences en matière de qualité
des données » du 08/11/2023 (points cités). Les enquêtes reposent sur les déclarations des organismes ; le
communiqué de 2021 cite aussi des contrôles sur place. Le référentiel est dans referentiels/constats_acpr.csv.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

FICHIER = Path(__file__).parent / "referentiels" / "constats_acpr.csv"
COUVERTURES = ["Couvert", "Partiel", "Manquant", "Hors application"]
PASTILLES = {"Couvert": "🟢", "Partiel": "🟠", "Manquant": "🔴", "Hors application": "⚪"}


def charger() -> pd.DataFrame:
    return pd.read_csv(FICHIER, dtype=str, keep_default_na=False)


def faits_campagne(c: dict) -> list[tuple[str, str]]:
    """Chiffres de la campagne affichée, lus dans le moteur, à mettre en face des constats."""
    g, d = c["gouv"], c["donnees"]
    crit = d[d["critique"].astype(bool)]
    expert = int(crit["critique_expert"].fillna(False).astype(str).str.lower().eq("true").sum()) \
        if "critique_expert" in crit else 0
    faits = [("Zones de risque critiques couvertes par un contrôle",
              f"{g['nb_zones_risque_critiques'] - g['nb_zones_non_couvertes']} sur {g['nb_zones_risque_critiques']}"),
             ("Données critiques par tests de sensibilité", f"{len(crit) - expert} sur {len(crit)} "
              f"({expert} à dire d'expert, signalée{'s' if expert > 1 else ''})")]
    n2 = c.get("niveau2")
    if n2 is not None and len(n2):
        for ident, libelle in (("N2-07", "Données externes documentées et contrôlées"),
                               ("N2-02", "Contrôles réalisés dans leur périodicité")):
            ligne = n2[n2["id"] == ident]
            if len(ligne):
                faits.append((libelle, ligne.iloc[0]["valeur"]))
    return faits


def markdown(df: pd.DataFrame) -> str:
    """La grille en Markdown, à emporter (prise de poste, comité, auto-évaluation)."""
    l = ["# Constats de l'ACPR sur la qualité des données et couverture par l'Atelier QDD", "",
         "*Sources publiques de l'ACPR ; enquêtes déclaratives 2022 et 2024, communiqué du 11/01/2021 ; points de la "
         "notice du 08/11/2023. Données de l'application fictives.*", ""]
    for r in df.itertuples():
        l += [f"## {r.id} · {r.theme} — {r.couverture}", "", f"**Constat :** {r.constat}", "",
              f"**Chiffres :** {r.chiffre}", "", f"> « {r.citation} » — {r.source}, p. {r.page}", "",
              f"**Notice (points) :** {r.notice_points}", "", f"**Dans l'application :** {r.dans_l_application}", "",
              f"**Reste à faire en entreprise :** {r.reste_a_faire}", ""]
    return "\n".join(l)


def afficher(c: dict, aller, pages: dict) -> None:
    import streamlit as st

    df = charger()
    st.markdown("Ce que l'ACPR relève le plus souvent sur la gestion et la qualité des données des assureurs, chaque "
                "constat avec sa source, sa page et une citation exacte, face à ce que l'application couvre et à ce qui "
                "reste à faire en entreprise.")
    st.caption("Les enquêtes 2022 (239 organismes) et 2024 (224 organismes) reposent sur les déclarations des "
               "organismes, ce que l'ACPR rappelle en tête de chaque synthèse ; le communiqué du 11/01/2021 cite "
               "aussi les contrôles sur place de l'ACPR. Les constats propres à un organisme (rapports de contrôle) "
               "sont confidentiels et ne figurent pas ici.")
    compte = df["couverture"].value_counts()
    for col, cv in zip(st.columns(4), COUVERTURES):
        col.metric(f"{PASTILLES[cv]} {cv}", int(compte.get(cv, 0)), border=True)
    with st.container(border=True):
        st.markdown(f"**Dans la campagne affichée ({c['campagne']})**")
        for libelle, valeur in faits_campagne(c):
            g, d = st.columns([3, 1])
            g.markdown(libelle)
            d.markdown(f"**{valeur}**")
    choix = st.pills("Afficher", COUVERTURES, selection_mode="multi", default=COUVERTURES, key="acpr_filtre")
    for r in df[df["couverture"].isin(choix or COUVERTURES)].itertuples():
        with st.expander(f"{PASTILLES[r.couverture]} **{r.id} · {r.theme}** — {r.constat}"):
            st.markdown(f"**Chiffres :** {r.chiffre}")
            st.markdown(f"> « {r.citation} »  \n> — {r.source}, p. {r.page}")
            st.markdown(f"**Notice ACPR, points :** {r.notice_points}")
            st.markdown(f"**Dans l'application ({r.couverture.lower()}) :** {r.dans_l_application}")
            st.markdown(f"**Reste à faire en entreprise :** {r.reste_a_faire}")
            if r.page_app and r.page_app in pages:
                if st.button(f"Voir : {pages[r.page_app][1]}", key=f"acpr_aller_{r.id}", type="tertiary",
                             icon=":material/arrow_forward:"):
                    aller(r.page_app)
    g, d = st.columns(2)
    g.download_button("Grille complète (Markdown)", markdown(df).encode("utf-8"), file_name="constats_acpr.md",
                      mime="text/markdown", icon=":material/description:", width="stretch", key="acpr_md")
    d.download_button("Grille complète (CSV)", df.to_csv(index=False, sep=";").encode("utf-8-sig"),
                      file_name="constats_acpr.csv", mime="text/csv", icon=":material/download:", width="stretch",
                      key="acpr_csv")
