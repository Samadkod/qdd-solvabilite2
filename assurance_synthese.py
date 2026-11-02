"""Présentation assurance ; calcul des tuiles importé du module original."""
from __future__ import annotations
from html import escape
import pandas as pd
from synthese import Tuile, tuiles, evolutions, COULEURS, BLOCS, CHARGEMENT, _liste_anomalies, _liste_controles

def afficher_synthese(c: dict, prev: dict | None, xlsx: bytes, aller, df_lignes: pd.DataFrame | None = None,
                      volumes: pd.DataFrame | None = None, execution: pd.DataFrame | None = None,
                      precedentes: list[Tuile] | None = None, base=None, methode=None) -> None:
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
    par_cle = {t.cle: t for t in ts}

    def section(titre: str, contexte: str) -> None:
        st.markdown(f'<div class="qdd-section"><h2>{escape(titre)}</h2><span>{escape(contexte)}</span></div>',
                    unsafe_allow_html=True)

    def cartes(groupe: list[Tuile]) -> None:
        statuts = {"vert": "Conforme", "rouge": "Vigilance prioritaire", "orange": "À suivre",
                   "gris": "Repère", "bleu": "Périmètre"}
        for i in range(0, len(groupe), 3):
            cols = st.columns(3, gap="medium")
            for col, t in zip(cols, groupe[i:i + 3]):
                with col, st.container(border=True, key=f"qdd_card_{t.cle}"):
                    st.markdown(f'<div class="qdd-card-meta" style="--status:{COULEURS[t.ton]}">'
                                f'{statuts[t.ton]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="qdd-tuile-titre">{escape(t.titre)}</div>',
                                unsafe_allow_html=True, help=t.aide)
                    st.markdown(f'<div class="qdd-tuile-valeur" style="color:{COULEURS[t.ton]}">'
                                f'{escape(t.valeur)}</div>', unsafe_allow_html=True)
                    delta = escape(t.delta) if t.delta else "&nbsp;"
                    st.markdown(f'<div class="qdd-tuile-delta" style="color:{COULEURS[t.delta_ton]}">'
                                f'{delta}</div>', unsafe_allow_html=True)
                    if t.liste is not None:
                        if st.button("Voir le détail ↗", key=f"tuile_{t.cle}",
                                     help=t.aide, type="tertiary", width="stretch"):
                            detail(t)

    section("Vue d’ensemble", "Les indicateurs clés de la campagne")
    majeures = {"note", "hors_tol", "ouvertes"}
    cartes([par_cle[k] for k in ("note", "hors_tol", "ouvertes")])

    # Lecture exécutive dérivée des tuiles existantes, sans nouvelle règle de notation.
    n_crit = par_cle["hors_tol"].nombre or 0
    n_graves = par_cle["haute"].nombre or 0
    n_retard = par_cle["retard"].nombre or 0
    n_qrt = par_cle["qrt_ko"].nombre or 0
    conforme = c["ind"]["note"] >= c["ind"]["note_min"]
    attention = any((n_crit, n_graves, n_retard, n_qrt))
    bilan = "Objectif global atteint" if conforme else "Objectif global non atteint"
    if attention:
        lecture = (f'<b>{bilan} — des points de vigilance restent à traiter.</b><br>'
                   f'<strong>{n_crit}</strong> donnée(s) critique(s) hors tolérance · '
                   f'<strong>{n_qrt}</strong> restitution(s) QRT non conforme(s) · '
                   f'<strong>{n_graves}</strong> anomalie(s) grave(s) · '
                   f'<strong>{n_retard}</strong> échéance(s) dépassée(s). '
                   'La note agrégée ne remplace pas la revue des risques individuels.')
    else:
        lecture = f'<b>{bilan}.</b> Aucun point de vigilance dans ces quatre catégories.'
    st.markdown(f'<div class="qdd-summary{"" if attention else " qdd-summary-ok"}">{lecture}</div>',
                unsafe_allow_html=True)

    # Actions conservées avec les mêmes clés et les mêmes filtres de navigation.
    with st.expander("Agir sur les points de vigilance", icon=":material/arrow_forward:", expanded=True):
        actions = [
            ("Voir les données hors tolérance", "donnees", {}),
            ("Voir les contrôles bloquants", "controles", {"filtre_controles": ["rouge"]}),
            ("Voir les anomalies ouvertes", "anomalies", {}),
        ]
        for col, (libelle, page, etat) in zip(st.columns(3), actions):
            if col.button(libelle, key=f"action_{page}_{libelle}", width="stretch"):
                aller(page, **etat)

    if df_lignes is not None:
        from operations_qdd.ui import afficher_diagnostic
        afficher_diagnostic(c, prev, df_lignes, aller)

    titres = {
        "La note": ("Performance de la qualité", "Objectif et évolution de la note"),
        "Les contrôles": ("Contrôles & restitutions réglementaires", "Résultats, retards et couverture des risques"),
        "Les anomalies": ("Suivi des anomalies", "Gravité, échéances et cycle de vie"),
        CHARGEMENT: ("Fiabilité de l’exploitation", "Chargement des sources et exécution technique"),
    }
    for bloc, _ in BLOCS:
        groupe = [t for t in ts if t.bloc == bloc and t.cle not in majeures]
        if groupe:
            section(*titres[bloc])
            cartes(groupe)

    if df_lignes is not None and not df_lignes.empty:
        from lignes_anomalie import regroupements
        section("Où concentrer les corrections ?", "Les 5 messages les plus fréquents")
        top = regroupements(df_lignes).head(5)
        st.dataframe(top[["Contrôle", "Message", "Lignes en anomalie", "Part"]], hide_index=True, width="stretch",
                     column_config={"Contrôle": st.column_config.TextColumn(width="small"),
                                    "Message": st.column_config.TextColumn(width="large"),
                                    "Lignes en anomalie": st.column_config.NumberColumn("Lignes", width="small"),
                                    "Part": st.column_config.ProgressColumn(format="%.1f %%", min_value=0,
                                                                             max_value=100, width="small")})
        st.caption("Priorisation de Pareto : la part correspond aux lignes du message divisées par le total "
                   "des lignes en anomalie de cohérence. Elle ne mesure pas la gravité métier.")

    with st.expander("Autres actions & accès rapides", icon=":material/apps:"):
        for libelle, page, etat in [
            ("Voir les contrôles en retard", "controles", {"filtre_controles": ["en retard"]}),
            ("Voir les lignes en anomalie", "lignes", {}),
            ("Voir les règles de contrôle", "regles", {}),
            ("Voir le chargement et l'exécution", "chargement", {}),
            ("Voir les étapes sans contrôle", "lignage", {}),
            ("Comprendre d'où sortent les chiffres", "comprendre", {}),
        ]:
            if st.button(f"→ {libelle}", key=f"action_{page}_{libelle}", type="tertiary"):
                aller(page, **etat)

    section("Exports de la campagne", "Des livrables pour documenter et partager la revue")
    with st.container(border=True):
        reg = c["registre"]
        cols = st.columns(3)
        cols[0].download_button("Registre des anomalies · CSV", icon=":material/download:", data=_liste_anomalies(reg).to_csv(index=False, sep=";")
                           .encode("utf-8-sig"), file_name=f"registre_anomalies_{c['campagne']}.csv",
                           mime="text/csv", width="stretch")
        ko = c["controles"][c["controles"]["statut"].isin(["rouge", "orange"])]
        cols[1].download_button("Contrôles en anomalie · CSV", icon=":material/download:", data=_liste_controles(ko).to_csv(index=False, sep=";")
                           .encode("utf-8-sig"), file_name=f"controles_en_anomalie_{c['campagne']}.csv",
                           mime="text/csv", width="stretch")
        cols[2].download_button("Rapport complet · Excel", xlsx, icon=":material/download:", file_name="rapport_qdd.xlsx", type="primary", width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if base is not None and methode is not None:
        from operations_qdd.ui import afficher_dossier
        afficher_dossier(c, prev, df_lignes, volumes, execution, xlsx, base, methode)
    st.markdown('<div class="qdd-footer">Démonstration sur un assureur dommages BTP fictif. '
                'SCR simplifié, non réglementaire ; QRT simplifiés, hors taxonomie EIOPA. '
                'Méthode C. Motard (ISFA / Grant Thornton, 2024), corrigée.<br>'
                'Les évolutions sont comparées à la campagne précédente. Les couleurs indiquent le sens '
                'de l’évolution ; les détails restent accessibles depuis chaque indicateur.</div>',
                unsafe_allow_html=True)
