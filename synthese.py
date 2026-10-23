"""Page « Synthèse » : tuiles de pilotage regroupées par thème, chacune ouvrant la liste qui la compose.

Le calcul des tuiles (valeur, couleur, liste détaillée, évolution depuis la campagne précédente) est séparé de
l'affichage : les tests vérifient que chaque valeur est égale aux indicateurs du moteur, au nombre de lignes de
sa liste, et que l'évolution est colorée selon le sens de l'indicateur (une hausse des anomalies est rouge).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from explications import AIDE_COMPTEURS as AIDE, p

COULEURS = {"rouge": "#AD3030", "orange": "#9C6400", "vert": "#22744A", "gris": "#566370", "bleu": "#0E5A69"}
BLOCS = [("La note", ":material/speed:"), ("Les contrôles", ":material/fact_check:"), ("Les anomalies", ":material/flag:"),
         ("Le chargement et l'exploitation", ":material/settings:")]
CHARGEMENT = "Le chargement et l'exploitation"


@dataclass
class Tuile:
    cle: str
    bloc: str
    titre: str
    valeur: str
    ton: str
    aide: str
    liste: pd.DataFrame | None = None
    nombre: int | None = None     # nombre d'éléments que la tuile compte (= lignes de la liste)
    mesure: float | None = None   # valeur numérique comparée d'une campagne à l'autre
    mieux: str | None = None      # "haut" : une hausse est une amélioration ; "bas" : une baisse ; None : neutre
    unite: str = "nombre"         # "nombre" ou "point" (écart de pourcentages)
    delta: str | None = None
    delta_ton: str = "gris"


def _liste_controles(ctrl: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "Contrôle": ctrl["controle_id"], "Libellé": ctrl["libelle"], "Donnée": ctrl["donnee_id"],
        "Responsable": ctrl["responsable"], "Résultat": ctrl["resultat"].map(p), "Seuil": ctrl["seuil"].map(p),
        "Retard (périodes)": ctrl["anteriorite"].astype(int), "Statut": ctrl["statut"].fillna("—")})


def _liste_anomalies(reg: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "Anomalie": reg["anomalie_id"], "Type": reg["type"], "Libellé": reg["libelle"], "Gravité": reg["gravite"],
        "Propriétaire": reg["proprietaire"], "Échéance": pd.to_datetime(reg["echeance"]).dt.strftime("%d/%m/%Y"),
        "Statut": reg["statut"], "Détectée le": pd.to_datetime(reg["date_detection"]).dt.strftime("%d/%m/%Y"),
        "Clôturée le": pd.to_datetime(reg["date_cloture"]).dt.strftime("%d/%m/%Y").fillna(""),
        "Action attendue": reg["action_attendue"]})


def _compte(cle, bloc, titre, sel_liste, n, total, ton_si, aide, mieux="bas") -> Tuile:
    """Tuile qui compte des éléments : rouge/orange s'il y en a (selon ton_si), vert sinon."""
    valeur = f"{n} sur {total}" if total is not None else str(n)
    return Tuile(cle, bloc, titre, valeur, ton_si if n else "vert", aide, sel_liste, n, float(n), mieux)


