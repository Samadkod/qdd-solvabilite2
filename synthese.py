"""Page « Synthèse » : tuiles de pilotage regroupées par thème, chacune ouvrant la liste qui la compose.

Le calcul des tuiles (valeur, couleur, liste détaillée) est séparé de l'affichage : un test vérifie que
chaque valeur est égale aux indicateurs du moteur et au nombre de lignes de sa liste.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from explications import AIDE_COMPTEURS as AIDE, p

COULEURS = {"rouge": "#AD3030", "orange": "#9C6400", "vert": "#22744A", "gris": "#566370", "bleu": "#0E5A69"}


@dataclass
class Tuile:
    cle: str
    bloc: str
    titre: str
    valeur: str
    ton: str
    aide: str
    liste: pd.DataFrame | None = None
    nombre: int | None = None  # nombre d'éléments que la tuile compte (= lignes de la liste)


def _liste_controles(ctrl: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "Contrôle": ctrl["controle_id"], "Libellé": ctrl["libelle"], "Donnée": ctrl["donnee_id"],
        "Responsable": ctrl["responsable"], "Résultat": ctrl["resultat"].map(p), "Seuil": ctrl["seuil"].map(p),
        "Retard (périodes)": ctrl["anteriorite"].astype(int), "Statut": ctrl["statut"].fillna("—")})


def _liste_anomalies(reg: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "Anomalie": reg["anomalie_id"], "Type": reg["type"], "Libellé": reg["libelle"], "Gravité": reg["gravite"],
        "Propriétaire": reg["proprietaire"], "Échéance": pd.to_datetime(reg["echeance"]).dt.strftime("%d/%m/%Y"),
        "Statut": reg["statut"], "Action attendue": reg["action_attendue"]})


def tuiles(c: dict, prev: dict | None) -> list[Tuile]:
    I, g, d, ctrl, reg = c["ind"], c["gouv"], c["donnees"], c["controles"], c["registre"]
    out: list[Tuile] = []

    # ---------------------------------------------------------------- la note
    ok = I["note"] >= I["note_min"]
    out.append(Tuile("note", "La note", "Note QDD agrégée", p(I["note"]), "vert" if ok else "rouge", AIDE["note"]))
    out.append(Tuile("objectif", "La note", "Objectif (note minimum)", p(I["note_min"]), "gris", AIDE["objectif"]))
    out.append(Tuile("ecart", "La note", "Écart à l'objectif", f"{I['ecart_objectif'] * 100:+.2f} pt".replace(".", ","),
                     "vert" if ok else "rouge", AIDE["ecart"]))
    if prev is not None:
        dv = I["note"] - prev["ind"]["note"]
        out.append(Tuile("variation", "La note", f"Variation depuis {prev['campagne']}".replace("-", "\u2011"),
                         f"{dv * 100:+.2f} pt".replace(".", ","), "vert" if dv >= 0 else "rouge",
                         "Évolution de la note depuis la campagne précédente. Les causes sont détaillées dans "
                         "« Note & données »."))
    crit = d[d["critique"]]
    ht = crit[crit["note"] < crit["note_min"]].sort_values("sensibilite", ascending=False)
    out.append(Tuile("hors_tol", "La note", "Données critiques hors tolérance",
                     f"{len(ht)} sur {len(crit)}", "rouge" if len(ht) else "vert", AIDE["hors_tol"],
                     pd.DataFrame({"Donnée": ht["libelle"], "Propriétaire": ht["proprietaire"],
                                   "Poids dans le SCR": ht["sensibilite"].map(lambda v: p(v, 1)),
                                   "Note": ht["note"].map(p), "Minimum": ht["note_min"].map(p),
                                   "Statut": ht["statut"]}), len(ht)))

    # ---------------------------------------------------------------- les contrôles
    notes = ctrl[ctrl["critique"] & ctrl["inclus_note"]]
    retard = notes[notes["anteriorite"] > 0]
    evalues = ctrl[ctrl["evalue"]]
    rouges, oranges = evalues[evalues["statut"] == "rouge"], evalues[evalues["statut"] == "orange"]
    qrt = ctrl[~ctrl["inclus_note"] & ctrl["evalue"]]
    qrt_ko = qrt[qrt["conforme"] != True]  # noqa: E712 (NaN compris)
    out.append(Tuile("ctrl_notes", "Les contrôles", "Contrôles qui comptent dans la note", str(len(notes)), "bleu",
                     "Contrôles portant sur une donnée critique (hors vérifications QRT).",
                     _liste_controles(notes), len(notes)))
    out.append(Tuile("ctrl_retard", "Les contrôles", "Contrôles en retard", str(len(retard)),
                     "orange" if len(retard) else "vert", AIDE["a_jour"], _liste_controles(retard), len(retard)))
    out.append(Tuile("ctrl_rouges", "Les contrôles", "Contrôles en rouge", str(len(rouges)),
                     "rouge" if len(rouges) else "vert",
                     "Contrôles dont le résultat est nettement sous le seuil (QRT compris).",
                     _liste_controles(rouges), len(rouges)))
    out.append(Tuile("ctrl_oranges", "Les contrôles", "Contrôles en orange", str(len(oranges)),
                     "orange" if len(oranges) else "vert",
                     "Contrôles juste sous leur seuil (moins de 2 points).", _liste_controles(oranges), len(oranges)))
    out.append(Tuile("qrt_ko", "Les contrôles", "États QRT non conformes", f"{len(qrt_ko)} sur {len(qrt)}",
                     "rouge" if len(qrt_ko) else "vert", AIDE["qrt"], _liste_controles(qrt_ko), len(qrt_ko)))
    cv = c["couverture"]
    trous = cv[cv["zone_risque"] & cv["critique"] & ~cv["couvert"]]
    out.append(Tuile("zones", "Les contrôles", "Étapes à risque sans contrôle",
                     f"{g['nb_zones_non_couvertes']} sur {g['nb_zones_risque_critiques']}",
                     "rouge" if len(trous) else "vert", AIDE["zones"],
                     pd.DataFrame({"Flux": trous["flux_id"], "Traitement": trous["traitement"],
                                   "De": trous["systeme_source"], "Vers": trous["systeme_cible"],
                                   "Donnée": trous["libelle_donnee"], "Propriétaire": trous["proprietaire"]}),
                     len(trous)))

    # ---------------------------------------------------------------- les anomalies
    ouv = reg[reg["statut"].isin(["Ouverte", "Récurrente"])]
    en_retard = ouv[pd.to_datetime(ouv["echeance"]) < pd.Timestamp(c["date"])]
    for cle, titre, sel, ton, aide in [
        ("ouvertes", "Anomalies ouvertes", ouv, "orange", AIDE["ouvertes"]),
        ("haute", "Anomalies graves", ouv[ouv["gravite"] == "Haute"], "rouge", AIDE["haute"]),
        ("retard", "Échéance dépassée", en_retard, "rouge", AIDE["retard"]),
        ("recurrentes", "Anomalies récurrentes", ouv[ouv["statut"] == "Récurrente"], "orange",
         "Anomalies déjà présentes à la campagne précédente et toujours pas réglées."),
        ("cloturees", "Anomalies clôturées", reg[reg["statut"] == "Clôturée"], "vert", AIDE["cloturees"]),
    ]:
        n = len(sel)
        ton = ton if (n or cle == "cloturees") else "vert"
        if cle == "cloturees" and n == 0:
            ton = "gris"
        out.append(Tuile(cle, "Les anomalies", titre, str(n), ton, aide, _liste_anomalies(sel), n))
    return out


# ====================================================================== affichage
def afficher_synthese(c: dict, prev: dict | None, xlsx: bytes, aller) -> None:
    """aller(page, **etat) : change de page (fourni par l'application)."""
    import streamlit as st

    @st.dialog("Détail", width="large")
    def detail(t: Tuile) -> None:
        st.markdown(f"### {t.titre} : {t.valeur}")
        st.caption(t.aide)
        if t.liste is None or t.liste.empty:
            st.success("Rien à signaler : la liste est vide.")
        else:
            st.dataframe(t.liste, hide_index=True, width="stretch")
            st.download_button("⬇️ Exporter cette liste (CSV)", t.liste.to_csv(index=False, sep=";").encode("utf-8-sig"),
                               file_name=f"{t.cle}_{c['campagne']}.csv", mime="text/csv")

    ts = tuiles(c, prev)
    principal, actions = st.columns([3.6, 1.4], gap="large")
    with principal:
        for bloc, icone in [("La note", "📊"), ("Les contrôles", "🔍"), ("Les anomalies", "🚩")]:
            st.markdown(f"#### {icone} Synthèse — {bloc.lower()}")
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
    with actions:
        st.markdown('<div class="qdd-actions-titre">ACTIONS</div>', unsafe_allow_html=True)
        for libelle, page, etat in [
            ("Voir les données hors tolérance", "donnees", {}),
            ("Voir les contrôles en rouge", "controles", {"filtre_controles": ["rouge"]}),
            ("Voir les contrôles en retard", "controles", {"filtre_controles": ["en retard"]}),
            ("Voir les anomalies ouvertes", "anomalies", {}),
            ("Voir les étapes sans contrôle", "lignage", {}),
            ("Comprendre d'où sortent les chiffres", "comprendre", {}),
        ]:
            if st.button(f"→ {libelle}", key=f"action_{page}_{libelle}", type="tertiary"):
                aller(page, **etat)
        st.divider()
        reg = c["registre"]
        st.download_button("⬇️ Exporter le registre des anomalies", _liste_anomalies(reg).to_csv(index=False, sep=";")
                           .encode("utf-8-sig"), file_name=f"registre_anomalies_{c['campagne']}.csv",
                           mime="text/csv", type="tertiary")
        ko = c["controles"][c["controles"]["statut"].isin(["rouge", "orange"])]
        st.download_button("⬇️ Exporter les contrôles en anomalie", _liste_controles(ko).to_csv(index=False, sep=";")
                           .encode("utf-8-sig"), file_name=f"controles_en_anomalie_{c['campagne']}.csv",
                           mime="text/csv", type="tertiary")
        st.download_button("⬇️ Rapport Excel complet", xlsx, file_name="rapport_qdd.xlsx", type="tertiary",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.caption("Cliquez sur ↗ dans une tuile pour voir la liste qui la compose, et l'exporter.")
