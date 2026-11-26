"""Relances aux propriétaires : pour chaque responsable, ce qui lui revient et un message prêt à envoyer.

Deux sources, déjà calculées par le moteur :
- le registre des anomalies non clôturées (échéance comparée à la date d'arrêté, comme la tuile de la Synthèse) ;
- les points de contrôle non refaits dans leur périodicité (antériorité > 0), pénalisés de 5 % par période.
Rien n'est envoyé : l'application prépare le message, le chargé QDD le relit et l'envoie lui-même.
"""
from __future__ import annotations

import re
from html import escape

import pandas as pd

DEPASSEE, BIENTOT, RETARD, A_VENIR = ("Échéance dépassée", "Échéance dans les 30 jours", "Contrôle à refaire",
                                      "À venir")
ORDRE_URGENCE = {DEPASSEE: 0, RETARD: 1, BIENTOT: 2, A_VENIR: 3}
ORDRE_GRAVITE = {"Haute": 0, "Moyenne": 1, "Basse": 2}
STATUTS = {"vert": "Conforme", "orange": "À corriger", "rouge": "Bloquant"}
JOURS_PROCHE = 30


def _pct(x) -> str:
    return "—" if pd.isna(x) else f"{x * 100:.2f} %".replace(".", ",")


_LIBELLES = {DEPASSEE: ("échéance dépassée", "échéances dépassées"), RETARD: ("contrôle à refaire", "contrôles à refaire"),
             BIENTOT: ("échéance dans les 30 jours", "échéances dans les 30 jours"), A_VENIR: ("à venir", "à venir")}


def _compte(urgence: str, n: int) -> str:
    return f"{n} {_LIBELLES[urgence][n > 1]}"


def _fr(texte: str) -> str:
    """Nombres du registre écrits à la française : 94.59% → 94,59 %."""
    return re.sub(r"(\d+)\.(\d+)\s?%", r"\1,\2 %", str(texte))


def _date(x) -> str:
    return "—" if pd.isna(x) else pd.Timestamp(x).strftime("%d/%m/%Y")


def relances(camp: dict) -> pd.DataFrame:
    """Une ligne par point à relancer, triée par responsable puis urgence et gravité."""
    arrete = pd.Timestamp(camp["date"])
    lignes = []
    reg = camp["registre"]
    for a in reg[reg["statut"].isin(["Ouverte", "Récurrente"])].itertuples():
        ech = pd.Timestamp(a.echeance)
        jours = (ech - arrete).days
        urgence = DEPASSEE if jours < 0 else BIENTOT if jours <= JOURS_PROCHE else A_VENIR
        lignes.append({"responsable": a.proprietaire, "urgence": urgence, "reference": a.anomalie_id,
                       "nature": f"Anomalie · {a.type}", "objet": str(a.objet).replace("|", " · "),
                       "gravite": a.gravite, "echeance": ech, "statut": a.statut,
                       "constat": a.constat, "action": a.action_attendue})
    ct = camp["controles"]
    for p in ct[ct["anteriorite"].fillna(0) > 0].itertuples():
        n = int(p.anteriorite)
        statut = STATUTS.get(p.statut, "Non noté")
        lignes.append({"responsable": p.responsable, "urgence": RETARD, "reference": p.controle_id.replace("|", " · "),
                       "nature": "Contrôle à refaire", "objet": p.libelle, "gravite": statut, "echeance": pd.NaT,
                       "statut": f"{n} période{'s' if n > 1 else ''} de retard",
                       "constat": (f"Non refait depuis le {_date(p.date_derniere_real)} ; résultat retenu "
                                   f"{_pct(p.resultat)} pour un seuil de {_pct(p.seuil)} ({statut}), réduit de 5 % "
                                   "par période de retard."),
                       "action": f"Refaire le contrôle sur l'arrêté du {_date(arrete)} et transmettre le résultat."})
    df = pd.DataFrame(lignes, columns=["responsable", "urgence", "reference", "nature", "objet", "gravite", "echeance",
                                       "statut", "constat", "action"])
    if df.empty:
        return df
    df["_u"] = df["urgence"].map(ORDRE_URGENCE)
    df["_g"] = df["gravite"].map(ORDRE_GRAVITE).fillna(9)
    return df.sort_values(["responsable", "_u", "_g", "reference"]).drop(columns=["_u", "_g"]).reset_index(drop=True)


def synthese(df: pd.DataFrame) -> pd.DataFrame:
    """Par responsable : nombre de points par urgence, du plus chargé au moins chargé."""
    if df.empty:
        return pd.DataFrame(columns=["responsable", DEPASSEE, RETARD, BIENTOT, A_VENIR, "total"])
    t = pd.crosstab(df["responsable"], df["urgence"]).reindex(columns=list(ORDRE_URGENCE), fill_value=0)
    t["total"] = t.sum(axis=1)
    return t.sort_values([DEPASSEE, RETARD, "total"], ascending=False).reset_index()


