"""Liste de suivi des contrôles d'une campagne : exécution, résultat, échéance, durée, détail de la campagne.

Une ligne par point de contrôle (contrôle × segment). Deux statuts séparés :
  - Exécution : le contrôle a-t-il tourné pour cet arrêté ?
      Exécuté | Non réalisé (prévu au plan, pas fait) | Saisi hors outil (résultat repris de l'historique,
      daté de l'arrêté) | Échec technique (la requête ne s'exécute pas au rejeu) ;
  - Résultat : vert / orange / rouge par rapport au seuil, « non noté » si la donnée n'est pas critique.
Un contrôle vert mais non refait n'est pas un bon contrôle : c'est pourquoi les deux sont affichés côte à côte.

Aucun calcul de note ici : on relit les sorties du moteur. Seule règle ajoutée, l'échéance
(qdd_s2.anteriorite.prochaine_echeance), cohérente avec l'antériorité (testé).
"""
from __future__ import annotations

import pandas as pd

from explications import MODALITES
from qdd_s2.anteriorite import prochaine_echeance

EXECUTIONS = ["Exécuté", "Saisi hors outil", "Non réalisé", "Échec technique"]
RESULTATS = ["rouge", "orange", "vert", "non noté"]
PERIODES = ["Toutes", "Cette campagne", "Avant cette campagne"]
NOMS_FREQUENCE = {"M": "Mensuelle", "T": "Trimestrielle", "S": "Semestrielle", "A": "Annuelle"}


def _execution(r, rejeu: dict) -> str:
    if not r.realise_campagne:
        return "Non réalisé"
    if str(r.detail).startswith("Résultat antérieur"):
        return "Saisi hors outil"
    return "Échec technique" if rejeu.get(r.controle, "Exécuté") == "Échec technique" else "Exécuté"


def liste_suivi(c: dict, execution: pd.DataFrame | None = None, historique: list[dict] | None = None) -> pd.DataFrame:
    """c : vue d'une campagne (clés « controles » et « date ») ; execution : rejeu des requêtes (chargement.execution) ;
    historique : vues des campagnes jusqu'à c incluse, dans l'ordre, pour la colonne « Tendance »."""
    hist = [dict(zip(h["controles"]["controle_id"], h["controles"]["resultat"])) for h in (historique or [])]
    ctrl = c["controles"]
    arrete = pd.Timestamp(c["date"])
    rejeu = {} if execution is None else dict(zip(execution["Contrôle"], execution["Statut"]))
    duree = {} if execution is None else dict(zip(execution["Contrôle"], execution["Durée (ms)"]))
    lignes = []
    for r in ctrl.itertuples():
        exe = _execution(r, rejeu)
        ech = prochaine_echeance(r.date_derniere_real, r.frequence)
        statut = r.statut if isinstance(r.statut, str) else "non noté"
        retard = int(r.anteriorite)
        lignes.append({
            "Contrôle": r.controle, "Segment": MODALITES.get(r.maille, r.maille), "Libellé": r.libelle, "Donnée": r.donnee_id,
            "Responsable": r.responsable, "Fréquence": NOMS_FREQUENCE.get(r.frequence, r.frequence),
            "Exécution": exe, "Résultat": r.resultat, "Seuil": r.seuil, "Statut": statut,
            "Réalisé le": pd.Timestamp(r.date_derniere_real), "Échéance": ech,
            "Retard (périodes)": retard,
            "Durée (ms)": duree.get(r.controle) if exe == "Exécuté" else None,
            "À surveiller": statut in ("rouge", "orange") or retard > 0 or exe != "Exécuté",
            "Lignes": r.controle in CONTROLES_AVEC_LIGNES,
            "Tendance": [round(h[r.controle_id] * 100, 2) for h in hist if r.controle_id in h],
        })
    out = pd.DataFrame(lignes)
    out["Réalisé cette campagne"] = out["Réalisé le"] == arrete
    return out


