"""Avis QDD sur un projet informatique (notice ACPR, point 18 : le responsable QDD évalue le risque porté par les
projets internes, dont les projets informatiques, en matière de qualité des données).

On déclare ce que le projet touche (systèmes ou flux) ; la grille se déduit du lignage déclaré, du répertoire, du
référentiel des contrôles et des résultats du moteur pour la campagne affichée : données et données critiques
touchées, contrôles à rejouer, étapes à risque sans contrôle, états QRT et données externes concernés. Le niveau de
risque suit des règles écrites (REGLES) ; l'avis QDD reste une décision humaine. Aucun calcul nouveau, rien n'est
conservé : la fiche se télécharge.
"""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

NIVEAUX = ["Élevé", "Moyen", "Faible"]
REGLES = [
    ("Élevé", "Une donnée critique touchée est Bloquante dans la campagne (hors tolérance)."),
    ("Élevé", "Une étape à risque touchée n'a aucun contrôle pour une donnée critique."),
    ("Moyen", "Une donnée critique est touchée, conforme ou à corriger."),
    ("Moyen", "Un état QRT ou une donnée externe est touché."),
    ("Faible", "Aucune donnée critique, aucun état QRT ni aucune donnée externe n'est touché."),
]
AVIS = ["Favorable", "Favorable avec réserves", "Défavorable", "À compléter"]
STATUT = {"vert": "Conforme", "orange": "À corriger", "rouge": "Bloquant"}
ENTETE = "ATELIER QDD · AVIS QDD SUR UN PROJET"
PIED = "Données 100 % fictives · grille tirée du lignage et du moteur ; avis émis par une personne"
EXEMPLE = {"nom": "Refonte du chargement des sinistres vers l'entrepôt (exemple fictif)",
           "systemes": [], "flux": ["F05"],
           "description": "Remplacement du chargement nocturne des sinistres par un nouvel outil d'intégration."}


def systemes(c: dict) -> list[str]:
    cv = c["couverture"]
    return sorted(set(cv["systeme_source"]) | set(cv["systeme_cible"]))


def flux(c: dict) -> pd.DataFrame:
    """Un flux par ligne : identifiant, source, cible, traitement (pour le choix et l'affichage)."""
    cols = ["flux_id", "systeme_source", "systeme_cible", "traitement", "mode", "origine", "zone_risque"]
    return c["couverture"][cols].drop_duplicates("flux_id").sort_values("flux_id", key=lambda s: s.str[1:].astype(int))


def _flux_du_controle(v) -> set[str]:
    return {x.strip() for x in str(v).split(",") if x.strip() and str(v) != "nan"}


def evaluer(c: dict, systemes_touches: list[str] | None = None, flux_touches: list[str] | None = None) -> dict:
    """La grille d'évaluation, déduite du lignage et des résultats de la campagne."""
    cv = c["couverture"]
    sy, fx = set(systemes_touches or []), set(flux_touches or [])
    garde = cv["flux_id"].isin(fx) | cv["systeme_source"].isin(sy) | cv["systeme_cible"].isin(sy)
    etapes = cv[garde].copy()
    fl = flux(c)
    fl = fl[fl["flux_id"].isin(set(etapes["flux_id"]))]
    ids = list(dict.fromkeys(etapes["donnee_id"]))
    d = c["donnees"].set_index("donnee_id").loc[ids].reset_index() if ids else c["donnees"].head(0)
    d = d.assign(Statut=d["statut"].map(STATUT).where(d["critique"].astype(bool), "Non noté"))
    k = c["controles"].copy()
    par_flux = k["flux"].map(lambda v: bool(_flux_du_controle(v) & set(fl["flux_id"])))
    sur_donnee = k["donnee_id"].isin(ids)
    k = k[par_flux | sur_donnee].sort_values("controle_id").assign(Lien=lambda x: par_flux[x.index].map(
        {True: "Contrôle le flux touché", False: "Contrôle une donnée touchée"}))
    lacunes = etapes[etapes["zone_risque"].astype(bool) & ~etapes["couvert"].astype(bool)]
    crit = d[d["critique"].astype(bool)]
    qrt = sorted({m for v in d["etats_qrt"].dropna() for m in re.findall(r"S\.\d{2}\.\d{2}", str(v))})
    externes = fl[fl["origine"] == "Externe"]
    motifs = []
    if (crit["statut"] == "rouge").any():
        motifs.append(("Élevé", REGLES[0][1], ", ".join(crit.loc[crit["statut"] == "rouge", "libelle"])))
    lac_crit = lacunes[lacunes["critique"].astype(bool)]
    if len(lac_crit):
        motifs.append(("Élevé", REGLES[1][1], ", ".join(sorted({f"{r.flux_id} · {r.libelle_donnee}"
                                                                for r in lac_crit.itertuples()}))))
    if len(crit) and not motifs:
        motifs.append(("Moyen", REGLES[2][1], ", ".join(crit["libelle"])))
    if (qrt or len(externes)) and not motifs:
        motifs.append(("Moyen", REGLES[3][1], ", ".join(qrt + list(externes["flux_id"]))))
    niveau = motifs[0][0] if motifs else ("Faible" if len(etapes) else "—")
    return {"campagne": c["campagne"], "date": str(c.get("date", "")), "flux": fl, "etapes": etapes, "donnees": d,
            "critiques": crit, "controles": k, "lacunes": lacunes, "qrt": qrt, "externes": externes,
            "niveau": niveau, "motifs": motifs, "exigences": exigences(fl, crit, k, lacunes, qrt, externes)}


