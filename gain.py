"""Gain de note avant correction : ce que rapporterait chaque correction, recalculé par le moteur.

Pour chaque point de contrôle imparfait ou en retard, deux hypothèses, chacune recalculée avec le moteur
(`qdd_s2.moteur.evaluer`, mêmes paramètres, mêmes données critiques) sur une copie, sans toucher la base :
- « refait » (point en retard seulement) : le contrôle est refait dans la campagne avec le même résultat brut que la
  dernière fois ; seule la pénalité de retard disparaît ;
- « corrigé » : les lignes fautives sont corrigées et le contrôle refait : résultat brut porté à 100 %.
La seule vraie correction reste celle de l'Atelier de résolution (correction sur copie, recontrôle, validation).
"""
from __future__ import annotations

import pandas as pd

from qdd_s2.moteur import evaluer

STATUTS = {"vert": "Conforme", "orange": "À corriger", "rouge": "Bloquant"}
DERIVEES = ("resultat", "critique", "poids_dans_donnee", "poids_dans_note", "seuil", "evalue", "conforme", "statut")
COLS_DONNEES = ("sensibilite", "critique_expert", "libelle", "proprietaire")


def _entrees(c: dict) -> tuple[pd.DataFrame, pd.DataFrame, set]:
    d = c["donnees"].set_index("donnee_id") if "donnee_id" in c["donnees"] else c["donnees"]
    don = d[[k for k in COLS_DONNEES if k in d]]
    ct = c["controles"]
    return don, ct[[k for k in ct.columns if k not in DERIVEES]].copy(), set(d.index[d["critique"].astype(bool)])


def _recalcul(c: dict, params, ctrl: pd.DataFrame, don: pd.DataFrame, crit: set):
    return evaluer(don, ctrl, params, date_campagne=c["date"], critiques=crit)


def simulations(c: dict, params) -> pd.DataFrame:
    """Une ligne par (point, hypothèse) : note après, gain en points, statut du point et de sa donnée après."""
    don, base, crit = _entrees(c)
    ref = _recalcul(c, params, base, don, crit)
    note0, objectif = ref.indicateurs["note"], ref.indicateurs["note_min"]
    statut_donnee0 = ref.donnees["statut"]
    ct = c["controles"]
    candidats = ct[(ct["resultat"] < 1 - 1e-12) | (ct["anteriorite"].fillna(0) > 0)]
    lignes = []
    for p in candidats.itertuples():
        hyps = []
        if (p.anteriorite or 0) > 0:
            hyps.append(("Refait (même résultat)", {"anteriorite": 0.0}))
        if p.resultat_brut < 1 - 1e-12:
            hyps.append(("Corrigé et refait", {"anteriorite": 0.0, "resultat_brut": 1.0}))
        for nom, changement in hyps:
            ctrl = base.copy()
            masque = ctrl["controle_id"] == p.controle_id
            for col, val in changement.items():
                ctrl.loc[masque, col] = val
            ev = _recalcul(c, params, ctrl, don, crit)
            point = ev.controles.loc[ev.controles["controle_id"] == p.controle_id].iloc[0]
            d_id = p.donnee_id
            lignes.append({
                "point": p.controle_id, "libelle": p.libelle, "responsable": p.responsable, "donnee_id": d_id,
                "donnee": don.loc[d_id, "libelle"] if "libelle" in don and d_id in don.index else d_id,
                "critique": d_id in crit, "dans_la_note": bool(p.inclus_note), "hypothese": nom,
                "statut_point_avant": STATUTS.get(p.statut, "Non noté"),
                "statut_point_apres": STATUTS.get(point["statut"], "Non noté"),
                "statut_donnee_avant": STATUTS.get(statut_donnee0.get(d_id), "Non noté"),
                "statut_donnee_apres": STATUTS.get(ev.donnees["statut"].get(d_id), "Non noté"),
                "note_avant": note0, "note_apres": ev.indicateurs["note"],
                "gain_points": (ev.indicateurs["note"] - note0) * 100, "objectif": objectif})
    out = pd.DataFrame(lignes)
    if out.empty:
        return out
    return out.sort_values(["gain_points", "point"], ascending=[False, True]).reset_index(drop=True)


def par_donnee(c: dict, params) -> pd.DataFrame:
    """Pour chaque donnée critique hors tolérance : statut et note si tous ses points en retard étaient refaits,
    puis si tous ses points étaient corrigés et refaits ; et le plan complet (tout corrigé)."""
    don, base, crit = _entrees(c)
    ref = _recalcul(c, params, base, don, crit)
    note0 = ref.indicateurs["note"]
    d0 = ref.donnees
    lignes = []
    hors = [i for i in d0.index if i in crit and d0.loc[i, "statut"] in ("orange", "rouge")]
    scenarios = [(i, "Tous ses contrôles en retard refaits", {"anteriorite": 0.0}) for i in hors]
    scenarios += [(i, "Tous ses contrôles corrigés et refaits", {"anteriorite": 0.0, "resultat_brut": 1.0}) for i in hors]
    scenarios.append((None, "Plan complet : tout corrigé et refait", {"anteriorite": 0.0, "resultat_brut": 1.0}))
    for d_id, nom, changement in scenarios:
        ctrl = base.copy()
        masque = (ctrl["donnee_id"] == d_id) if d_id else pd.Series(True, index=ctrl.index)
        for col, val in changement.items():
            ctrl.loc[masque, col] = val
        ev = _recalcul(c, params, ctrl, don, crit)
        lignes.append({"donnee_id": d_id or "toutes",
                       "donnee": don.loc[d_id, "libelle"] if d_id and "libelle" in don else "Toutes les données",
                       "hypothese": nom, "points_concernes": int(masque.sum()),
                       "statut_avant": STATUTS.get(d0.loc[d_id, "statut"], "—") if d_id else "—",
                       "statut_apres": STATUTS.get(ev.donnees.loc[d_id, "statut"], "—") if d_id else "—",
                       "note_donnee_apres": ev.donnees.loc[d_id, "note"] if d_id else None,
                       "minimum": d0.loc[d_id, "note_min"] if d_id else None,
                       "note_apres": ev.indicateurs["note"], "gain_points": (ev.indicateurs["note"] - note0) * 100})
    return pd.DataFrame(lignes)


