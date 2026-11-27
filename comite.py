"""Dossier de comité en un clic : le document à apporter au comité QDD, produit par le moteur.

Tout chiffre vient des sorties du moteur pour la campagne affichée (indicateurs, variation, données critiques,
points de contrôle, registre, contrôle de niveau 2, manifeste des données en défaut). Les « points à arbitrer » sont
proposés par des règles écrites ci-dessous ; la décision, et le compte rendu, restent au comité.
"""
from __future__ import annotations

import pandas as pd

from relances import DEPASSEE, RETARD, relances, synthese

STATUTS = {"vert": "Conforme", "orange": "À corriger", "rouge": "Bloquant"}
SEUIL_LINEARITE = 0.10
GRAVITE = {"rouge": 0, "orange": 1}
ENTETE = "ATELIER QDD · DOSSIER DE COMITÉ"
PIED = "Données 100 % fictives · dossier généré par le moteur de l'Atelier QDD ; décisions réservées au comité"


def _periodes(n) -> str:
    n = int(n)
    return f"{n} période{'s' if n > 1 else ''}"


def _par_gravite(d: pd.DataFrame) -> pd.DataFrame:
    """Bloquant avant À corriger, puis le plus grand écart au minimum d'abord."""
    return d.assign(_g=d["statut"].map(GRAVITE), _e=d["note"] - d["note_min"]).sort_values(["_g", "_e"])


def _pct(x, d: int = 2) -> str:
    return "—" if x is None or pd.isna(x) else f"{x * 100:.{d}f} %".replace(".", ",")


def _pts(x) -> str:
    return "—" if x is None or pd.isna(x) else f"{x * 100:+.2f} pt".replace(".", ",")


def _date(x) -> str:
    return pd.Timestamp(x).strftime("%d/%m/%Y")


def _table(entetes: list[str], lignes: list[list]) -> list[str]:
    if not lignes:
        return []
    return (["| " + " | ".join(entetes) + " |", "|" + "---|" * len(entetes)]
            + ["| " + " | ".join(str(v).replace("|", "·") for v in l) + " |" for l in lignes] + [""])


def _empreinte(campagne: str) -> str | None:
    try:
        from archives_defaut import lire_manifeste
        return next((a["sha256"] for a in lire_manifeste()["archives"] if a["campagne"] == campagne), None)
    except Exception:  # noqa: BLE001 — l'empreinte est un complément, son absence est dite dans le document
        return None


def points_a_arbitrer(c: dict) -> list[str]:
    """Propositions tirées de règles écrites, dans l'ordre : données critiques, restitutions QRT, contrôles en
    retard bloquants, zones non couvertes, sensibilités non linéaires."""
    points = []
    d = c["donnees"]
    for r in _par_gravite(d[d["critique"].astype(bool) & d["statut"].isin(["orange", "rouge"])]).itertuples():
        points.append(f"Plan de correction pour **{r.libelle}** ({STATUTS[r.statut]} : note {_pct(r.note)} pour un "
                      f"minimum de {_pct(r.note_min)}) — {r.proprietaire}.")
    ct = c["controles"]
    qrt = ct[ct["seuil_fixe"].notna() & (ct["statut"] == "rouge")]
    for r in qrt.itertuples():
        points.append(f"Valider la correction de la restitution **{r.controle_id.replace('|', ' · ')}** avant la remise "
                      f"({_pct(r.resultat)} pour un seuil fixe de {_pct(r.seuil)}) — {r.responsable}.")
    for r in ct[(ct["anteriorite"].fillna(0) > 0) & (ct["statut"] == "rouge")].itertuples():
        points.append(f"Fixer une date de réalisation pour **{r.controle_id.replace('|', ' · ')}**, bloquant faute "
                      f"d'avoir été refait ({_periodes(r.anteriorite)} de retard) — {r.responsable}.")
    g = c["gouv"]
    if g.get("nb_zones_non_couvertes"):
        points.append(f"Décider des contrôles à créer pour les **{g['nb_zones_non_couvertes']} zones de risque "
                      f"critiques** sans contrôle (flux {', '.join(g.get('flux_non_couverts', []))}).")
    if "non_linearite" in d:
        for r in d[d["critique"].astype(bool) & (d["non_linearite"] > SEUIL_LINEARITE)].itertuples():
            points.append(f"Choisir la sensibilité retenue pour **{r.libelle}** : écart de linéarité "
                          f"{_pct(r.non_linearite)}, au-dessus de {_pct(SEUIL_LINEARITE, 0)}.")
    return points