def exigences(fl, crit, k, lacunes, qrt, externes) -> list[tuple[str, str, str]]:
    """Ce que la recette du projet doit prouver (exigence, détail, qui), tiré de la grille."""
    if not len(fl):
        return []
    e = [("Recette des données", "Jeu d'essai rejoué avant et après bascule sur un arrêté connu ; écarts expliqués "
          "ligne à ligne" + (f" pour : {', '.join(crit['libelle'])}" if len(crit) else ""), "Projet + équipe QDD")]
    for code, g in k.assign(code=k["controle_id"].str.split("|").str[0]).groupby("code", sort=True):
        mailles = sorted(m for m in g["maille"].unique() if m != "TOUS")
        e.append((f"Rejouer {code}", f"{g['libelle'].iloc[0]}{' (' + ', '.join(mailles) + ')' if mailles else ''} : "
                  "résultat au moins égal au seuil avant mise en production", g["responsable"].iloc[0]))
    e.append(("Contrôles de chargement", "Volumétrie et requêtes de contrôle (niveau 0) sur les flux "
              + ", ".join(fl["flux_id"]) + " au premier chargement", "Équipe données"))
    for r in lacunes.drop_duplicates("flux_id").itertuples():
        e.append((f"Contrôle à créer sur {r.flux_id}", f"Étape à risque sans contrôle : {r.traitement}", "Équipe QDD"))
    if qrt:
        e.append(("États QRT", "Comparer avant et après sur un arrêté rejoué : " + ", ".join(qrt), "Actuariat / reporting"))
    if len(externes):
        e.append(("Données externes", "Vérifier l'annexe qualité des données du contrat (notice, points 43-44) : "
                  + ", ".join(externes["flux_id"]), "Achats / équipe QDD"))
    e.append(("Lignage et répertoire", "Mettre à jour les flux, systèmes et contrôles modifiés (notice, points 46, 52 "
              "et 58)", "Équipe QDD"))
    return e


def markdown(projet: dict, ev: dict, avis: dict) -> str:
    """La fiche d'avis QDD, à joindre au dossier du projet."""
    l = [f"# Avis QDD sur un projet : {projet.get('nom') or 'sans nom'}", "",
         f"*Atelier QDD, campagne {ev['campagne']}, données fictives. Fiche établie le "
         f"{date.today().strftime('%d/%m/%Y')}. Notice ACPR du 08/11/2023, point 18.*", ""]
    if projet.get("description"):
        l += [f"**Projet :** {projet['description']}", ""]
    l += [f"**Mise en production prévue :** {projet.get('mep') or 'non renseignée'} · **Chef de projet :** "
          f"{projet.get('chef') or 'non renseigné'}", "",
          f"## Niveau de risque QDD : {ev['niveau']}", ""]
    l += [f"- {n} — {r} ({x})" for n, r, x in ev["motifs"]] or ["- Aucune règle d'élévation déclenchée."]
    l += ["", "## Ce que le projet touche", "",
          "- Flux : " + (", ".join(f"{r.flux_id} ({r.systeme_source} → {r.systeme_cible})" for r in ev["flux"].itertuples())
                         or "aucun"),
          f"- Données : {len(ev['donnees'])}, dont {len(ev['critiques'])} critiques",
          f"- Contrôles concernés : {len(ev['controles'])} points de contrôle",
          f"- Étapes à risque sans contrôle : {len(ev['lacunes'])}",
          "- États QRT : " + (", ".join(ev["qrt"]) or "aucun"),
          "- Données externes : " + (", ".join(ev["externes"]["flux_id"]) or "aucune"), "",
          "## Données critiques touchées", ""]
    l += [f"- {r.libelle} : {r.Statut}, note {r.note:.2%} (minimum {r.note_min:.2%}) ; propriétaire {r.proprietaire}"
          .replace(".", ",").replace("%", " %") for r in ev["critiques"].itertuples()] or ["- Aucune."]
    l += ["", "## Exigences de recette", ""]
    l += [f"- **{a}** : {b} — *{q}*" for a, b, q in ev["exigences"]] or ["- Aucune."]
    l += ["", "## Avis QDD", "", f"**Avis :** {avis.get('avis') or 'À compléter'}", "",
          f"**Réserves et conditions :** {avis.get('reserves') or '—'}", "",
          f"**Émis par :** {avis.get('auteur') or '……………………'}", "",
          "*Le niveau de risque suit des règles écrites ; l'avis est une décision humaine. Le lignage est déclaré : "
          "il ne prouve pas une propagation exécutée.*"]
    return "\n".join(l)