def message(responsable: str, df: pd.DataFrame, campagne: str, date) -> str:
    """Le message à envoyer à un responsable : ses points, du plus urgent au moins urgent, et ce qui est attendu."""
    d = df[df["responsable"] == responsable]
    lignes = [f"Objet : Qualité des données – campagne {campagne} (arrêté du {_date(date)}) – points à traiter", "",
              "Bonjour,", "",
              f"Dans le cadre de la campagne de qualité des données {campagne} (arrêté du {_date(date)}), voici les "
              f"points qui relèvent de : {responsable}.", ""]
    for urgence in ORDRE_URGENCE:
        bloc = d[d["urgence"] == urgence]
        if bloc.empty:
            continue
        titre = {DEPASSEE: "Anomalies dont l'échéance est dépassée", RETARD: "Contrôles à refaire",
                 BIENTOT: f"Anomalies à traiter dans les {JOURS_PROCHE} jours", A_VENIR: "Pour information"}[urgence]
        lignes.append(f"{titre} ({len(bloc)}) :")
        for r in bloc.itertuples():
            if r.nature == "Contrôle à refaire":
                lignes.append(f"- {r.reference} – {r.objet} : {r.constat}")
            else:
                lignes.append(f"- {r.reference} ({r.objet}, gravité {str(r.gravite).lower()}, échéance "
                              f"{_date(r.echeance)}) : {_fr(r.constat).rstrip('.')}. Action attendue : "
                              f"{_fr(r.action).rstrip('.')}.")
        lignes.append("")
    lignes += ["Les corrections de données passent par l'Atelier de résolution (correction sur copie, nouveau "
               "contrôle, validation par une autre personne). Une anomalie n'est clôturée qu'une fois le contrôle "
               "refait dans la campagne et revenu conforme.", "",
               "Pouvez-vous me confirmer une date de traitement pour chacun de ces points ?", "",
               "Bien cordialement,", "[Nom] – Qualité des données"]
    return "\n".join(lignes)


def tous_les_messages(df: pd.DataFrame, campagne: str, date) -> str:
    return ("\n\n" + "=" * 80 + "\n\n").join(message(r, df, campagne, date) for r in synthese(df)["responsable"])


def afficher(c: dict) -> None:
    import streamlit as st

    df = relances(c)
    if df.empty:
        st.success("Rien à relancer : aucune anomalie ouverte ni aucun contrôle en retard sur cette campagne.")
        return
    syn = synthese(df)
    tuiles = [("Responsables à relancer", syn["responsable"].nunique(), ""),
              ("Échéances dépassées", int((df["urgence"] == DEPASSEE).sum()), "Anomalies, à la date d'arrêté."),
              ("Contrôles à refaire", int((df["urgence"] == RETARD).sum()), "Points de contrôle non refaits dans "
               "leur périodicité."),
              ("Échéances sous 30 jours", int((df["urgence"] == BIENTOT).sum()), "Anomalies à traiter dans les 30 "
               "jours suivant l'arrêté.")]
    for col, (titre, valeur, aide) in zip(st.columns(4), tuiles):
        col.metric(titre, valeur, help=aide or None, border=True)
    st.caption(f"Échéances comparées à la date d'arrêté ({_date(c['date'])}), comme sur la Synthèse. Un contrôle à "
               "refaire peut aussi figurer au registre (anomalie « Contrôle non réalisé ») : les deux sont listés, "
               "le contrôle pour le planifier, l'anomalie pour la suivre.")
    g, d = st.columns(2)
    g.download_button("Tous les messages (.txt)", tous_les_messages(df, c["campagne"], c["date"]).encode("utf-8"),
                      file_name=f"relances_{c['campagne']}.txt", mime="text/plain", icon=":material/mail:",
                      width="stretch", key="relances_tous")
    export = df.assign(echeance=df["echeance"].map(_date))
    d.download_button("Liste des points (CSV)", export.to_csv(index=False, sep=";").encode("utf-8-sig"),
                      file_name=f"relances_{c['campagne']}.csv", mime="text/csv", icon=":material/download:",
                      width="stretch", key="relances_csv")
    for r in syn.itertuples(index=False):
        resp = r.responsable
        compte = " · ".join(_compte(u, n) for u, n in ((DEPASSEE, r[1]), (RETARD, r[2]), (BIENTOT, r[3]),
                                                       (A_VENIR, r[4])) if n)
        with st.expander(f"**{escape(resp)}** — {compte}", expanded=False):
            d_r = df[df["responsable"] == resp]
            st.dataframe(d_r.assign(echeance=d_r["echeance"].map(_date)), hide_index=True, width="stretch",
                         column_order=["urgence", "reference", "nature", "objet", "gravite", "echeance", "statut",
                                       "action"],
                         column_config={"urgence": "Urgence", "reference": "Référence", "nature": "Nature",
                                        "objet": "Objet", "gravite": "Gravité / statut", "echeance": "Échéance",
                                        "statut": "État", "action": "Action attendue"})
            st.markdown("**Message prêt à envoyer** · copiez-le avec l'icône en haut à droite, relisez, envoyez.")
            texte = message(resp, df, c["campagne"], c["date"])
            st.code(texte, language=None, wrap_lines=True)
            st.download_button("Télécharger ce message", texte.encode("utf-8"), file_name=(
                f"relance_{c['campagne']}_{resp.replace(' ', '_')}.txt"), mime="text/plain",
                icon=":material/download:", key=f"relance_dl_{resp}", type="tertiary")