def _pct(x) -> str:
    return f"{x * 100:.2f} %".replace(".", ",")


def afficher(c: dict, params) -> None:
    import streamlit as st

    @st.cache_data(show_spinner="Recalcul de la note pour chaque correction…", max_entries=12)
    def _sim(campagne: str, _c: dict, _p, cle_params: str) -> pd.DataFrame:
        return simulations(_c, _p)

    @st.cache_data(show_spinner=False, max_entries=12)
    def _par_donnee(campagne: str, _c: dict, _p, cle_params: str) -> pd.DataFrame:
        return par_donnee(_c, _p)

    sim = _sim(c["campagne"], c, params, repr(params))
    st.markdown("#### Gain de note avant correction")
    st.caption("Pour chaque point imparfait ou en retard, la note recalculée par le moteur si le point était refait "
               "(même résultat, sans pénalité de retard) ou corrigé et refait (résultat à 100 %). Hypothèses sur une "
               "copie ; la base n'est pas modifiée. La vraie correction passe par l'Atelier de résolution.")
    if sim.empty:
        st.info("Aucun point imparfait ni en retard : rien à simuler.")
        return
    utiles = sim[sim["gain_points"] > 0.005]
    sans = sim[(sim["gain_points"] <= 0.005) & (sim["hypothese"] == "Corrigé et refait")]
    meilleur = utiles.iloc[0] if len(utiles) else None
    a, b, d = st.columns(3)
    a.metric("Note actuelle", _pct(sim["note_avant"].iloc[0]), help=f"Objectif {_pct(sim['objectif'].iloc[0])}",
             border=True)
    if meilleur is not None:
        b.metric("Meilleure correction", meilleur["point"].replace("|", " · "),
                 f"{meilleur['gain_points']:+.2f} pt".replace(".", ","), border=True, help=meilleur["hypothese"])
    d.metric("Corrections sans effet sur la note", int(sans["point"].nunique()), border=True,
             help="Données non critiques ou restitutions QRT (hors note) : à corriger quand même, mais elles ne "
                  "bougent pas la note.")
    st.markdown("**Par donnée hors tolérance : que faut-il pour qu'elle repasse conforme ?**")
    pdn = _par_donnee(c["campagne"], c, params, repr(params))
    st.dataframe(pdn.assign(note_donnee_apres=pdn["note_donnee_apres"].map(lambda x: "—" if pd.isna(x) else _pct(x)),
                            minimum=pdn["minimum"].map(lambda x: "—" if pd.isna(x) else _pct(x)),
                            note_apres=pdn["note_apres"].map(_pct),
                            gain=pdn["gain_points"].map(lambda g: f"{g:+.2f} pt".replace(".", ",")),
                            statut=pdn["statut_avant"] + " → " + pdn["statut_apres"]),
                 hide_index=True, width="stretch",
                 column_order=["donnee", "hypothese", "points_concernes", "note_donnee_apres", "minimum", "statut",
                               "note_apres", "gain"],
                 column_config={"donnee": "Donnée", "hypothese": "Hypothèse", "points_concernes": "Points",
                                "note_donnee_apres": "Note de la donnée après", "minimum": "Minimum",
                                "statut": "Statut de la donnée", "note_apres": "Note QDD après",
                                "gain": "Gain de note"})
    st.markdown("**Point par point**")
    voir_tout = st.toggle("Afficher aussi les corrections sans effet sur la note", key="gain_tout")
    sim = sim if voir_tout else utiles
    vue = sim.assign(point=sim["point"].str.replace("|", " · ", regex=False),
                     note_apres=sim["note_apres"].map(_pct),
                     gain=sim["gain_points"].map(lambda g: f"{g:+.2f} pt".replace(".", ",")),
                     donnee_statut=sim["statut_donnee_avant"] + " → " + sim["statut_donnee_apres"],
                     point_statut=sim["statut_point_avant"] + " → " + sim["statut_point_apres"])
    st.dataframe(vue, hide_index=True, width="stretch",
                 column_order=["point", "hypothese", "gain", "note_apres", "point_statut", "donnee",
                               "donnee_statut", "responsable"],
                 column_config={"point": "Point", "hypothese": "Hypothèse", "gain": "Gain de note",
                                "note_apres": "Note après", "point_statut": "Statut du point",
                                "donnee": "Donnée", "donnee_statut": "Statut de la donnée",
                                "responsable": "Responsable"})
    st.download_button("Exporter les simulations (CSV)", sim.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name=f"gain_de_note_{c['campagne']}.csv", mime="text/csv", icon=":material/download:",
                       key="gain_csv")