def _section_gains(gains: pd.DataFrame | None, par_donnee: pd.DataFrame | None) -> list[str]:
    """Ce que rapporteraient les corrections (gain.py) : par donnée hors tolérance, puis les 5 meilleurs points."""
    if gains is None or gains.empty:
        return []
    l = ["## 8. Ce que rapporteraient les corrections", "",
         "*Recalcul du moteur sur une copie : « refait » = même résultat sans pénalité de retard ; « corrigé » = "
         "résultat porté à 100 %.*", ""]
    if par_donnee is not None and len(par_donnee):
        l += _table(["Donnée", "Hypothèse", "Statut de la donnée", "Note QDD après", "Gain"],
                    [[r.donnee, r.hypothese, f"{r.statut_avant} → {r.statut_apres}" if r.statut_avant != "—" else "—",
                      _pct(r.note_apres), _pts(r.gain_points / 100)] for r in par_donnee.itertuples()])
    top = gains[gains["gain_points"] > 0.005].head(5)
    l += _table(["Point", "Hypothèse", "Gain", "Responsable"],
                [[r.point.replace("|", " · "), r.hypothese, _pts(r.gain_points / 100), r.responsable]
                 for r in top.itertuples()])
    nuls = gains[(gains["gain_points"] <= 0.005) & (gains["hypothese"] == "Corrigé et refait")]["point"].nunique()
    if nuls:
        l += [f"{nuls} points corrigés ne changeraient pas la note (données non critiques ou restitutions QRT, hors "
              "note) : à traiter quand même, sans en attendre d'effet sur la note.", ""]
    return l


def markdown_comite(c: dict, prev: dict | None = None, var: pd.DataFrame | None = None, genere_le=None,
                    gains: pd.DataFrame | None = None, par_donnee: pd.DataFrame | None = None) -> str:
    """Le dossier de comité en Markdown (mis en page en PDF par export_pdf)."""
    ind, g, d, ct = c["ind"], c["gouv"], c["donnees"], c["controles"]
    genere_le = pd.Timestamp.now() if genere_le is None else pd.Timestamp(genere_le)
    crit = d[d["critique"].astype(bool)]
    hors = _par_gravite(crit[crit["statut"].isin(["orange", "rouge"])])
    nb_qrt = int(ind["nb_controles_restitution"])
    qrt_ok = round(ind["taux_conformite_restitutions"] * nb_qrt)
    l = [f"# Comité qualité des données — campagne {c['campagne']}", "",
         f"*Arrêté du {_date(c['date'])} · dossier généré le {genere_le:%d/%m/%Y} par l'Atelier QDD à partir "
         "du moteur · données fictives*", "",
         "## 1. Où en est-on", ""]
    atteint = ind["note"] >= ind["note_min"]
    l += [f"- **Note QDD : {_pct(ind['note'])}** pour un objectif de {_pct(ind['note_min'])} : objectif "
          f"{'atteint' if atteint else 'non atteint'} ({_pts(ind['note'] - ind['note_min'])})."
          + (f" Campagne précédente ({prev['campagne']}) : {_pct(prev['ind']['note'])}." if prev else ""),
          f"- **Données critiques hors tolérance : {int(ind['nb_donnees_hors_tolerance'])} sur "
          f"{int(ind['nb_donnees_critiques'])}.**",
          f"- **Restitutions QRT conformes : {qrt_ok} sur {nb_qrt}** (suivies à part, hors note).",
          f"- **Zones de risque couvertes : {g['nb_zones_risque_critiques'] - g['nb_zones_non_couvertes']} sur "
          f"{g['nb_zones_risque_critiques']}.**",
          f"- **Anomalies ouvertes : {g['nb_anomalies_ouvertes']}**, dont {g['nb_anomalies_haute']} de gravité haute, "
          f"{g['nb_anomalies_recurrentes']} récurrentes, {g['nb_anomalies_en_retard']} à échéance dépassée ; "
          f"{g['nb_anomalies_cloturees']} clôturées au registre.", ""]
    if var is not None and not var.empty and prev is not None:
        etapes = var[var["impact"].notna() & (var["impact"].abs() >= 0.00005)]
        l += [f"## 2. Pourquoi la note a bougé depuis {prev['campagne']}", ""]
        l += _table(["Facteur", "Effet"], [[r.etape, _pts(r.impact)] for r in etapes.itertuples()])
        l += ["Les autres facteurs (ajout ou retrait de contrôles et de données critiques, pondération) sont sans "
              "effet sur cette campagne.", ""]
    l += ["## 3. Données critiques hors tolérance", ""]
    l += _table(["Donnée", "Note", "Minimum", "Écart", "Statut", "Propriétaire"],
                [[r.libelle, _pct(r.note), _pct(r.note_min), _pts(r.note - r.note_min), STATUTS[r.statut],
                  r.proprietaire] for r in hors.itertuples()]) or ["Aucune.", ""]
    qrt = ct[ct["seuil_fixe"].notna() & (ct["statut"] != "vert")]
    l += ["## 4. Restitutions QRT non conformes", ""]
    l += _table(["Point", "Contrôle", "Résultat", "Seuil fixe", "Responsable"],
                [[r.controle_id.replace("|", " · "), r.libelle, _pct(r.resultat), _pct(r.seuil), r.responsable]
                 for r in qrt.itertuples()]) or ["Aucune.", ""]
    retard = ct[ct["anteriorite"].fillna(0) > 0]
    l += ["## 5. Contrôles non refaits dans leur périodicité", ""]
    l += _table(["Point", "Dernière réalisation", "Retard", "Résultat retenu", "Seuil", "Statut", "Responsable"],
                [[r.controle_id.replace("|", " · "), _date(r.date_derniere_real), _periodes(r.anteriorite),
                  _pct(r.resultat), _pct(r.seuil), STATUTS.get(r.statut, "Non noté"), r.responsable]
                 for r in retard.itertuples()]) or ["Aucun.", ""]
    if len(retard):
        l += ["Le résultat retenu est le dernier connu, réduit de 5 % par période de retard.", ""]
    rel = relances(c)
    syn = synthese(rel)
    l += ["## 6. Qui doit agir", ""]
    l += _table(["Responsable", "Échéances dépassées", "Contrôles à refaire", "Total des points"],
                [[r.responsable, r[1], r[2], r.total] for r in syn.itertuples(index=False)]) or ["Personne.", ""]
    haute = c["registre"]
    haute = haute[haute["statut"].isin(["Ouverte", "Récurrente"]) & (haute["gravite"] == "Haute")]
    if len(haute):
        l += ["Anomalies de gravité haute :", ""]
        l += _table(["Anomalie", "Objet", "Propriétaire", "Échéance", "Statut"],
                    [[r.anomalie_id, str(r.objet).replace("|", " · "), r.proprietaire, _date(r.echeance), r.statut]
                     for r in haute.itertuples()])
    n2 = c.get("niveau2")
    if n2 is not None and len(n2):
        l += ["## 7. Contrôle de niveau 2", ""]
        l += _table(["Constat", "Valeur", "Appréciation"],
                    [[r.indicateur, r.valeur, STATUTS.get(r.statut, r.statut)] for r in n2.itertuples()])
    gains_md = _section_gains(gains, par_donnee)
    l += gains_md
    n_arb, n_dec = (9, 10) if gains_md else (8, 9)
    l += [f"## {n_arb}. Points à arbitrer", "",
          "*Proposés par l'application à partir des règles du dispositif ; la décision revient au comité.*", ""]
    l += [f"{i}. {p}" for i, p in enumerate(points_a_arbitrer(c), 1)] or ["Aucun."]
    l += ["", f"## {n_dec}. Décisions du comité", "", "*À compléter en séance.*", ""]
    l += [f"{i}. Décision : {'.' * 60}  Responsable : {'.' * 28}  Échéance : {'.' * 14}"
          for i in range(1, 5)] + [""]
    emp = _empreinte(c["campagne"])
    l += ["## Preuves", "",
          "- Données en défaut de la campagne conservées et figées : empreinte SHA-256 "
          + (f"`{emp}`." if emp else "non disponible pour cette campagne."),
          "- Détail complet dans l'Atelier QDD : Synthèse, Contrôles, Anomalies, Relances, Dossier de campagne "
          "(ZIP de preuves avec manifeste).",
          "- Prototype sur données fictives : ce dossier ne vaut pas attestation de conformité.", ""]
    return "\n".join(l)


