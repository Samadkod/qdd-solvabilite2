"""Atelier QDD Solvabilité 2 — application Streamlit.

Onglets :
  0. Guide terre à terre : le dispositif expliqué sans jargon, chiffres de la campagne en direct
  0 bis. SAS pratique : exercices progressifs corrigés, résultats attendus recalculés sur les CSV de démo
  1. Atelier : fiches, QCM, vrai/faux, simulateur, avis critique, plan 90 jours (HTML autonome)
  2. Campagne live : le moteur Python tourne en direct sur le SI fictif, paramètres modifiables
  3. Code SAS / SQL : la version production (PROC SQL) et la bibliothèque de contrôles
Données 100 % fictives (assureur dommages BTP simulé).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from qdd_s2.campagne import Config, lancer_campagnes
from qdd_s2.moteur import Parametres
from qdd_s2.rapport_excel import ecrire_rapport
from exercices_sas import afficher_exercices
from explications import (AIDE_COMPTEURS as AIDE, ETAPES_COURTES, LEGENDE_CONTROLES, LEGENDE_DONNEES, MODALITES,
                          lire_axe, lire_variation)
from guide_terrain import afficher_guide
from style_app import appliquer_style, bandeau
from scripts.generer_donnees_btp import generer

RACINE = Path(__file__).parent
st.set_page_config(page_title="Atelier QDD Solvabilité 2", page_icon="🛡️", layout="wide")


@st.cache_resource
def base_fictive() -> Path:
    # le nom porte l'empreinte du générateur : toute évolution du SI fictif force une régénération
    import hashlib
    emp = hashlib.sha256((RACINE / "scripts" / "generer_donnees_btp.py").read_bytes()).hexdigest()[:10]
    chemin = Path(tempfile.gettempdir()) / f"btp_fictif_{emp}.duckdb"
    if not chemin.exists():
        generer(chemin)
    return chemin


@st.cache_data(show_spinner="Exécution des contrôles et calcul des notes…")
def campagnes(seuil, dscr, coef, degradation, ecart, montant):
    p = Parametres(seuil_significativite=seuil, delta_scr_max=dscr, coef_degradation=coef,
                   methode_degradation=degradation)
    cfg = Config(base=base_fictive(), methode_ecart=ecart, ponderation_montant=montant, params=p)
    camps, var = lancer_campagnes(cfg)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        ecrire_rapport(camps, var, f.name)
        xlsx = Path(f.name).read_bytes()
    out = []
    for c in camps:
        ev = c.evaluation
        out.append({"campagne": c.campagne, "date": c.date_arrete, "scr": c.scr_ref, "ind": ev.indicateurs,
                    "donnees": ev.donnees.reset_index().rename(columns={"index": "donnee_id"}),
                    "controles": ev.controles,
                    "axes": {a: ev.par_axe(a).reset_index() for a in ("maille", "etape", "criteres", "responsable")},
                    "sens": c.sensibilites.reset_index(), "gouv": c.gouvernance,
                    "couverture": c.couverture, "registre": c.registre, "journal": c.journal,
                    "params": ev.params})
    return out, var, xlsx


def pct(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:.{d}f} %".replace(".", ",")


COULEUR = {"vert": "background-color:#DCF1E4;color:#22744A", "orange": "background-color:#FBEBCB;color:#9C6400",
           "rouge": "background-color:#F8DEDE;color:#AD3030;font-weight:600"}

appliquer_style()
bandeau()

t0, t5, t1, t2, t4, t3 = st.tabs(["🧭 Guide terre à terre", "🧪 SAS pratique", "📚 Atelier (révision)",
                                   "⚙️ Campagne live", "🗂️ Gouvernance", "🧾 Code SAS / SQL"])

# ---------------------------------------------------------------- SAS pratique
with t5:
    afficher_exercices()

# ---------------------------------------------------------------- Atelier
with t1:
    html = (RACINE / "app" / "atelier_qdd_s2.html").read_text(encoding="utf-8")
    page = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>[hidden]{display:none!important}</style></head><body>' + html + "</body></html>")
    st.iframe(page, height=1500)

# ---------------------------------------------------------------- Campagne live
with t2:
    with st.sidebar:
        st.header("Paramètres de la méthode")
        st.caption("Ils s'appliquent au *Guide* et à la *Campagne live*. Les valeurs par défaut redonnent "
                   "les chiffres de référence.")
        seuil = st.number_input("Seuil de significativité (%)", 0.1, 20.0, 1.0, 0.1) / 100
        dscr = st.number_input("ΔSCR max par donnée (%)", 0.0, 20.0, 0.5, 0.05) / 100
        coef = st.number_input("Coefficient de dégradation (%)", 0.0, 100.0, 5.0, 1.0) / 100
        degradation = st.radio("Dégradation", ["simple", "composee"], format_func={"simple": "Simple", "composee": "Composée"}.get, horizontal=True)
        ecart = st.radio("Écart de rapprochement", ["memoire", "symetrique"],
                         format_func={"memoire": "Mémoire (max/min − 1)", "symetrique": "Symétrique borné"}.get)
        montant = st.toggle("Ratio d'anomalies pondéré en montant", value=True)
        st.caption("Contrôle de cohérence (éq. 12) : ΔSCR max doit rester sous le seuil.")

    if dscr >= seuil:
        st.error(f"Paramètres incohérents : ΔSCR max ({pct(dscr)}) doit être inférieur au seuil de significativité ({pct(seuil)}) — éq. 12.")
        st.stop()

    camps, var, xlsx = campagnes(seuil, dscr, coef, degradation, ecart, montant)
    noms = [f"{c['campagne']} · {pd.Timestamp(c['date']):%d/%m/%Y}" for c in camps]
    choix = st.segmented_control("Campagne", noms, default=noms[-1]) or noms[-1]
    k = noms.index(choix)
    c, prev = camps[k], camps[k - 1] if k > 0 else None
    I = c["ind"]

    g = c["gouv"]
    st.markdown("##### La note")
    m = st.columns(4)
    m[0].metric("Note QDD agrégée", pct(I["note"]),
                None if prev is None else f"{(I['note'] - prev['ind']['note']) * 100:+.2f} pt".replace(".", ","),
                help=AIDE["note"])
    m[1].metric("Objectif (note min)", pct(I["note_min"]), help=AIDE["objectif"])
    m[2].metric("Écart à l'objectif", pct(I["ecart_objectif"]), help=AIDE["ecart"])
    m[3].metric("Données hors tolérance", f"{I['nb_donnees_hors_tolerance']} / {I['nb_donnees_critiques']}",
                help=AIDE["hors_tol"])
    st.markdown("##### Les contrôles")
    m = st.columns(4)
    m[0].metric("Contrôles à jour", pct(I["taux_validation"], 0), help=AIDE["a_jour"])
    m[1].metric("Contrôles conformes", pct(I["taux_conformite_controles"], 0), help=AIDE["conformes"])
    m[2].metric("Restitutions QRT conformes", pct(I["taux_conformite_restitutions"], 0), help=AIDE["qrt"])
    m[3].metric("Zones de risque couvertes", pct(g["taux_couverture_zones_risque"], 0),
                help=AIDE["zones"] + " Flux sans contrôle : " + ", ".join(g["flux_non_couverts"]) + ".")
    st.markdown("##### Les anomalies")
    m = st.columns(4)
    m[0].metric("Anomalies ouvertes", g["nb_anomalies_ouvertes"], help=AIDE["ouvertes"])
    m[1].metric("dont gravité haute", g["nb_anomalies_haute"], help=AIDE["haute"])
    m[2].metric("dont échéance dépassée", g["nb_anomalies_en_retard"], help=AIDE["retard"])
    m[3].metric("Anomalies clôturées", g["nb_anomalies_cloturees"], help=AIDE["cloturees"])
    st.caption("Survolez le **?** d'un compteur pour savoir ce qu'il mesure. Le calcul pas à pas est dans "
               "*Guide terre à terre → D'où sortent les chiffres*.")

    st.subheader("Données")
    d = c["donnees"][["libelle", "donnee_id", "proprietaire", "sensibilite", "critique", "note", "note_min",
                      "statut", "criteres_couverts", "nb_controles"]].sort_values(
        ["critique", "sensibilite"], ascending=False)
    st.dataframe(
        d.style.format({"sensibilite": pct, "note": pct, "note_min": pct})
         .map(lambda v: COULEUR.get(v, ""), subset=["statut"]),
        hide_index=True, width="stretch",
        column_config={"libelle": "Donnée", "donnee_id": "Identifiant", "proprietaire": "Propriétaire",
                       "sensibilite": "Sensibilité SCR", "critique": "Critique", "note": "Note QDD",
                       "note_min": "Note min", "statut": "Statut", "criteres_couverts": "E/X/P",
                       "nb_controles": "Contrôles"})
    st.caption(LEGENDE_DONNEES)

    st.subheader("Pourquoi la note a bougé depuis la campagne précédente")
    debut, fin = var["note"].iloc[0], var["note"].iloc[-1]
    st.markdown(f"**{pct(debut)}** (N-1) → **{pct(fin)}** (N) : **{(fin - debut) * 100:+.2f} point**".replace(".", ","))
    v = var[var["impact"].notna() & (var["impact"].abs() > 1e-6)].copy()
    v["cause"] = v["etape"].map(ETAPES_COURTES).fillna(v["etape"])
    v["points"] = v["impact"] * 100
    v["sens"] = v["points"].map(lambda x: "Hausse" if x >= 0 else "Baisse")
    v["texte"] = v["points"].map(lambda x: f"{x:+.2f} pt".replace(".", ","))
    base = alt.Chart(v).encode(y=alt.Y("cause:N", sort=v.reindex(v["points"].abs().sort_values(ascending=False).index)["cause"].tolist(), title=None,
                                       axis=alt.Axis(labelLimit=320, labelFontSize=13, labelOverlap=False),
                                       scale=alt.Scale(paddingInner=0.35)))
    barres = base.mark_bar(cornerRadius=4).encode(
        x=alt.X("points:Q", title="Effet sur la note (points)", axis=alt.Axis(format="+.1f", grid=True)),
        color=alt.Color("sens:N", scale=alt.Scale(domain=["Hausse", "Baisse"], range=["#22744A", "#AD3030"]),
                        legend=None),
        tooltip=[alt.Tooltip("cause:N", title="Cause"), alt.Tooltip("texte:N", title="Effet")])
    etiquettes = base.mark_text(align="right", dx=-6, fontSize=13, color="#15202A").encode(
        x="points:Q", text="texte:N")
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#566370").encode(x="x:Q")
    st.altair_chart((barres + etiquettes + zero).properties(height=alt.Step(44)), width="stretch")
    st.info(lire_variation(var), icon="📖")

    st.subheader("Où sont les problèmes ? Écart au minimum, par groupe")
    axe = st.selectbox("Regrouper par", ["maille", "etape", "criteres", "responsable"],
                       format_func={"maille": "Segment / classe d'actif", "etape": "Étape de la chaîne",
                                    "criteres": "Critère de qualité", "responsable": "Responsable"}.get)
    a = c["axes"][axe].rename(columns={axe: "modalite"}).dropna(subset=["note"])
    a["groupe"] = a["modalite"].map(lambda x: MODALITES.get(x, x))
    a["points"] = a["ecart_objectif"] * 100
    a["statut"] = a.apply(lambda r: "Au-dessus du minimum" if r.note >= r.note_min else
                          ("Juste en dessous" if r.note >= r.note_min - 0.02 else "Nettement en dessous"), axis=1)
    a["texte"] = a["points"].map(lambda x: f"{x:+.2f} pt".replace(".", ","))
    a["note_txt"], a["min_txt"] = a["note"].map(pct), a["note_min"].map(pct)
    base = alt.Chart(a).encode(y=alt.Y("groupe:N", sort=a.sort_values("points")["groupe"].tolist(), title=None,
                                       axis=alt.Axis(labelLimit=320, labelFontSize=13, labelOverlap=False),
                                       scale=alt.Scale(paddingInner=0.35)))
    barres = base.mark_bar(cornerRadius=4).encode(
        x=alt.X("points:Q", title="Note − note minimum (points)", axis=alt.Axis(format="+.1f")),
        color=alt.Color("statut:N", scale=alt.Scale(domain=["Au-dessus du minimum", "Juste en dessous",
                                                            "Nettement en dessous"],
                                                    range=["#22744A", "#C98A10", "#AD3030"]),
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("groupe:N", title="Groupe"), alt.Tooltip("note_txt:N", title="Note"),
                 alt.Tooltip("min_txt:N", title="Minimum"), alt.Tooltip("texte:N", title="Écart")])
    etiquettes = (base.transform_filter("datum.points >= 0").mark_text(align="left", dx=6, fontSize=12, color="#15202A")
                  .encode(x="points:Q", text="texte:N")
                  + base.transform_filter("datum.points < 0").mark_text(align="right", dx=-6, fontSize=12, color="#15202A")
                  .encode(x="points:Q", text="texte:N"))
    st.altair_chart((barres + etiquettes + zero).properties(height=alt.Step(40)), width="stretch")
    st.info(lire_axe(a, axe), icon="📖")

    st.subheader("Points de contrôle")
    f = st.pills("Filtre", ["rouge", "orange", "vert", "en retard"], selection_mode="multi")
    ctrl = c["controles"]
    if f:
        mask = ctrl["statut"].isin([x for x in f if x != "en retard"])
        if "en retard" in f:
            mask |= ctrl["anteriorite"] > 0
        ctrl = ctrl[mask]
    cols = ["controle_id", "libelle", "donnee_id", "etape", "responsable", "resultat_brut", "anteriorite",
            "resultat", "seuil", "statut", "detail"]
    st.dataframe(ctrl[cols].style.format({"resultat_brut": pct, "resultat": pct, "seuil": pct})
                 .map(lambda v: COULEUR.get(v, ""), subset=["statut"]),
                 hide_index=True, width="stretch")
    st.caption(LEGENDE_CONTROLES)

    with st.expander("Sensibilités du SCR et test de linéarité"):
        s = c["sens"]
        st.dataframe(s.style.format({col: pct for col in s.columns if col.startswith("s") or col == "non_linearite"}),
                     hide_index=True, width="stretch")
        st.caption(
            f"SCR (formule standard simplifiée, non réglementaire) : {c['scr']:.1f} M€. ".replace(".", ",", 1)
            + "**Lire le tableau.** *valeur* : le montant de la donnée (M€, ou taux pour la cession). *sensibilite* : "
            "on augmente la donnée de 15 % et on mesure de combien le SCR bouge (en %), puis on divise par 15 %. "
            "Les colonnes *s_choc_…* refont le calcul avec d'autres chocs (−15 %, +5 %, +30 %) : si elles restent "
            "proches, la sensibilité est fiable (*lineaire* = vrai). Au-delà de 10 % d'écart (*non_linearite*), "
            "il faut la manier avec prudence.")

    st.download_button("⬇️ Rapport Excel de la campagne N", xlsx, file_name="rapport_qdd.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------------------------------------------------------- Code
with t4:
    st.markdown("**Ce que l'offre appelle le dispositif** : dictionnaire, lignage, contrôles, suivi des anomalies, "
                "piste d'audit. Valeurs de la campagne sélectionnée dans l'onglet *Campagne live*.")
    st.subheader("Registre des anomalies")
    reg = c["registre"]
    st.dataframe(reg.style.map(lambda v: {"Récurrente": COULEUR["rouge"], "Ouverte": COULEUR["orange"],
                                          "Clôturée": COULEUR["vert"]}.get(v, ""), subset=["statut"]),
                 hide_index=True, width="stretch")
    st.subheader("Lignage et couverture des zones de risque")
    cv = c["couverture"]
    seul = st.toggle("Seulement les zones de risque non couvertes (données critiques)", value=True)
    if seul:
        cv = cv[cv["zone_risque"] & cv["critique"] & ~cv["couvert"]]
    st.dataframe(cv[["donnee_id", "ordre", "flux_id", "systeme_source", "systeme_cible", "traitement", "mode",
                     "couvert", "controles", "proprietaire"]], hide_index=True, width="stretch")
    st.subheader("Dictionnaire des données")
    st.dataframe(c["donnees"][["donnee_id", "libelle", "proprietaire", "regle_gestion", "format_attendu",
                               "etats_qrt", "frequence_maj", "critique"]], hide_index=True, width="stretch")
    st.subheader("Journal d'exécution (piste d'audit)")
    st.json(c["journal"], expanded=False)

# ---------------------------------------------------------------- Guide (après Campagne live : utilise la campagne choisie)
with t0:
    afficher_guide(c, var)

with t3:
    st.markdown("**La version production est en SAS / PROC SQL.** Le Python sert de référence testée ; "
                "le SAS reprend les mêmes formules (voir `sas/README_SAS.md`).")
    sas = sorted((RACINE / "sas").glob("*.sas")) + [RACINE / "app" / "chargement_qdd.qvs"]
    fichier = st.selectbox("Programme SAS", sas, format_func=lambda p: p.name)
    st.code(fichier.read_text(encoding="utf-8"), language="sql", line_numbers=True)
    st.divider()
    sql = sorted((RACINE / "sql" / "controles").glob("*.sql"))
    q = st.selectbox("Contrôle SQL (ANSI, testé sur DuckDB)", sql, format_func=lambda p: p.stem)
    st.code(q.read_text(encoding="utf-8"), language="sql")
