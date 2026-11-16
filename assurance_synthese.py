"""Présentation assurance ; calcul des tuiles importé du module original."""
from __future__ import annotations
from html import escape
import pandas as pd
from langue import t as tr
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
        st.markdown(f'<div class="qdd-section"><h2>{escape(tr(titre))}</h2><span>{escape(tr(contexte))}</span></div>',
                    unsafe_allow_html=True)

    def cartes(groupe: list[Tuile]) -> None:
        statuts = {"vert": "Conforme", "rouge": "Vigilance prioritaire", "orange": "À suivre",
                   "gris": "Repère", "bleu": "Périmètre"}
        for i in range(0, len(groupe), 3):
            cols = st.columns(3, gap="medium")
            for col, t in zip(cols, groupe[i:i + 3]):
                with col, st.container(border=True, key=f"qdd_card_{t.cle}"):
                    st.markdown(f'<div class="qdd-card-meta" data-ton="{t.ton}" style="--status:{COULEURS[t.ton]}">'
                                f'{tr(statuts[t.ton])}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="qdd-tuile-titre">{escape(tr(t.titre))}</div>',
                                unsafe_allow_html=True, help=t.aide)
                    st.markdown(f'<div class="qdd-tuile-valeur" style="color:{COULEURS[t.ton]}">'
                                f'{escape(tr(t.valeur))}</div>', unsafe_allow_html=True)
                    delta = escape(tr(t.delta)) if t.delta else "&nbsp;"
                    st.markdown(f'<div class="qdd-tuile-delta" style="color:{COULEURS[t.delta_ton]}">'
                                f'{delta}</div>', unsafe_allow_html=True)
                    if t.liste is not None:
                        if st.button(tr("Voir le détail ↗"), key=f"tuile_{t.cle}",
                                     help=t.aide, type="tertiary", width="stretch"):
                            detail(t)

    ind = c["ind"]
    note, objectif = ind["note"], ind["note_min"]
    n1 = prev["ind"]["note"] if prev is not None else None

    def pct(v: float, d: int = 2) -> str:
        return f"{v * 100:.{d}f}".replace(".", ",")

    # ---------- 1. Verdict : note, objectif et N-1 sur une même règle ----------
    valeurs = [v for v in (note, objectif, n1) if v is not None]
    bas = min(int(min(valeurs) * 100) - 1, 95) / 100
    pos = lambda v: max(0.0, min(100.0, (v - bas) / (1 - bas) * 100))
    conforme = note >= objectif
    marge = (note - objectif) * 100
    marge_txt = ("+" if marge >= 0 else "−") + f"{abs(marge):.2f}".replace(".", ",")
    repere_n1 = (f'<span class="qdd-regle-n1" style="left:{pos(n1):.2f}%" title="N-1"></span>' if n1 is not None else "")
    legende_n1 = f' · <span class="qdd-leg-n1"></span>{tr("N-1")} {pct(n1)} %' if n1 is not None else ""
    delta_note = par_cle["note"].delta or ""
    st.markdown(
        f'''<div class="qdd-verdict {"ok" if conforme else "ko"}">
  <div class="qdd-verdict-gauche">
    <div class="qdd-verdict-etat">{tr("Objectif global atteint" if conforme else "Objectif global non atteint")}</div>
    <div class="qdd-verdict-note">{pct(note)}<span> %</span></div>
    <div class="qdd-verdict-libelle">{tr("Note QDD agrégée")} ·
      <span style="color:{COULEURS[par_cle["note"].delta_ton]}">{escape(tr(delta_note))}</span></div>
  </div>
  <div class="qdd-verdict-droite">
    <div class="qdd-regle"><span class="qdd-regle-zone" style="left:{pos(objectif):.2f}%"></span>
      <span class="qdd-regle-obj" style="left:{pos(objectif):.2f}%"></span>{repere_n1}
      <span class="qdd-regle-note" style="left:{pos(note):.2f}%"></span></div>
    <div class="qdd-regle-echelle"><span>{pct(bas, 0)} %</span><span>100 %</span></div>
    <div class="qdd-regle-legende"><span class="qdd-leg-note"></span>{tr("Note")} {pct(note)} % ·
      <span class="qdd-leg-obj"></span>{tr("Objectif")} {pct(objectif)} %{legende_n1}</div>
    <p><b>{marge_txt} pt</b> {tr("au-dessus de l'objectif" if marge >= 0 else "sous l'objectif")}.
      {tr("La note agrégée ne remplace pas la revue des risques individuels.")}</p>
  </div>
</div>''',
        unsafe_allow_html=True)

    # ---------- 2. Points de vigilance : une liste d'actions ----------
    vigilance = [
        ("hors_tol", "donnée(s) critique(s) hors tolérance", "Voir les données hors tolérance", "donnees", {}),
        ("ctrl_rouges", "contrôle(s) bloquant(s)", "Voir les contrôles bloquants", "controles",
         {"filtre_controles": ["rouge"]}),
        ("haute", "anomalie(s) grave(s)", "Voir les anomalies ouvertes", "anomalies", {}),
        ("ctrl_retard", "contrôle(s) en retard", "Voir les contrôles en retard", "controles",
         {"filtre_controles": ["en retard"]}),
    ]
    nb_points = sum(1 for k, *_ in vigilance if (par_cle[k].nombre or 0) > 0)
    section("Points de vigilance", f"{nb_points} sur {len(vigilance)} à traiter")
    for col, (cle, libelle, action, page, etat) in zip(st.columns(4, gap="small"), vigilance):
        n = par_cle[cle].nombre or 0
        ton = par_cle[cle].ton if n else "vert"
        with col, st.container(border=True, key=f"qdd_vig_{cle}"):
            st.markdown(f'<div class="qdd-vig" data-ton="{ton}"><b>{n}</b><span>{escape(tr(libelle))}</span></div>',
                        unsafe_allow_html=True)
            if st.button(tr(action), key=f"action_{page}_{action}", type="tertiary", icon=":material/arrow_forward:"):
                aller(page, **etat)

    if df_lignes is not None:
        from operations_qdd.ui import afficher_diagnostic
        afficher_diagnostic(c, prev, df_lignes, aller)

    # ---------- 3. Indicateurs : panneaux compacts (une ligne par indicateur) ----------
    titres = {
        "La note": "Performance de la qualité", "Les contrôles": "Contrôles & restitutions réglementaires",
        "Les anomalies": "Suivi des anomalies", CHARGEMENT: "Fiabilité de l’exploitation",
    }
    section("Indicateurs de la campagne", "Évolution depuis la campagne précédente, colorée selon son sens")
    blocs = [b for b, _ in BLOCS]
    for i in range(0, len(blocs), 2):
        for col, bloc in zip(st.columns(2, gap="medium"), blocs[i:i + 2]):
            with col, st.container(border=True, key=f"qdd_panneau_{i}_{bloc[:6]}"):
                st.markdown(f'<div class="qdd-panneau-titre">{escape(tr(titres[bloc]))}</div>', unsafe_allow_html=True)
                for t in (x for x in ts if x.bloc == bloc):
                    with st.container(key=f"qdd_ligne_{t.cle}"):
                        g, v, d, b = st.columns([5.2, 2.2, 2.6, 0.8], vertical_alignment="center", gap="small")
                        g.markdown(f'<div class="qdd-ligne-lib"><i style="background:{COULEURS[t.ton]}"></i>'
                                   f'{escape(tr(t.titre))}</div>', unsafe_allow_html=True, help=t.aide)
                        v.markdown(f'<div class="qdd-ligne-val">{escape(tr(t.valeur))}</div>', unsafe_allow_html=True)
                        d.markdown(f'<div class="qdd-ligne-delta" style="color:{COULEURS[t.delta_ton]}">'
                                   f'{escape(tr(t.delta)) if t.delta else "&nbsp;"}</div>', unsafe_allow_html=True)
                        if t.liste is not None and b.button("", key=f"tuile_{t.cle}", icon=":material/open_in_new:",
                                                            type="tertiary", help=tr("Voir le détail ↗")):
                            detail(t)

    # ---------- 4. Points critiques hors seuil ----------
    ctrl = c["controles"]
    ko = ctrl[ctrl["statut"].isin(["rouge", "orange"])].copy()
    if not ko.empty:
        ko["ecart"] = (ko["resultat"] - ko["seuil"]) * 100
        ko = ko.sort_values(["statut", "ecart"], key=lambda s: s.map({"rouge": 0, "orange": 1}) if s.name == "statut" else s)
        bas_ko = min(int(min(ko["resultat"].min(), ko["seuil"].min()) * 100) - 1, 90) / 100
        ecart_txt = lambda e: f"{e:+.2f}".replace(".", ",").replace("-", "−")
        x = lambda v: max(0.0, min(100.0, (v - bas_ko) / (1 - bas_ko) * 100))
        section("Points critiques hors seuil",
                f"{len(ko)} point(s) · résultat retenu (●) face au seuil (|), échelle {pct(bas_ko, 0)}–100 %")
        lignes_html = "".join(
            f'<div class="qdd-crit"><div class="qdd-crit-id"><b>{escape(r.controle)}</b> · {escape(str(r.maille))}'
            f'<span>{escape(str(r.libelle))}</span></div>'
            f'<div class="qdd-crit-barre"><span class="qdd-crit-seuil" style="left:{x(r.seuil):.2f}%"></span>'
            f'<span class="qdd-crit-point" style="left:{x(r.resultat):.2f}%;background:{COULEURS[r.statut]}"></span></div>'
            f'<div class="qdd-crit-chiffres">{pct(r.resultat)} % <em>/ {pct(r.seuil)} %</em></div>'
            f'<div class="qdd-crit-ecart" style="color:{COULEURS[r.statut]}">{ecart_txt(r.ecart)} pt</div></div>'
            for r in ko.itertuples())
        st.markdown(f'<div class="qdd-crit-liste">{lignes_html}</div>',
                    unsafe_allow_html=True)

    # ---------- 5. Pareto des corrections, avec part cumulée ----------
    if df_lignes is not None and not df_lignes.empty:
        from lignes_anomalie import regroupements
        reg_l = regroupements(df_lignes)
        reg_l["Cumul"] = reg_l["Part"].cumsum()
        top = reg_l.head(5)
        n3 = reg_l["Part"].head(3).sum()
        section("Où concentrer les corrections ?",
                f"Top 5 messages · {int(reg_l['Lignes en anomalie'].sum())} lignes · "
                f"3 messages couvrent {n3:.1f} %".replace(".", ","))
        st.dataframe(top[["Contrôle", "Message", "Lignes en anomalie", "Part", "Cumul"]], hide_index=True, width="stretch",
                     column_config={"Contrôle": st.column_config.TextColumn(width="small"),
                                    "Message": st.column_config.TextColumn(width="large"),
                                    "Lignes en anomalie": st.column_config.NumberColumn("Lignes", width="small"),
                                    "Part": st.column_config.ProgressColumn(format="%.1f %%", min_value=0,
                                                                             max_value=100, width="small"),
                                    "Cumul": st.column_config.NumberColumn("Part cumulée", format="%.1f %%",
                                                                           width="small")})
        st.caption("Priorisation de Pareto : la part correspond aux lignes du message divisées par le total "
                   "des lignes en anomalie de cohérence. Elle ne mesure pas la gravité métier.")

    with st.expander(tr("Autres actions & accès rapides"), icon=":material/apps:"):
        for libelle, page, etat in [
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
        cols[0].download_button(tr("Registre des anomalies · CSV"), icon=":material/download:", data=_liste_anomalies(reg).to_csv(index=False, sep=";")
                           .encode("utf-8-sig"), file_name=f"registre_anomalies_{c['campagne']}.csv",
                           mime="text/csv", width="stretch")
        ko = c["controles"][c["controles"]["statut"].isin(["rouge", "orange"])]
        cols[1].download_button(tr("Contrôles en anomalie · CSV"), icon=":material/download:", data=_liste_controles(ko).to_csv(index=False, sep=";")
                           .encode("utf-8-sig"), file_name=f"controles_en_anomalie_{c['campagne']}.csv",
                           mime="text/csv", width="stretch")
        cols[2].download_button(tr("Rapport complet · Excel"), xlsx, icon=":material/download:", file_name="rapport_qdd.xlsx", type="primary", width="stretch",
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
