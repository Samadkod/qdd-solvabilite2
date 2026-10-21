"""Atelier QDD Solvabilité 2 — application Streamlit.

Navigation par menu latéral, en quatre rubriques :
  Pilotage QDD : Synthèse (tuiles cliquables + actions), Note & données, Contrôles, Anomalies, Lignes en anomalie,
                 Règles de contrôle, Lignage & dictionnaire
  Comprendre   : D'où sortent les chiffres, Guide terre à terre
  Se former    : SAS pratique, Atelier (révision)
  Technique    : Code SAS / SQL
Le moteur Python tourne en direct sur le SI fictif ; la campagne et les paramètres se choisissent dans le menu.
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
from explications import (ETAPES_COURTES, LEGENDE_CONTROLES, LEGENDE_DONNEES, MODALITES, afficher_d_ou_sortent,
                          lire_axe, lire_variation)
from guide_terrain import afficher_guide
from style_app import appliquer_style, bandeau, entete_page
from lignes_anomalie import afficher_lignes, afficher_regles, lignes as lignes_en_anomalie
from synthese import afficher_synthese
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

# page -> (rubrique, titre, icône, description)
PAGES = {
    "synthese": ("Pilotage QDD", "Synthèse", "📊", "Tout l'état de la campagne en un écran. Cliquez sur ↗ pour le détail."),
    "donnees": ("Pilotage QDD", "Note & données", "🎯", "La note de chaque donnée, pourquoi elle a bougé et où sont les écarts."),
    "controles": ("Pilotage QDD", "Contrôles", "🔍", "Chaque point de contrôle : résultat, retard, seuil et statut."),
    "anomalies": ("Pilotage QDD", "Anomalies", "🚩", "Le registre : qui doit corriger quoi, pour quand."),
    "lignes": ("Pilotage QDD", "Lignes en anomalie", "🧾",
               "Chaque ligne en erreur, contrôle par contrôle : quoi corriger, exactement."),
    "regles": ("Pilotage QDD", "Règles de contrôle", "🛡️",
               "Le catalogue des 20 contrôles : famille, message, responsable, état dans la campagne."),
    "lignage": ("Pilotage QDD", "Lignage & dictionnaire", "🗂️",
                "Le trajet des données, les étapes sans contrôle, la carte d'identité de chaque donnée."),
    "comprendre": ("Comprendre", "D'où sortent les chiffres", "🔎", "Le calcul pas à pas, sur les vrais chiffres."),
    "guide": ("Comprendre", "Guide terre à terre", "🧭", "Le métier, les chiffres et le poste, sans jargon."),
    "sas": ("Se former", "SAS pratique", "🧪", "13 exercices progressifs, corrigés, avec le résultat attendu."),
    "atelier": ("Se former", "Atelier (révision)", "📚", "Fiches, QCM, vrai ou faux, simulateur, plan à 90 jours."),
    "code": ("Technique", "Code SAS / SQL", "💻", "La version production en SAS / PROC SQL et les 20 contrôles SQL."),
}

if "page" not in st.session_state:
    demandee = st.query_params.get("page", "synthese")
    st.session_state["page"] = demandee if demandee in PAGES else "synthese"


def aller(page: str, **etat) -> None:
    """Change de page (depuis un bouton d'action) en préparant éventuellement des filtres."""
    st.session_state.update(etat)
    st.session_state["page"] = page
    st.rerun()


def _choisir(page: str) -> None:
    st.session_state["page"] = page


appliquer_style()

# ---------------------------------------------------------------- menu latéral
with st.sidebar:
    st.markdown('<div class="qdd-marque">🛡️ Atelier QDD<span>Solvabilité 2 · données fictives</span></div>',
                unsafe_allow_html=True)
    rubrique = None
    for cle, (rub, titre, icone, _) in PAGES.items():
        if rub != rubrique:
            st.markdown(f'<div class="qdd-rubrique">{rub}</div>', unsafe_allow_html=True)
            rubrique = rub
        st.button(f"{icone}  {titre}", key=f"menu_{cle}", on_click=_choisir, args=(cle,), width="stretch",
                  type="primary" if st.session_state["page"] == cle else "tertiary")
    st.divider()
    with st.expander("⚙️ Paramètres de la méthode"):
        st.caption("Les valeurs par défaut redonnent les chiffres de référence.")
        seuil = st.number_input("Seuil de significativité (%)", 0.1, 20.0, 1.0, 0.1) / 100
        dscr = st.number_input("ΔSCR max par donnée (%)", 0.0, 20.0, 0.5, 0.05) / 100
        coef = st.number_input("Coefficient de dégradation (%)", 0.0, 100.0, 5.0, 1.0) / 100
        degradation = st.radio("Dégradation", ["simple", "composee"],
                               format_func={"simple": "Simple", "composee": "Composée"}.get, horizontal=True)
        ecart = st.radio("Écart de rapprochement", ["memoire", "symetrique"],
                         format_func={"memoire": "Mémoire (max/min − 1)", "symetrique": "Symétrique borné"}.get)
        montant = st.toggle("Ratio d'anomalies pondéré en montant", value=True)
        st.caption("Contrôle de cohérence (éq. 12) : ΔSCR max doit rester sous le seuil.")

page = st.session_state["page"]
st.query_params["page"] = page

if dscr >= seuil:
    st.error(f"Paramètres incohérents : ΔSCR max ({pct(dscr)}) doit être inférieur au seuil de significativité "
             f"({pct(seuil)}) — éq. 12.")
    st.stop()

camps, var, xlsx = campagnes(seuil, dscr, coef, degradation, ecart, montant)
noms = [f"{c['campagne']} · {pd.Timestamp(c['date']):%d/%m/%Y}" for c in camps]
with st.sidebar:
    choix = st.segmented_control("Campagne affichée", noms, default=noms[-1], key="campagne") or noms[-1]
k = noms.index(choix)
c, prev = camps[k], camps[k - 1] if k > 0 else None

rub, titre, icone, description = PAGES[page]
if page == "synthese":
    bandeau(c["campagne"], pd.Timestamp(c["date"]))
else:
    entete_page(rub, f"{icone} {titre}", description, f"Campagne {c['campagne']} · {pd.Timestamp(c['date']):%d/%m/%Y}")


# ================================================================ pages
def page_donnees() -> None:
    st.subheader("Les données et leur note")
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
    ordre = v.reindex(v["points"].abs().sort_values(ascending=False).index)["cause"].tolist()
    base = alt.Chart(v).encode(y=alt.Y("cause:N", sort=ordre, title=None,
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
    st.download_button("⬇️ Rapport Excel de la campagne", xlsx, file_name="rapport_qdd.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def page_controles() -> None:
    f = st.pills("Filtrer", ["rouge", "orange", "vert", "en retard"], selection_mode="multi", key="filtre_controles")
    ctrl = c["controles"]
    if f:
        mask = ctrl["statut"].isin([x for x in f if x != "en retard"])
        if "en retard" in f:
            mask |= ctrl["anteriorite"] > 0
        ctrl = ctrl[mask]
    st.caption(f"{len(ctrl)} point(s) de contrôle affiché(s) sur {len(c['controles'])}.")
    cols = ["controle_id", "libelle", "donnee_id", "etape", "responsable", "resultat_brut", "anteriorite",
            "resultat", "seuil", "statut", "detail"]
    st.dataframe(ctrl[cols].style.format({"resultat_brut": pct, "resultat": pct, "seuil": pct})
                 .map(lambda v: COULEUR.get(v, ""), subset=["statut"]),
                 hide_index=True, width="stretch")
    st.caption(LEGENDE_CONTROLES)


def page_anomalies() -> None:
    reg = c["registre"]
    f1, f2 = st.columns(2)
    statuts = f1.multiselect("Statut", ["Ouverte", "Récurrente", "Clôturée"], default=["Ouverte", "Récurrente"])
    gravites = f2.multiselect("Gravité", sorted(reg["gravite"].dropna().unique()), placeholder="Toutes")
    vue = reg[reg["statut"].isin(statuts)] if statuts else reg
    if gravites:
        vue = vue[vue["gravite"].isin(gravites)]
    st.caption(f"{len(vue)} anomalie(s) affichée(s) sur {len(reg)}. « Récurrente » : déjà présente à la campagne "
               "précédente. Une anomalie se clôture quand le contrôle est refait à temps et revient au vert.")
    st.dataframe(vue.style.map(lambda v: {"Récurrente": COULEUR["rouge"], "Ouverte": COULEUR["orange"],
                                          "Clôturée": COULEUR["vert"]}.get(v, ""), subset=["statut"]),
                 hide_index=True, width="stretch")
    st.download_button("⬇️ Exporter ces anomalies (CSV)", vue.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name=f"anomalies_{c['campagne']}.csv", mime="text/csv")


def page_lignage() -> None:
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


def page_atelier() -> None:
    html = (RACINE / "app" / "atelier_qdd_s2.html").read_text(encoding="utf-8")
    page_html = ('<!doctype html><html lang="fr"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width,initial-scale=1">'
                 '<style>[hidden]{display:none!important}</style></head><body>' + html + "</body></html>")
    st.iframe(page_html, height=1500)


def page_code() -> None:
    st.markdown("**La version production est en SAS / PROC SQL.** Le Python sert de référence testée ; "
                "le SAS reprend les mêmes formules (voir `sas/README_SAS.md`).")
    sas = sorted((RACINE / "sas").glob("*.sas")) + [RACINE / "app" / "chargement_qdd.qvs"]
    fichier = st.selectbox("Programme SAS", sas, format_func=lambda p: p.name)
    st.code(fichier.read_text(encoding="utf-8"), language="sql", line_numbers=True)
    st.divider()
    sql = sorted((RACINE / "sql" / "controles").glob("*.sql"))
    q = st.selectbox("Contrôle SQL (ANSI, testé sur DuckDB)", sql, format_func=lambda p: p.stem)
    st.code(q.read_text(encoding="utf-8"), language="sql")


{
    "synthese": lambda: afficher_synthese(c, prev, xlsx, aller,
                                          st.cache_data(show_spinner=False)(lignes_en_anomalie)(str(base_fictive()), c["date"])),
    "lignes": lambda: afficher_lignes(c, base_fictive()),
    "regles": lambda: afficher_regles(c, base_fictive()),
    "donnees": page_donnees,
    "controles": page_controles,
    "anomalies": page_anomalies,
    "lignage": page_lignage,
    "comprendre": lambda: afficher_d_ou_sortent(c),
    "guide": lambda: afficher_guide(c, var),
    "sas": afficher_exercices,
    "atelier": page_atelier,
    "code": page_code,
}[page]()
