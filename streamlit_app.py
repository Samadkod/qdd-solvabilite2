"""Atelier QDD Solvabilité 2 — application Streamlit.

Onglets :
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
                    "couverture": c.couverture, "registre": c.registre, "journal": c.journal})
    return out, var, xlsx


def pct(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:.{d}f} %".replace(".", ",")


COULEUR = {"vert": "background-color:#DCF1E4;color:#22744A", "orange": "background-color:#FBEBCB;color:#9C6400",
           "rouge": "background-color:#F8DEDE;color:#AD3030;font-weight:600"}

st.title("Atelier QDD Solvabilité 2")
st.caption("Méthode du mémoire de C. Motard (ISFA / Grant Thornton, 2024), corrigée et industrialisée — "
           "données **fictives** d'un assureur dommages BTP.")

t1, t2, t4, t3 = st.tabs(["📚 Atelier (révision)", "⚙️ Campagne live", "🗂️ Gouvernance", "🧾 Code SAS / SQL"])

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

    m = st.columns(6)
    m[0].metric("Note QDD agrégée", pct(I["note"]),
                None if prev is None else f"{(I['note'] - prev['ind']['note']) * 100:+.2f} pt")
    m[1].metric("Objectif (note min)", pct(I["note_min"]))
    m[2].metric("Écart à l'objectif", pct(I["ecart_objectif"]))
    m[3].metric("Données hors tolérance", f"{I['nb_donnees_hors_tolerance']} / {I['nb_donnees_critiques']}")
    m[4].metric("Contrôles à jour", pct(I["taux_validation"], 0))
    m[5].metric("Contrôles conformes", pct(I["taux_conformite_controles"], 0))
    g = c["gouv"]
    m2 = st.columns(6)
    m2[0].metric("Restitutions QRT conformes", pct(I["taux_conformite_restitutions"], 0))
    m2[1].metric("Zones de risque couvertes", pct(g["taux_couverture_zones_risque"], 0),
                 help="Flux sans contrôle : " + ", ".join(g["flux_non_couverts"]))
    m2[2].metric("Anomalies ouvertes", g["nb_anomalies_ouvertes"])
    m2[3].metric("dont gravité haute", g["nb_anomalies_haute"])
    m2[4].metric("dont échéance dépassée", g["nb_anomalies_en_retard"])
    m2[5].metric("Anomalies clôturées", g["nb_anomalies_cloturees"])

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

    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Pourquoi la note a bougé (N-1 → N)")
        v = var[(var["impact"].abs() > 1e-9) | var["impact"].isna()].copy()
        v["debut"] = (v["note"] - v["impact"].fillna(0)).where(v["impact"].notna(), v["note"].min() - 0.005)
        v["sens"] = v["impact"].apply(lambda x: "Total" if pd.isna(x) else ("Hausse" if x >= 0 else "Baisse"))
        v["ordre"] = range(len(v))
        v["libelle"] = v["etape"].str.replace(" (antériorité intacte)", "", regex=False)
        v["texte"] = v.apply(lambda r: pct(r.note) if pd.isna(r.impact) else f"{r.impact * 100:+.2f} pt", axis=1)
        base = alt.Chart(v).encode(y=alt.Y("libelle:N", sort=alt.SortField("ordre"), title=None))
        bars = base.mark_bar().encode(
            x=alt.X("debut:Q", title="Note QDD agrégée", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False)),
            x2="note:Q",
            color=alt.Color("sens:N", scale=alt.Scale(domain=["Total", "Hausse", "Baisse"],
                                                      range=["#0E5A69", "#22744A", "#AD3030"]), legend=None))
        st.altair_chart(bars + base.mark_text(align="left", dx=4).encode(
            x="note:Q", text="texte:N"), width="stretch")
        st.caption("Substitutions successives (mémoire, tableau 20) aux paramètres choisis.")
    with g2:
        st.subheader("Par axe d'analyse")
        axe = st.selectbox("Axe", ["maille", "etape", "criteres", "responsable"],
                           format_func={"maille": "Segment / classe", "etape": "Étape de la chaîne",
                                        "criteres": "Critère S2", "responsable": "Responsable"}.get)
        a = c["axes"][axe].rename(columns={axe: "modalite"}).dropna(subset=["note"])
        a["statut"] = a.apply(lambda r: "vert" if r.note >= r.note_min else
                              ("orange" if r.note >= r.note_min - 0.02 else "rouge"), axis=1)
        bar = alt.Chart(a).mark_bar().encode(
            y=alt.Y("modalite:N", sort="x", title=None),
            x=alt.X("note:Q", title="Note", axis=alt.Axis(format="%"), scale=alt.Scale(zero=False)),
            color=alt.Color("statut:N", scale=alt.Scale(domain=["vert", "orange", "rouge"],
                                                        range=["#22744A", "#C98A10", "#AD3030"]), legend=None),
            tooltip=[alt.Tooltip("note:Q", format=".2%"), alt.Tooltip("note_min:Q", format=".2%")])
        tick = alt.Chart(a).mark_tick(color="black", thickness=2, size=22).encode(y="modalite:N", x="note_min:Q")
        st.altair_chart(bar + tick, width="stretch")
        st.caption("Barre = note ; trait noir = note minimum.")

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

    with st.expander("Sensibilités du SCR et test de linéarité"):
        s = c["sens"]
        st.dataframe(s.style.format({col: pct for col in s.columns if col.startswith("s") or col == "non_linearite"}),
                     hide_index=True, width="stretch")
        st.caption(f"SCR (formule standard simplifiée, non réglementaire) : {c['scr']:,.1f} M€".replace(",", " "))

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
