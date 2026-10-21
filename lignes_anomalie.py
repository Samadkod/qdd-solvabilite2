"""Lignes en anomalie et catalogue des règles de contrôle.

Pour chaque contrôle de cohérence (C01 à C10), sql/lignes/<fichier>.sql renvoie les lignes fautives
(objet, montant, valeurs en cause) à la même date d'arrêté que le contrôle agrégé sql/controles/<fichier>.sql.
tests/test_lignes_anomalie.py vérifie que, maille par maille, le nombre de lignes (pondéré pour C03, qui
compte les lignes en trop) est exactement le nombre d'anomalies du contrôle agrégé.
Les contrôles de rapprochement (R) et de restitution (Q) comparent des totaux : ils n'ont pas de « ligne ».
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

RACINE = Path(__file__).resolve().parent
SQL_LIGNES = RACINE / "sql" / "lignes"
SQL_CONTROLES = RACINE / "sql" / "controles"
REFERENTIEL = RACINE / "referentiels" / "referentiel_controles.csv"

MESSAGES = {
    "C01": "Contrat présent dans l'outil de gestion mais absent de l'entrepôt de données.",
    "C02": "Prime acquise négative ou supérieure à la prime émise.",
    "C03": "Numéro de contrat présent plusieurs fois dans l'outil de gestion.",
    "C04": "Sinistre rattaché à un contrat inconnu de l'outil de gestion.",
    "C05": "Provision de dossier négative.",
    "C06": "Date de survenance postérieure à la date de déclaration.",
    "C07": "Sinistre survenu avant la date d'effet du contrat.",
    "C08": "Code ISIN absent ou mal formé (12 caractères attendus).",
    "C09": "Code CIC incohérent avec la classe d'actif.",
    "C10": "Code activité absent de la nomenclature BTP.",
    "R01": "Les primes acquises de la gestion et de la comptabilité doivent être égales.",
    "R02": "Les primes acquises de la gestion et de l'entrepôt doivent être égales.",
    "R03": "Les provisions de la gestion, de l'entrepôt et de l'actuariat doivent être égales.",
    "R04": "Les règlements de la gestion et de la comptabilité doivent être égaux.",
    "R05": "Le taux de cession du traité et celui du modèle doivent être égaux.",
    "R06": "Les valorisations du dépositaire et de la comptabilité doivent être égales.",
    "Q01": "Le bilan S.02.01 doit être égal à la liste des actifs S.06.02.",
    "Q02": "Le Best Estimate déclaré en S.17.01 doit être celui de l'outil de provisionnement.",
    "Q03": "Le triangle S.19.01 doit reprendre les règlements de la gestion.",
    "Q04": "Les primes déclarées en S.05.01 doivent être celles de la comptabilité.",
}
# défauts connus des données fictives (pas du contrôle) : affichés tels quels avec un avertissement
DEFAUTS_CONNUS = {
    "C07": "Défaut connu des données fictives : le générateur tire la date de survenance des sinistres sans tenir "
           "compte de la date d'effet du contrat, d'où environ un sinistre sur deux signalé. Le contrôle est juste ; "
           "il n'est pas exécuté dans les campagnes de démonstration (il reprend son résultat de décembre 2025), "
           "la note n'est donc pas touchée. Correction du générateur en attente de décision.",
}
FAMILLES = {"coherence": "Cohérence", "rapprochement": "Rapprochement", "restitution": "Restitution QRT"}
FREQUENCES = {"T": "Trimestrielle", "S": "Semestrielle", "A": "Annuelle"}
CRITERES = {"E": "Exhaustivité", "X": "Exactitude", "P": "Pertinence"}


def referentiel() -> pd.DataFrame:
    return pd.read_csv(REFERENTIEL, dtype=str, keep_default_na=False)


def _sql(dossier: Path, fichier: str) -> str:
    return (dossier / fichier).read_text(encoding="utf-8")


def lignes(base: Path | str, arrete: str) -> pd.DataFrame:
    """Toutes les lignes en anomalie des contrôles de cohérence à la date d'arrêté."""
    ref = referentiel()
    morceaux = []
    con = duckdb.connect(str(base), read_only=True)
    try:
        for r in ref.itertuples():
            if not (SQL_LIGNES / r.fichier_sql).exists():
                continue
            df = con.execute(_sql(SQL_LIGNES, r.fichier_sql), {"arrete": arrete}).df()
            df.insert(0, "controle", r.controle_id)
            df.insert(1, "libelle", r.libelle)
            df["message"] = MESSAGES.get(r.controle_id, r.libelle)
            df["responsable"] = r.responsable
            morceaux.append(df)
    finally:
        con.close()
    cols = ["controle", "libelle", "maille", "objet", "montant", "poids", "valeurs", "message", "responsable"]
    if not morceaux:
        return pd.DataFrame(columns=cols)
    out = pd.concat(morceaux, ignore_index=True)[cols]
    out["poids"] = out["poids"].astype(int)
    return out.sort_values(["controle", "maille", "objet"]).reset_index(drop=True)