def pdf_comite(md: str, titre: str) -> bytes:
    import streamlit as st

    from export_pdf import pdf_depuis_markdown

    @st.cache_data(max_entries=20, show_spinner=False)
    def _fabriquer(texte: str, t: str) -> bytes:
        return pdf_depuis_markdown(texte, t, ENTETE, PIED)
    return _fabriquer(md, titre)


def afficher(c: dict, prev: dict | None, var: pd.DataFrame | None) -> None:
    import streamlit as st

    with st.container(border=True, key="qdd_comite"):
        g, d = st.columns([3, 2], vertical_alignment="center")
        g.markdown("**Dossier de comité** · note et variation, données hors tolérance, restitutions QRT, contrôles "
                   "en retard, qui doit agir, niveau 2, points à arbitrer, preuves. Généré par le moteur pour la "
                   "campagne affichée.")
        from gain import par_donnee, simulations

        @st.cache_data(show_spinner="Préparation du dossier de comité…", max_entries=12)
        def _gains(campagne: str, _c: dict, _p, cle: str):
            return simulations(_c, _p), par_donnee(_c, _p)
        gains, pdn = _gains(c["campagne"], c, c["params"], repr(c["params"])) if c.get("params") else (None, None)
        md = markdown_comite(c, prev, var, genere_le=pd.Timestamp.now().normalize(), gains=gains,
                             par_donnee=pdn)  # date du jour : contenu stable dans la journée
        titre = f"Comité QDD — campagne {c['campagne']}"
        b1, b2 = d.columns(2)
        b1.download_button("PDF", pdf_comite(md, titre), file_name=f"dossier_comite_{c['campagne']}.pdf",
                           mime="application/pdf", icon=":material/picture_as_pdf:", type="primary",
                           width="stretch", key="comite_pdf")
        b2.download_button("Markdown", md.encode("utf-8"), file_name=f"dossier_comite_{c['campagne']}.md",
                           mime="text/markdown", icon=":material/description:", width="stretch", key="comite_md")