CONTROLES_AVEC_LIGNES = {f"C{i:02d}" for i in range(1, 11)}  # sql/lignes/C01…C10


def filtrer(df: pd.DataFrame, executions=(), resultats=(), periode: str = "Toutes", surveiller: bool = False,
            recherche: str = "") -> pd.DataFrame:
    """Filtres de la liste. « en retard » peut figurer dans resultats (raccourci de la Synthèse)."""
    vue = df
    if executions:
        vue = vue[vue["Exécution"].isin(executions)]
    if resultats:
        m = vue["Statut"].isin([x for x in resultats if x != "en retard"])
        if "en retard" in resultats:
            m |= vue["Retard (périodes)"] > 0
        vue = vue[m]
    if periode == "Cette campagne":
        vue = vue[vue["Réalisé cette campagne"]]
    elif periode == "Avant cette campagne":
        vue = vue[~vue["Réalisé cette campagne"]]
    if surveiller:
        vue = vue[vue["À surveiller"]]
    if recherche:
        t = recherche.lower()
        texte = (vue["Contrôle"] + " " + vue["Segment"] + " " + vue["Libellé"] + " " + vue["Donnée"] + " "
                 + vue["Responsable"]).str.lower()
        vue = vue[texte.str.contains(t, regex=False)]
    return vue


def detail_campagne(df: pd.DataFrame) -> dict:
    """Compteurs du panneau de droite. Avancement = contrôles (pas points) exécutés pour cet arrêté."""
    par_ctrl = df.groupby("Contrôle")["Exécution"].first()
    n_ctrl, n_exec = len(par_ctrl), int((par_ctrl == "Exécuté").sum())
    return {
        "avancement": n_exec / n_ctrl if n_ctrl else float("nan"),
        "nb_controles": n_ctrl, "nb_executes": n_exec,
        "nb_non_realises": int((par_ctrl == "Non réalisé").sum()),
        "nb_saisis": int((par_ctrl == "Saisi hors outil").sum()),
        "nb_echecs": int((par_ctrl == "Échec technique").sum()),
        "nb_points": len(df),
        **{f"nb_{s.replace(' ', '_')}": int((df["Statut"] == s).sum()) for s in RESULTATS},
        "nb_en_retard": int((df["Retard (périodes)"] > 0).sum()),
        "nb_a_surveiller": int(df["À surveiller"].sum()),
        "duree_totale_ms": float(df.drop_duplicates("Contrôle")["Durée (ms)"].fillna(0).sum()),
    }


# ====================================================================== affichage Streamlit
CLES_FILTRES = {"suivi_recherche": "", "filtre_periode": "Toutes", "filtre_execution": [], "filtre_controles": [],
                "filtre_surveiller": False}
PASTILLES = {"rouge": ":red[:material/fiber_manual_record:]", "orange": ":orange[:material/fiber_manual_record:]",
             "vert": ":green[:material/fiber_manual_record:]", "non noté": ":gray[:material/radio_button_unchecked:]",
             "en retard": ":red[:material/schedule:]"}
ICONES_EXECUTION = {"Exécuté": ":material/check:", "Saisi hors outil": ":material/edit_note:",
                    "Non réalisé": ":material/do_not_disturb_on:", "Échec technique": ":material/error:"}


def _effacer() -> None:
    import streamlit as st
    st.session_state.update(CLES_FILTRES)