def comptes_agreges(base: Path | str, arrete: str) -> pd.DataFrame:
    """Nombre d'anomalies calculé par les contrôles agrégés (sql/controles), par contrôle et maille."""
    ref = referentiel()
    morceaux = []
    con = duckdb.connect(str(base), read_only=True)
    try:
        for r in ref.itertuples():
            if not (SQL_LIGNES / r.fichier_sql).exists():
                continue
            df = con.execute(_sql(SQL_CONTROLES, r.fichier_sql), {"arrete": arrete}).df()
            df.insert(0, "controle", r.controle_id)
            morceaux.append(df[["controle", "maille", "n_anomalies", "n_elements"]])
    finally:
        con.close()
    return pd.concat(morceaux, ignore_index=True)


def regroupements(df: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par message : combien de lignes, d'objets, de mailles et quel montant (comme un Pareto)."""
    if df.empty:
        return pd.DataFrame(columns=["Contrôle", "Message", "Lignes en anomalie", "Objets", "Mailles", "Montant (€)"])
    g = df.groupby(["controle", "message"], as_index=False).agg(
        lignes=("poids", "sum"), objets=("objet", "nunique"), mailles=("maille", lambda s: ", ".join(sorted(set(s)))),
        montant=("montant", "sum"))
    g = g.sort_values("lignes", ascending=False)
    return g.rename(columns={"controle": "Contrôle", "message": "Message", "lignes": "Lignes en anomalie",
                             "objets": "Objets", "mailles": "Mailles", "montant": "Montant (€)"})


def catalogue(ctrl: pd.DataFrame, df_lignes: pd.DataFrame) -> pd.DataFrame:
    """Catalogue des règles : une ligne par contrôle, avec son état dans la campagne."""
    ref = referentiel()
    ctrl = ctrl.assign(code=ctrl["controle_id"].str.split("|").str[0])
    rang = {"rouge": 3, "orange": 2, "vert": 1}
    lignes_par = df_lignes.groupby("controle")["poids"].sum() if not df_lignes.empty else pd.Series(dtype=int)
    out = []
    for r in ref.itertuples():
        pts = ctrl[ctrl["code"] == r.controle_id]
        statuts = [s for s in pts["statut"].dropna() if s in rang]
        pire = max(statuts, key=rang.get) if statuts else "—"
        out.append({
            "ID": r.controle_id, "Famille": FAMILLES.get(r.famille, r.famille), "Message": MESSAGES.get(r.controle_id, r.libelle),
            "Critères": ", ".join(CRITERES.get(k.strip(), k) for k in r.criteres.split(",") if k.strip()),
            "Fréquence": FREQUENCES.get(r.frequence, r.frequence), "Responsable": r.responsable,
            "Seuil": "Fixe 99,90 % (restitution)" if r.seuil_fixe else "Selon le poids de la donnée",
            "Points de contrôle": int(len(pts)),
            "Réalisé ce trimestre": "oui" if len(pts) and bool(pts["realise_campagne"].all()) else "non",
            "Lignes en anomalie": int(lignes_par.get(r.controle_id, 0)) if (SQL_LIGNES / r.fichier_sql).exists() else None,
            "Pire statut": pire,
        })
    return pd.DataFrame(out)


# ====================================================================== affichage
def afficher_lignes(c: dict, base: Path) -> None:
    import streamlit as st

    df = st.cache_data(show_spinner=False)(lignes)(str(base), c["date"])
    realises = set(c["controles"].loc[c["controles"]["realise_campagne"], "controle_id"].str.split("|").str[0])
    filtres, contenu = st.columns([1, 3.2], gap="medium")
    with filtres, st.container(border=True):
        st.markdown("**Filtres**")
        recherche = st.text_input("Recherche", placeholder="Identifiant, valeur…", label_visibility="collapsed")
        ctrls = st.multiselect("Contrôles", sorted(df["controle"].unique()), placeholder="Tous")
        mailles = st.multiselect("Segment / classe", sorted(df["maille"].unique()), placeholder="Tous")
        seulement = st.toggle("Seulement les contrôles réalisés ce trimestre", value=False,
                              help="Les contrôles non refaits (ex. C07, C08) reprennent un ancien résultat dans la note ; "
                                   "leurs lignes sont montrées à titre indicatif, recalculées sur les données du jour.")
    vue = df
    if ctrls:
        vue = vue[vue["controle"].isin(ctrls)]
    if mailles:
        vue = vue[vue["maille"].isin(mailles)]
    if seulement:
        vue = vue[vue["controle"].isin(realises)]
    if recherche:
        r = recherche.lower()
        vue = vue[vue["objet"].str.lower().str.contains(r, regex=False) | vue["valeurs"].str.lower().str.contains(r, regex=False)]
    with contenu:
        for code, texte in DEFAUTS_CONNUS.items():
            if code in set(vue["controle"]):
                st.warning(f"**{code}** — {texte}", icon="⚠️")
        resultats, groupes = st.tabs(["Résultats", "Regroupements"])
        with resultats:
            st.caption(f"**{int(vue['poids'].sum())} ligne(s) en anomalie** ({len(vue)} objet(s) affiché(s)) · "
                       f"arrêté du {pd.Timestamp(c['date']):%d/%m/%Y}")
            st.dataframe(vue.rename(columns={"controle": "Contrôle", "objet": "Objet", "maille": "Segment",
                                             "valeurs": "Valeurs en cause", "message": "Message",
                                             "responsable": "Responsable", "montant": "Montant (€)"})
                         [["Contrôle", "Objet", "Segment", "Valeurs en cause", "Message", "Montant (€)", "Responsable"]],
                         hide_index=True, width="stretch",
                         column_config={"Montant (€)": st.column_config.NumberColumn(format="%.2f")})
            st.download_button("⬇️ Exporter ces lignes (CSV)", vue.to_csv(index=False, sep=";").encode("utf-8-sig"),
                               file_name=f"lignes_en_anomalie_{c['campagne']}.csv", mime="text/csv")
        with groupes:
            st.caption("Une ligne par message, du plus fréquent au plus rare : par où commencer les corrections.")
            st.dataframe(regroupements(vue), hide_index=True, width="stretch",
                         column_config={"Montant (€)": st.column_config.NumberColumn(format="%.2f")})
    st.caption("Les contrôles de rapprochement (R) et de restitution QRT (Q) comparent des totaux entre outils : ils "
               "n'ont pas de ligne individuelle. Leur détail est dans la page Contrôles.")


def afficher_regles(c: dict, base: Path) -> None:
    import streamlit as st

    df_l = st.cache_data(show_spinner=False)(lignes)(str(base), c["date"])
    cat = catalogue(c["controles"], df_l)
    filtres, contenu = st.columns([1, 3.2], gap="medium")
    with filtres, st.container(border=True):
        st.markdown("**Filtres**")
        recherche = st.text_input("Recherche", placeholder="Mot du message…", label_visibility="collapsed",
                                  key="regles_recherche")
        familles = st.multiselect("Familles", list(FAMILLES.values()), placeholder="Toutes")
        statuts = st.multiselect("Pire statut", ["rouge", "orange", "vert"], placeholder="Tous")
        resp = st.multiselect("Responsable", sorted(cat["Responsable"].unique()), placeholder="Tous")
    vue = cat
    if familles:
        vue = vue[vue["Famille"].isin(familles)]
    if statuts:
        vue = vue[vue["Pire statut"].isin(statuts)]
    if resp:
        vue = vue[vue["Responsable"].isin(resp)]
    if recherche:
        vue = vue[vue["Message"].str.lower().str.contains(recherche.lower(), regex=False)]
    with contenu:
        st.caption(f"**{len(vue)} règle(s)** sur {len(cat)} · source : referentiels/referentiel_controles.csv")
        couleur = {"rouge": "background-color:#F8DEDE;color:#AD3030;font-weight:600",
                   "orange": "background-color:#FBEBCB;color:#9C6400", "vert": "background-color:#DCF1E4;color:#22744A"}
        st.dataframe(vue.style.map(lambda v: couleur.get(v, ""), subset=["Pire statut"]), hide_index=True,
                     width="stretch", column_config={"Lignes en anomalie": st.column_config.NumberColumn(format="%d")})
        st.download_button("⬇️ Télécharger les règles de contrôle (CSV)",
                           vue.to_csv(index=False, sep=";").encode("utf-8-sig"), file_name="regles_de_controle.csv",
                           mime="text/csv")
        choix = st.selectbox("Voir le détail d'une règle", list(vue["ID"]),
                             format_func=lambda i: f"{i} · {MESSAGES.get(i, i)}") if len(vue) else None
        if choix:
            if choix in DEFAUTS_CONNUS:
                st.warning(DEFAUTS_CONNUS[choix], icon="⚠️")
            ref = referentiel().set_index("controle_id").loc[choix]
            pts = c["controles"][c["controles"]["controle_id"].str.split("|").str[0] == choix]
            from explications import p as pct
            st.dataframe(pd.DataFrame({"Point de contrôle": pts["controle_id"], "Résultat": pts["resultat"].map(pct),
                                       "Seuil": pts["seuil"].map(pct), "Retard (périodes)": pts["anteriorite"].astype(int),
                                       "Statut": pts["statut"].fillna("non évalué (donnée non critique)"),
                                       "Ce qui a été compté": pts["detail"]}),
                         hide_index=True, width="stretch")
            with st.expander("Requête SQL du contrôle"):
                st.code(_sql(SQL_CONTROLES, ref["fichier_sql"]), language="sql")
            if (SQL_LIGNES / ref["fichier_sql"]).exists():
                with st.expander("Requête SQL des lignes en anomalie"):
                    st.code(_sql(SQL_LIGNES, ref["fichier_sql"]), language="sql")