def tuiles(c: dict, prev: dict | None, df_lignes: pd.DataFrame | None = None,
           volumes: pd.DataFrame | None = None, execution: pd.DataFrame | None = None) -> list[Tuile]:
    I, g, d, ctrl, reg = c["ind"], c["gouv"], c["donnees"], c["controles"], c["registre"]
    out: list[Tuile] = []

    # ---------------------------------------------------------------- la note
    ok = I["note"] >= I["note_min"]
    out.append(Tuile("note", "La note", "Note QDD agrégée", p(I["note"]), "vert" if ok else "rouge", AIDE["note"],
                     mesure=I["note"], mieux="haut", unite="point"))
    out.append(Tuile("objectif", "La note", "Objectif (note minimum)", p(I["note_min"]), "gris", AIDE["objectif"],
                     mesure=I["note_min"], unite="point"))
    out.append(Tuile("ecart", "La note", "Écart à l'objectif", f"{I['ecart_objectif'] * 100:+.2f} pt".replace(".", ","),
                     "vert" if ok else "rouge", AIDE["ecart"], mesure=I["ecart_objectif"], mieux="haut", unite="point"))
    if prev is not None:
        dv = I["note"] - prev["ind"]["note"]
        out.append(Tuile("variation", "La note", f"Variation depuis {prev['campagne']}".replace("-", "‑"),
                         f"{dv * 100:+.2f} pt".replace(".", ","), "vert" if dv >= 0 else "rouge",
                         "Évolution de la note depuis la campagne précédente. Les causes sont détaillées dans "
                         "« Note & données »."))
    crit = d[d["critique"]]
    ht = crit[crit["note"] < crit["note_min"]].sort_values("sensibilite", ascending=False)
    out.append(_compte("hors_tol", "La note", "Données critiques hors tolérance",
                       pd.DataFrame({"Donnée": ht["libelle"], "Propriétaire": ht["proprietaire"],
                                     "Poids dans le SCR": ht["sensibilite"].map(lambda v: p(v, 1)),
                                     "Note": ht["note"].map(p), "Minimum": ht["note_min"].map(p),
                                     "Statut": ht["statut"]}), len(ht), len(crit), "rouge", AIDE["hors_tol"]))

    # ---------------------------------------------------------------- les contrôles
    notes = ctrl[ctrl["critique"] & ctrl["inclus_note"]]
    retard = notes[notes["anteriorite"] > 0]
    evalues = ctrl[ctrl["evalue"]]
    rouges, oranges = evalues[evalues["statut"] == "rouge"], evalues[evalues["statut"] == "orange"]
    qrt = ctrl[~ctrl["inclus_note"] & ctrl["evalue"]]
    qrt_ko = qrt[qrt["conforme"] != True]  # noqa: E712 (NaN compris)
    out.append(Tuile("ctrl_notes", "Les contrôles", "Contrôles qui comptent dans la note", str(len(notes)), "bleu",
                     "Contrôles portant sur une donnée critique (hors vérifications QRT).",
                     _liste_controles(notes), len(notes), float(len(notes))))
    out.append(_compte("ctrl_retard", "Les contrôles", "Contrôles en retard", _liste_controles(retard), len(retard),
                       None, "orange", AIDE["a_jour"]))
    out.append(_compte("ctrl_rouges", "Les contrôles", "Contrôles bloquants", _liste_controles(rouges), len(rouges),
                       None, "rouge", "Contrôles dont le résultat est nettement sous le seuil (QRT compris)."))
    out.append(_compte("ctrl_oranges", "Les contrôles", "Contrôles à corriger", _liste_controles(oranges), len(oranges),
                       None, "orange", "Contrôles juste sous leur seuil (moins de 2 points)."))
    out.append(_compte("qrt_ko", "Les contrôles", "États QRT non conformes", _liste_controles(qrt_ko), len(qrt_ko),
                       len(qrt), "rouge", AIDE["qrt"]))
    cv = c["couverture"]
    trous = cv[cv["zone_risque"] & cv["critique"] & ~cv["couvert"]]
    out.append(_compte("zones", "Les contrôles", "Étapes à risque sans contrôle",
                       pd.DataFrame({"Flux": trous["flux_id"], "Traitement": trous["traitement"],
                                     "De": trous["systeme_source"], "Vers": trous["systeme_cible"],
                                     "Donnée": trous["libelle_donnee"], "Propriétaire": trous["proprietaire"]}),
                       len(trous), g["nb_zones_risque_critiques"], "rouge", AIDE["zones"]))

    # ---------------------------------------------------------------- les anomalies
    ouv = reg[reg["statut"].isin(["Ouverte", "Récurrente"])]
    en_retard = ouv[pd.to_datetime(ouv["echeance"]) < pd.Timestamp(c["date"])]
    for cle, titre, sel, ton, aide in [
        ("ouvertes", "Anomalies ouvertes", ouv, "orange", AIDE["ouvertes"]),
        ("haute", "Anomalies graves", ouv[ouv["gravite"] == "Haute"], "rouge", AIDE["haute"]),
        ("retard", "Échéance dépassée", en_retard, "rouge", AIDE["retard"]),
        ("recurrentes", "Anomalies récurrentes", ouv[ouv["statut"] == "Récurrente"], "orange",
         "Anomalies déjà présentes à la campagne précédente et toujours pas réglées."),
    ]:
        out.append(_compte(cle, "Les anomalies", titre, _liste_anomalies(sel), len(sel), None, ton, aide))
    clos = reg[reg["statut"] == "Clôturée"]
    out.append(Tuile("cloturees", "Les anomalies", "Anomalies clôturées", str(len(clos)), "vert" if len(clos) else "gris",
                     AIDE["cloturees"], _liste_anomalies(clos), len(clos), float(len(clos)), "haut"))

    # ---------------------------------------------------------------- le chargement et l'exploitation
    if volumes is not None:
        alerte = volumes[volumes["Statut"].isin(["Bloquant", "À expliquer"])]
        bloquant = bool((volumes["Statut"] == "Bloquant").any())
        out.append(_compte("volumes_alerte", CHARGEMENT, "Tables sources en alerte de volume", alerte, len(alerte),
                           len(volumes), "rouge" if bloquant else "orange",
                           "Contrôle de chargement : table vide (bloquant), ou nombre de lignes qui varie de plus de "
                           "10 % depuis le trimestre précédent (à expliquer avant de lire les résultats)."))
    if execution is not None:
        ko = execution[execution["Statut"] != "Exécuté"]
        out.append(_compte("echecs", CHARGEMENT, "Contrôles en échec technique", ko, len(ko), len(execution), "rouge",
                           "Requêtes de contrôle qui n'ont pas pu s'exécuter (erreur, table manquante…). Un contrôle en "
                           "échec ne dit rien de la qualité : ce n'est ni une anomalie, ni un résultat conforme."))
    j = c.get("journal")
    if j:
        from lignes_anomalie import MESSAGES, referentiel
        ref = referentiel()
        code = ctrl["controle_id"].str.split("|").str[0]
        faits = set(code[ctrl["realise_campagne"]])
        non_faits = ref[~ref["controle_id"].isin(faits)]
        out.append(_compte("non_executes", CHARGEMENT, "Contrôles non exécutés ce trimestre",
                           pd.DataFrame({"Contrôle": non_faits["controle_id"],
                                         "Message": non_faits["controle_id"].map(MESSAGES),
                                         "Responsable": non_faits["responsable"]}), len(non_faits), len(ref), "orange",
                           "Ces contrôles n'ont pas tourné à cette campagne (planifiés plus tard ou oubliés) : ils "
                           "reprennent leur dernier résultat connu, avec une pénalité de retard."))
        h = pd.Timestamp(j["horodatage"])
        out.append(Tuile("execution", CHARGEMENT, f"Dernière exécution (à {h:%H:%M})", f"{h:%d/%m/%Y}", "gris",
                         f"Date du dernier calcul de la campagne (version du code {j['version_code']}). "
                         "Le journal complet est dans « Chargement & exécution »."))
        vol = json.loads(j["volumetries_sources"]) if isinstance(j["volumetries_sources"], str) else j["volumetries_sources"]
        total = sum(vol.values())
        out.append(Tuile("lues", CHARGEMENT, "Lignes lues dans les sources", f"{total:,}".replace(",", " "), "gris",
                         "Nombre de lignes lues dans chaque table source à la date d'arrêté.",
                         pd.DataFrame({"Table": list(vol), "Lignes": list(vol.values())}), mesure=float(total)))
    if df_lignes is not None:
        from lignes_anomalie import DEFAUTS_CONNUS, regroupements
        n = int(df_lignes["poids"].sum())
        par = df_lignes.groupby("controle")["poids"].sum()
        connus = " ".join(f"Dont {int(par[k])} pour {k}, défaut connu des données fictives (voir la page)."
                          for k in DEFAUTS_CONNUS if k in par.index)
        out.append(Tuile("lignes", CHARGEMENT, "Lignes en anomalie (cohérence)", f"{n:,}".replace(",", " "),
                         "orange" if n else "vert",
                         "Lignes individuelles en erreur trouvées par les contrôles C01 à C10, sur les données du jour. "
                         "Le détail ligne à ligne est dans la page « Lignes en anomalie ». " + connus,
                         regroupements(df_lignes), mesure=float(n), mieux="bas"))
    return out