def afficher(c: dict) -> None:
    import streamlit as st

    from export_pdf import pdf_depuis_markdown

    st.markdown("Avant qu'un projet informatique change un outil ou un flux, mesurer ce qu'il touche dans le "
                "dispositif QDD et poser les exigences de recette. La notice ACPR (point 18) confie cette évaluation "
                "au responsable QDD ; en 2024, 41 % des responsables QDD la font (enquête ACPR, n°167 p. 8).")
    if st.button("Remplir avec l'exemple", icon=":material/lightbulb:", key="projet_exemple", type="tertiary"):
        st.session_state.update(projet_nom=EXEMPLE["nom"], projet_desc=EXEMPLE["description"],
                                projet_sys=EXEMPLE["systemes"], projet_flux=EXEMPLE["flux"])
    with st.container(border=True):
        g, d = st.columns(2)
        nom = g.text_input("Projet", key="projet_nom", placeholder="ex. Nouvel outil de gestion des sinistres")
        chef = d.text_input("Chef de projet", key="projet_chef")
        desc = st.text_area("Ce que le projet change", key="projet_desc", height=70)
        g, d, m = st.columns([2, 2, 1])
        sy = g.multiselect("Systèmes touchés", systemes(c), key="projet_sys", placeholder="Choisir un ou plusieurs systèmes")
        fl = flux(c)
        lib = {r.flux_id: f"{r.flux_id} · {r.traitement}" for r in fl.itertuples()}
        fx = d.multiselect("Flux touchés", list(lib), format_func=lib.get, key="projet_flux",
                          placeholder="Choisir un ou plusieurs flux")
        mep = m.date_input("Mise en production", value=None, key="projet_mep", format="DD/MM/YYYY")
    if not (sy or fx):
        st.info("Choisissez au moins un système ou un flux touché par le projet.")
        return
    ev = evaluer(c, sy, fx)
    couleur = {"Élevé": "red", "Moyen": "orange", "Faible": "green"}.get(ev["niveau"], "gray")
    st.markdown(f"#### Niveau de risque QDD : :{couleur}-badge[{ev['niveau']}]")
    for n, r, x in ev["motifs"]:
        st.markdown(f"- **{n}** · {r} *({x})*")
    with st.popover("Règles du niveau de risque", icon=":material/rule:"):
        st.markdown("\n".join(f"- **{n}** : {r}" for n, r in REGLES)
                    + "\n\nLa première règle déclenchée, dans cet ordre, fixe le niveau.")
    a, b, cc, dd = st.columns(4)
    a.metric("Données touchées", len(ev["donnees"]), border=True)
    b.metric("Dont critiques", len(ev["critiques"]), border=True)
    cc.metric("Points de contrôle concernés", len(ev["controles"]), border=True)
    dd.metric("Étapes à risque sans contrôle", len(ev["lacunes"]), border=True)
    st.markdown("**Données touchées**")
    st.dataframe(ev["donnees"][["libelle", "Statut", "proprietaire", "etats_qrt", "origine"]], hide_index=True,
                 width="stretch", column_config={"libelle": "Donnée", "proprietaire": "Propriétaire",
                                                 "etats_qrt": "États et usages", "origine": "Origine"})
    st.markdown("**Contrôles à rejouer**")
    st.dataframe(ev["controles"][["controle_id", "libelle", "Lien", "responsable", "statut"]]
                 .assign(statut=lambda x: x["statut"].map(STATUT).fillna("Non noté")), hide_index=True,
                 width="stretch", column_config={"controle_id": "Point de contrôle", "libelle": "Règle",
                                                 "responsable": "Responsable", "statut": "Statut actuel"})
    st.markdown("**Exigences de recette**")
    st.markdown("\n".join(f"- **{a}** : {b} — *{q}*" for a, b, q in ev["exigences"]))
    with st.container(border=True):
        st.markdown("**Avis QDD** · décision humaine, appuyée sur la grille ci-dessus")
        g, d = st.columns([1, 2])
        avis = g.selectbox("Avis", AVIS, index=3, key="projet_avis")
        auteur = g.text_input("Émis par", key="projet_auteur")
        reserves = d.text_area("Réserves et conditions", key="projet_reserves", height=110,
                               placeholder="ex. Mise en production après recette de R03 et R04 sur l'arrêté du 30/09.")
    projet = {"nom": nom, "chef": chef, "description": desc, "mep": mep.strftime("%d/%m/%Y") if mep else ""}
    md = markdown(projet, ev, {"avis": avis, "reserves": reserves, "auteur": auteur})
    g, d = st.columns(2)
    g.download_button("Fiche d'avis (PDF)", pdf_depuis_markdown(md, "Avis QDD sur un projet", ENTETE, PIED),
                      file_name="avis_qdd_projet.pdf", mime="application/pdf", icon=":material/picture_as_pdf:",
                      width="stretch", key="projet_pdf")
    d.download_button("Fiche d'avis (Markdown)", md.encode("utf-8"), file_name="avis_qdd_projet.md",
                      mime="text/markdown", icon=":material/description:", width="stretch", key="projet_md")
    st.caption("Le lignage est déclaré : il ne prouve pas une propagation exécutée. Rien n'est conservé après la "
               "visite ; téléchargez la fiche.")