def afficher_suivi(c: dict, execution: pd.DataFrame, aller, couleurs: dict, historique: list[dict] | None = None) -> None:
    import streamlit as st

    df = liste_suivi(c, execution, historique)
    nb_exe = df["Exécution"].value_counts()
    nb_res = df["Statut"].value_counts().to_dict() | {"en retard": int((df["Retard (périodes)"] > 0).sum())}
    nb_per = {"Toutes": len(df), "Cette campagne": int(df["Réalisé cette campagne"].sum()),
              "Avant cette campagne": int((~df["Réalisé cette campagne"]).sum())}
    filtres, contenu, detail = st.columns([1.15, 3.3, 1.1], gap="medium")
    with filtres, st.container(border=True, key="qdd_filtres"):
        st.markdown("**Filtres**")
        st.caption("Les nombres comptent des points de contrôle (un contrôle × un segment).")
        recherche = st.text_input("Recherche", placeholder="Contrôle, donnée, responsable…", icon=":material/search:",
                                  label_visibility="collapsed", key="suivi_recherche")
        surveiller = st.toggle(f"À surveiller seulement ({int(df['À surveiller'].sum())})", key="filtre_surveiller",
                               help="Rouge ou orange, en retard, ou pas exécuté normalement pour cet arrêté.")
        st.markdown("###### :material/event_available: Réalisé")
        periode = st.pills("Réalisé", PERIODES, default="Toutes", key="filtre_periode", label_visibility="collapsed",
                           format_func=lambda x: f"{x} · {nb_per[x]}") or "Toutes"
        st.markdown("###### :material/play_circle: Exécution")
        executions = st.pills("Exécution", [e for e in EXECUTIONS if nb_exe.get(e, 0)], selection_mode="multi",
                              key="filtre_execution", label_visibility="collapsed",
                              format_func=lambda x: f"{ICONES_EXECUTION[x]} {x} · {nb_exe.get(x, 0)}")
        st.markdown("###### :material/traffic: Résultat")
        resultats = st.pills("Résultat", RESULTATS + ["en retard"], selection_mode="multi", key="filtre_controles",
                             label_visibility="collapsed",
                             format_func=lambda x: f"{PASTILLES[x]} {x} · {nb_res.get(x, 0)}")
        st.button("Effacer les filtres", icon=":material/filter_alt_off:", on_click=_effacer, key="suivi_effacer",
                  type="tertiary")
    vue = filtrer(df, executions, resultats, periode, surveiller, recherche)

    with contenu:
        st.caption(f"{len(vue)} point(s) de contrôle affiché(s) sur {len(df)}. Cliquez sur une ligne pour voir "
                   "ses lignes en anomalie ou son détail.")
        aff = vue.assign(**{"Réalisé le": vue["Réalisé le"].dt.strftime("%d/%m/%Y"),
                            "Échéance": vue["Échéance"].dt.strftime("%d/%m/%Y")})
        cols = ["Contrôle", "Segment", "Exécution", "Statut", "Tendance", "Résultat", "Seuil", "Échéance",
                "Retard (périodes)", "Réalisé le", "Durée (ms)", "Libellé", "Responsable"]
        ton_exe = {"Exécuté": couleurs["vert"], "Saisi hors outil": couleurs["orange"],
                   "Non réalisé": couleurs["orange"], "Échec technique": couleurs["rouge"]}
        sel = st.dataframe(
            aff[cols].style.format({"Résultat": _pct, "Seuil": _pct, "Durée (ms)": lambda v: "" if pd.isna(v) else f"{v:.1f}"})
            .map(lambda v: couleurs.get(v, ""), subset=["Statut"])
            .map(lambda v: ton_exe.get(v, ""), subset=["Exécution"])
            .map(lambda v: couleurs["rouge"] if isinstance(v, (int, float)) and v > 0 else "", subset=["Retard (périodes)"]),
            hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key="suivi_selection",
            column_config={"Segment": st.column_config.TextColumn(width="small"),
                           "Tendance": st.column_config.LineChartColumn(
                "Tendance", y_min=85, y_max=100,
                help="Résultat du point de contrôle, campagne après campagne, jusqu'à celle affichée. Même échelle "
                     "pour toutes les lignes (85 % en bas, 100 % en haut) : une pente visible est une vraie baisse.")})
        lignes_sel = sel.selection.rows if sel is not None else []
        if lignes_sel:
            r = vue.iloc[lignes_sel[0]]
            with st.container(border=True):
                st.markdown(f"**{r['Contrôle']} · {r['Libellé']} — {r['Segment']}**")
                st.markdown(_resume(r, c))
                if r["Lignes"]:
                    if st.button(f"Voir les lignes en anomalie de {r['Contrôle']}", icon=":material/search:",
                                 key="suivi_loupe", type="primary"):
                        aller("lignes", lignes_controles=[r["Contrôle"]])
                else:
                    st.caption("Ce contrôle compare des totaux entre outils : il n'y a pas de ligne fautive à lister, "
                               "l'écart est dans la colonne « detail » de la page Note & données.")
        st.download_button("Exporter cette liste (CSV)", icon=":material/download:",
                           data=aff[cols].assign(Tendance=aff["Tendance"].map(
                               lambda t: " → ".join(f"{v:.2f}".replace(".", ",") for v in t)))
                           .to_csv(index=False, sep=";").encode("utf-8-sig"),
                           file_name=f"suivi_controles_{c['campagne']}.csv", mime="text/csv")
        st.caption("**Échéance** : prochaine fin de période (trimestre, semestre, année) après la dernière réalisation. "
                   "Échéance passée à la date d'arrêté = contrôle en retard, son résultat est pénalisé de 5 % par "
                   "période. **Durée** : temps de la requête au rejeu, en millisecondes (données fictives). "
                   "**Saisi hors outil** : résultat daté de l'arrêté mais repris de l'historique, sans exécution.")

    with detail, st.container(border=True):
        d = detail_campagne(df)
        st.markdown(f"**Campagne {c['campagne']}**")
        st.markdown(f'<div class="qdd-tuile-valeur">{d["avancement"] * 100:.0f} %</div>'.replace(".", ","),
                    unsafe_allow_html=True)
        st.caption(f"des contrôles exécutés pour l'arrêté ({d['nb_executes']} sur {d['nb_controles']})")
        st.progress(d["avancement"])
        st.markdown(
            f"Contrôles non réalisés : **{d['nb_non_realises']}**  \n"
            + (f"Contrôles saisis hors outil : **{d['nb_saisis']}**  \n" if d["nb_saisis"] else "")
            + f"Échecs techniques : **{d['nb_echecs']}**")
        st.divider()
        st.markdown(
            f"Points de contrôle : **{d['nb_points']}**  \n"
            f":red[Rouges] : **{d['nb_rouge']}**  \n:orange[Orange] : **{d['nb_orange']}**  \n"
            f":green[Verts] : **{d['nb_vert']}**  \nNon notés : **{d['nb_non_noté']}**  \n"
            f"En retard : **{d['nb_en_retard']}**")
        st.divider()
        st.markdown(f"À surveiller : **{d['nb_a_surveiller']}**  \n"
                    f"Durée totale du rejeu : **{d['duree_totale_ms']:.0f} ms**")


def _pct(v) -> str:
    return "—" if v is None or pd.isna(v) else f"{v * 100:.2f} %".replace(".", ",")


def _resume(r: pd.Series, c: dict) -> str:
    morceaux = [f"Exécution : **{r['Exécution']}** · résultat **{_pct(r['Résultat'])}** pour un seuil de "
                f"**{_pct(r['Seuil'])}** → **{r['Statut']}**."]
    if r["Retard (périodes)"] > 0:
        morceaux.append(f"Dernière réalisation le {r['Réalisé le']:%d/%m/%Y}, échéance dépassée le "
                        f"{r['Échéance']:%d/%m/%Y} : **{r['Retard (périodes)']} période(s) de retard**.")
    else:
        morceaux.append(f"À jour : prochaine échéance le {r['Échéance']:%d/%m/%Y} ({r['Fréquence'].lower()}).")
    morceaux.append(f"Responsable : {r['Responsable']}.")
    return "  \n".join(morceaux)