def evolutions(courantes: list[Tuile], precedentes: list[Tuile], nom_prec: str) -> list[Tuile]:
    """Ajoute à chaque tuile son évolution depuis la campagne précédente, colorée selon le sens de l'indicateur."""
    avant = {t.cle: t for t in precedentes if t.mesure is not None}
    for t in courantes:
        a = avant.get(t.cle)
        if t.mesure is None or a is None:
            continue
        dv = t.mesure - a.mesure
        if round(dv * 100, 2) == 0 if t.unite == "point" else round(dv) == 0:  # stable à la précision affichée
            t.delta, t.delta_ton = f"= stable depuis {nom_prec}", "gris"
            continue
        fleche = "▲" if dv > 0 else "▼"
        txt = f"{dv * 100:+.2f} pt".replace(".", ",") if t.unite == "point" else f"{dv:+,.0f}".replace(",", " ")
        t.delta = f"{fleche} {txt} depuis {nom_prec}"
        if t.mieux is None:
            t.delta_ton = "gris"
        else:
            t.delta_ton = "vert" if (dv > 0) == (t.mieux == "haut") else "rouge"
    return courantes


# ====================================================================== affichage
def afficher_synthese(c: dict, prev: dict | None, xlsx: bytes, aller, df_lignes: pd.DataFrame | None = None,
                      volumes: pd.DataFrame | None = None, execution: pd.DataFrame | None = None,
                      precedentes: list[Tuile] | None = None) -> None:
    """aller(page, **etat) : change de page (fourni par l'application)."""
    import streamlit as st

    @st.dialog("Détail", width="large")
    def detail(t: Tuile) -> None:
        st.markdown(f"### {t.titre} : {t.valeur}")
        st.caption(t.aide)
        if t.liste is None or t.liste.empty:
            st.success("Rien à signaler : la liste est vide.")
        else:
            from statuts import tableau
            tableau(t.liste, hide_index=True, width="stretch")
            st.download_button("Exporter cette liste (CSV)", icon=":material/download:", data=t.liste.to_csv(index=False, sep=";").encode("utf-8-sig"),
                               file_name=f"{t.cle}_{c['campagne']}.csv", mime="text/csv")

    ts = tuiles(c, prev, df_lignes, volumes, execution)
    if prev is not None and precedentes:
        evolutions(ts, precedentes, prev["campagne"].replace("-", "‑"))
    principal, actions = st.columns([3.6, 1.4], gap="large")
    with principal:
        for bloc, icone in BLOCS:
            st.markdown(f"#### {icone} Synthèse — {bloc[0].lower() + bloc[1:]}")
            groupe = [t for t in ts if t.bloc == bloc]
            for i in range(0, len(groupe), 3):
                cols = st.columns(3)
                for col, t in zip(cols, groupe[i:i + 3]):
                    with col, st.container(border=True):
                        tete, bouton = st.columns([5, 1], vertical_alignment="center")
                        tete.markdown(f'<div class="qdd-tuile-titre">{t.titre}</div>', unsafe_allow_html=True,
                                      help=t.aide)
                        if t.liste is not None and bouton.button("↗", key=f"tuile_{t.cle}",
                                                                 help="Voir le détail", type="tertiary"):
                            detail(t)
                        st.markdown(f'<div class="qdd-tuile-valeur" style="color:{COULEURS[t.ton]}">{t.valeur}</div>',
                                    unsafe_allow_html=True)
                        if t.delta:
                            st.markdown(f'<div class="qdd-tuile-delta" style="color:{COULEURS[t.delta_ton]}">'
                                        f'{t.delta}</div>', unsafe_allow_html=True)
        if df_lignes is not None and not df_lignes.empty:
            from lignes_anomalie import regroupements
            st.markdown("#### :material/leaderboard: Top 5 des messages en anomalie")
            top = regroupements(df_lignes).head(5)
            st.dataframe(top[["Contrôle", "Message", "Lignes en anomalie", "Part"]], hide_index=True, width="stretch",
                         column_config={"Contrôle": st.column_config.TextColumn(width="small"),
                                        "Message": st.column_config.TextColumn(width="large"),
                                        "Lignes en anomalie": st.column_config.NumberColumn("Lignes", width="small"),
                                        "Part": st.column_config.ProgressColumn(format="%.1f %%", min_value=0,
                                                                                 max_value=100, width="small")})
            st.caption("Réflexe de Pareto : corriger d'abord les messages qui pèsent le plus. Part = lignes du message "
                       "÷ total des lignes en anomalie de cohérence.")
    with actions:
        st.markdown('<div class="qdd-actions-titre">ACTIONS</div>', unsafe_allow_html=True)
        for libelle, page, etat in [
            ("Voir les données hors tolérance", "donnees", {}),
            ("Voir les contrôles bloquants", "controles", {"filtre_controles": ["rouge"]}),
            ("Voir les contrôles en retard", "controles", {"filtre_controles": ["en retard"]}),
            ("Voir les anomalies ouvertes", "anomalies", {}),
            ("Voir les lignes en anomalie", "lignes", {}),
            ("Voir les règles de contrôle", "regles", {}),
            ("Voir le chargement et l'exécution", "chargement", {}),
            ("Voir les étapes sans contrôle", "lignage", {}),
            ("Comprendre d'où sortent les chiffres", "comprendre", {}),
        ]:
            if st.button(f"→ {libelle}", key=f"action_{page}_{libelle}", type="tertiary"):
                aller(page, **etat)
        st.divider()
        reg = c["registre"]
        st.download_button("Exporter le registre des anomalies", icon=":material/download:", data=_liste_anomalies(reg).to_csv(index=False, sep=";")
                           .encode("utf-8-sig"), file_name=f"registre_anomalies_{c['campagne']}.csv",
                           mime="text/csv", type="tertiary")
        ko = c["controles"][c["controles"]["statut"].isin(["rouge", "orange"])]
        st.download_button("Exporter les contrôles en anomalie", icon=":material/download:", data=_liste_controles(ko).to_csv(index=False, sep=";")
                           .encode("utf-8-sig"), file_name=f"controles_en_anomalie_{c['campagne']}.csv",
                           mime="text/csv", type="tertiary")
        st.download_button("Rapport Excel complet", xlsx, icon=":material/download:", file_name="rapport_qdd.xlsx", type="tertiary",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.caption("Cliquez sur ↗ dans une tuile pour voir la liste qui la compose. Sous chaque chiffre : son "
                   "évolution depuis la campagne précédente, en vert si elle va dans le bon sens, en rouge sinon.")
