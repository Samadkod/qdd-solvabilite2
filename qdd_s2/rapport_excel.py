"""Rapport Excel de campagne QDD.

Les onglets « Paramètres », « Contrôles » et « Données critiques » sont VIVANTS :
dégradation, notes par donnée, notes minimum, statuts et note agrégée sont des
formules Excel qui se recalculent si l'on modifie un paramètre (cellules bleues)
ou un résultat de contrôle. Les autres onglets sont des valeurs produites par le
moteur Python (comparaison N-1, axes d'analyse, variation, sensibilités).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

F = "Arial"
BLEU = Font(name=F, color="0000FF")
GRAS = Font(name=F, bold=True)
TITRE = Font(name=F, bold=True, size=14, color="1F3864")
NORMAL = Font(name=F)
ENTETE = PatternFill("solid", fgColor="1F3864")
JAUNE = PatternFill("solid", fgColor="FFF2CC")
VERT = PatternFill("solid", fgColor="C6EFCE")
ORANGE = PatternFill("solid", fgColor="FFE699")
ROUGE = PatternFill("solid", fgColor="FFC7CE")
FIN = Side(style="thin", color="BFBFBF")
PCT = "0.00%"


def _entetes(ws, row, cols, widths=None):
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=j, value=c)
        cell.font = Font(name=F, bold=True, color="FFFFFF")
        cell.fill = ENTETE
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w


def _df(ws, df: pd.DataFrame, row=1, pct_cols=(), widths=None, table=None):
    _entetes(ws, row, list(df.columns), widths)
    for i, rec in enumerate(df.itertuples(index=False), row + 1):
        for j, v in enumerate(rec, 1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            if isinstance(v, (list, tuple, set)):
                v = ", ".join(map(str, v))
            c = ws.cell(row=i, column=j, value=v)
            c.font = NORMAL
            if df.columns[j - 1] in pct_cols:
                c.number_format = PCT
    if table and len(df):
        ref = f"A{row}:{get_column_letter(len(df.columns))}{row + len(df)}"
        t = Table(displayName=table, ref=ref)
        t.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
        ws.add_table(t)
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def _statuts(ws, plage):
    ws.conditional_formatting.add(plage, CellIsRule(operator="equal", formula=['"vert"'], fill=VERT))
    ws.conditional_formatting.add(plage, CellIsRule(operator="equal", formula=['"orange"'], fill=ORANGE))
    ws.conditional_formatting.add(plage, CellIsRule(operator="equal", formula=['"rouge"'], fill=ROUGE))


def ecrire_rapport(campagnes, variation: pd.DataFrame, chemin: str | Path, axes=("maille", "etape", "criteres", "responsable")):
    cour, prec = campagnes[-1], campagnes[-2] if len(campagnes) > 1 else None
    ev = cour.evaluation
    p = ev.params
    wb = Workbook()

    # ---------------- Paramètres ----------------
    wp = wb.active
    wp.title = "Paramètres"
    wp["A1"] = "Paramètres de la campagne"; wp["A1"].font = TITRE
    wp["A2"] = "Cellules bleues sur fond jaune = hypothèses modifiables ; tout le classeur se recalcule."
    wp["A2"].font = Font(name=F, italic=True)
    params = [
        ("Seuil de significativité (criticité)", p.seuil_significativite, "Éq. 5 — donnée critique si sensibilité ≥ seuil"),
        ("ΔSCR max par donnée critique", p.delta_scr_max, "Éq. 10 — note min = 1 − ΔSCR/s ; doit rester < seuil (éq. 12)"),
        ("Coefficient de dégradation", p.coef_degradation, "Éq. 36 — dégradation simple par réalisation manquée"),
        ("Marge zone orange", p.marge_alerte, "Amélioration : note entre min − marge et min = orange"),
    ]
    _entetes(wp, 4, ["Paramètre", "Valeur", "Commentaire / source"], [42, 14, 80])
    for i, (lib, val, com) in enumerate(params, 5):
        wp.cell(row=i, column=1, value=lib).font = NORMAL
        c = wp.cell(row=i, column=2, value=val); c.font = BLEU; c.fill = JAUNE; c.number_format = PCT
        wp.cell(row=i, column=3, value=com).font = NORMAL
    wp["A10"] = "Contrôle de cohérence ΔSCR < seuil"; wp["A10"].font = GRAS
    wp["B10"] = '=IF(B6<B5,"OK","INCOHÉRENT")'; wp["B10"].font = GRAS
    wp["A12"] = "Mode de tolérance"; wp["B12"] = p.mode_tolerance
    wp["A13"] = "Pondération des données"; wp["B13"] = p.ponderation_donnees
    wp["A14"] = "Base d'antériorité"; wp["B14"] = p.base_anteriorite
    wp["A15"] = "Méthode de dégradation"; wp["B15"] = p.methode_degradation
    wp["A16"] = "Note : le classeur vivant implémente le mode « donnée » (ΔSCR max) et la dégradation simple, choix retenus par le mémoire."
    wp["A16"].font = Font(name=F, italic=True)
    wp["A17"] = ("Donnée critique à dire d'expert sans sensibilité calculable (ex. date de survenance) : "
                 "convention = sensibilité moyenne des données critiques, documentée dans la politique QDD.")
    wp["A17"].font = Font(name=F, italic=True)
    SEUIL, DSCR, COEF, MARGE = "Paramètres!$B$5", "Paramètres!$B$6", "Paramètres!$B$7", "Paramètres!$B$8"

    # ---------------- Contrôles (vivant) ----------------
    wc = wb.create_sheet("Contrôles")
    c = ev.controles.sort_values(["donnee_id", "controle_id"]).reset_index(drop=True)
    cols = ["Point de contrôle", "Libellé", "Famille", "Donnée", "Maille", "Critères", "Fréq.", "Étape", "Responsable",
            "Poids", "Résultat brut", "Antériorité", "Résultat dégradé", "Poids × résultat", "Poids × brut",
            "Seuil d'acceptation", "Conforme", "Statut", "Détail du calcul", "Dernière réalisation",
            "Inclus dans la note (1/0)", "Seuil fixe (restitution)", "Poids note"]
    _entetes(wc, 1, cols, [20, 34, 13, 34, 18, 9, 6, 22, 18, 7, 11, 10, 11, 10, 10, 11, 9, 9, 46, 13, 11, 11, 9])
    n = len(c)
    for i, r in enumerate(c.itertuples(), 2):
        vals = [r.controle_id, r.libelle, r.famille, r.donnee_id, r.maille, r.criteres, r.frequence, r.etape,
                r.responsable, r.poids, r.resultat_brut, r.anteriorite]
        for j, v in enumerate(vals, 1):
            cell = wc.cell(row=i, column=j, value=v); cell.font = NORMAL
        for j in (10, 11, 12):
            wc.cell(row=i, column=j).font = BLEU
        wc.cell(row=i, column=11).number_format = PCT
        wc.cell(row=i, column=13, value=f"=K{i}*MAX(0,1-{COEF}*L{i})").number_format = PCT
        inc = int(r.inclus_note) if pd.notna(r.inclus_note) else 1
        fx = r.seuil_fixe if pd.notna(r.seuil_fixe) else None
        wc.cell(row=i, column=21, value=inc).font = BLEU
        cfx = wc.cell(row=i, column=22, value=fx); cfx.font = BLEU; cfx.number_format = PCT
        wc.cell(row=i, column=23, value=f"=J{i}*U{i}")
        wc.cell(row=i, column=14, value=f"=W{i}*M{i}")
        wc.cell(row=i, column=15, value=f"=W{i}*K{i}")
        wc.cell(row=i, column=16, value=f"=IF(V{i}<>\"\",V{i},IFERROR(INDEX('Données critiques'!$J:$J,MATCH(D{i},'Données critiques'!$A:$A,0)),\"\"))").number_format = PCT
        wc.cell(row=i, column=17, value=f'=IF(P{i}="","—",IF(M{i}>=P{i},"OUI","NON"))')
        wc.cell(row=i, column=18, value=f'=IF(P{i}="","",IF(M{i}>=P{i},"vert",IF(V{i}<>"","rouge",IF(M{i}>=P{i}-{MARGE},"orange","rouge"))))')
        wc.cell(row=i, column=19, value=r.detail).font = NORMAL
        wc.cell(row=i, column=20, value=str(r.date_derniere_real)).font = NORMAL
    _statuts(wc, f"R2:R{n + 1}")
    wc.freeze_panes = "B2"
    wc.auto_filter.ref = f"A1:W{n + 1}"
    LC = n + 1

    # ---------------- Données critiques (vivant) ----------------
    wd = wb.create_sheet("Données critiques")
    d = ev.donnees.reset_index().rename(columns={"index": "donnee_id"})
    cols = ["Donnée", "Libellé", "Propriétaire", "Valeur (M€)", "Sensibilité SCR", "Critique (expert)", "Critique",
            "Note QDD", "Note avant dégradation", "Note minimum", "Écart à l'objectif", "Statut", "Nb contrôles",
            "Critères couverts", "Pondération (s × critique)", "Non-linéarité"]
    _entetes(wd, 1, cols, [36, 34, 22, 11, 11, 10, 9, 10, 11, 11, 11, 9, 9, 10, 12, 11])
    for i, r in enumerate(d.itertuples(), 2):
        exp = r.critique_expert
        exp = "" if pd.isna(exp) else ("OUI" if exp else "NON")
        vals = [r.donnee_id, r.libelle, r.proprietaire, None if pd.isna(r.valeur) else r.valeur, r.sensibilite, exp]
        for j, v in enumerate(vals, 1):
            wd.cell(row=i, column=j, value=v).font = NORMAL
        wd.cell(row=i, column=4).number_format = "#,##0.0"
        wd.cell(row=i, column=5).font = BLEU; wd.cell(row=i, column=5).number_format = PCT
        wd.cell(row=i, column=7, value=f'=IF(F{i}="",IF(E{i}>={SEUIL},"OUI","NON"),F{i})')
        wd.cell(row=i, column=8, value=f"=IFERROR(SUMIFS(Contrôles!$N$2:$N${LC},Contrôles!$D$2:$D${LC},A{i})/SUMIFS(Contrôles!$W$2:$W${LC},Contrôles!$D$2:$D${LC},A{i}),\"\")").number_format = PCT
        wd.cell(row=i, column=9, value=f"=IFERROR(SUMIFS(Contrôles!$O$2:$O${LC},Contrôles!$D$2:$D${LC},A{i})/SUMIFS(Contrôles!$W$2:$W${LC},Contrôles!$D$2:$D${LC},A{i}),\"\")").number_format = PCT
        wd.cell(row=i, column=10, value=f'=IF(AND(G{i}="OUI",E{i}>0),1-{DSCR}/E{i},"")').number_format = PCT
        wd.cell(row=i, column=11, value=f'=IF(OR(J{i}="",H{i}=""),"",H{i}-J{i})').number_format = PCT
        wd.cell(row=i, column=12, value=f'=IF(OR(J{i}="",H{i}=""),"",IF(H{i}>=J{i},"vert",IF(H{i}>=J{i}-{MARGE},"orange","rouge")))')
        wd.cell(row=i, column=13, value=f"=COUNTIFS(Contrôles!$D$2:$D${LC},A{i},Contrôles!$U$2:$U${LC},1)")
        wd.cell(row=i, column=14, value=getattr(r, "criteres_couverts", "")).font = NORMAL
        wd.cell(row=i, column=15, value=f'=IF(AND(G{i}="OUI",M{i}>0),E{i},0)').number_format = PCT
        nl = r.non_linearite
        wd.cell(row=i, column=16, value=None if pd.isna(nl) else nl).number_format = PCT
    LD = len(d) + 1
    _statuts(wd, f"L2:L{LD}")
    wd.freeze_panes = "B2"

    # ---------------- Synthèse ----------------
    ws = wb.create_sheet("Synthèse", 0)
    ws["A1"] = f"Qualité des données Solvabilité 2 — campagne {cour.campagne} (arrêté {cour.date_arrete})"
    ws["A1"].font = TITRE
    ws["A2"] = "Assureur dommages BTP FICTIF — données simulées à des fins de démonstration de la méthode (mémoire C. Motard, ISFA 2024)."
    ws["A2"].font = Font(name=F, italic=True, color="C00000")
    _entetes(ws, 4, ["Indicateur", "Campagne N (Excel, vivant)", "Campagne N (moteur Python)", "Campagne N-1 (moteur)", "Lecture"],
             [44, 22, 22, 20, 70])
    DC = "'Données critiques'"
    rng = lambda col: f"{DC}!${col}$2:${col}${LD}"
    ind = ev.indicateurs
    indp = prec.evaluation.indicateurs if prec else {}
    lignes = [
        ("Note QDD agrégée", f"=SUMPRODUCT({rng('O')},{rng('H')})/SUM({rng('O')})", "note",
         "Moyenne des notes des données critiques pondérée par la sensibilité (éq. 6)"),
        ("Note QDD agrégée minimum (objectif)", f"=SUMPRODUCT({rng('O')},{rng('J')})/SUM({rng('O')})", "note_min",
         "Agrégation des notes minimum = 1 − tolérance globale (éq. 13-14)"),
        ("Écart à l'objectif", "=B5-B6", "ecart_objectif", "> 0 : tolérance globale respectée"),
        ("Note avant dégradation des contrôles non réalisés", f"=SUMPRODUCT({rng('O')},{rng('I')})/SUM({rng('O')})",
         "note_avant_degradation", "Isole l'effet des contrôles en retard"),
        ("Dégradation moyenne", "=1-B5/B8", "degradation_moyenne", "Coût des contrôles non réalisés"),
        ("Nb données critiques", f'=COUNTIF({rng("G")},"OUI")', "nb_donnees_critiques", ""),
        ("Sensibilité moyenne des données critiques", f'=AVERAGEIF({rng("G")},"OUI",{rng("E")})', "sensibilite_moyenne", ""),
        ("Taux de validation (contrôles à jour)",
         f'=(COUNTIFS(Contrôles!$L$2:$L${LC},0,Contrôles!$Q$2:$Q${LC},"OUI",Contrôles!$U$2:$U${LC},1)+COUNTIFS(Contrôles!$L$2:$L${LC},0,Contrôles!$Q$2:$Q${LC},"NON",Contrôles!$U$2:$U${LC},1))'
         f'/(COUNTIFS(Contrôles!$Q$2:$Q${LC},"OUI",Contrôles!$U$2:$U${LC},1)+COUNTIFS(Contrôles!$Q$2:$Q${LC},"NON",Contrôles!$U$2:$U${LC},1))',
         "taux_validation", "Part des contrôles de données critiques réalisés à l'échéance"),
        ("Taux de conformité des contrôles",
         f'=COUNTIFS(Contrôles!$Q$2:$Q${LC},"OUI",Contrôles!$U$2:$U${LC},1)/(COUNTIFS(Contrôles!$Q$2:$Q${LC},"OUI",Contrôles!$U$2:$U${LC},1)+COUNTIFS(Contrôles!$Q$2:$Q${LC},"NON",Contrôles!$U$2:$U${LC},1))',
         "taux_conformite_controles", "Amélioration : part des contrôles ≥ seuil d'acceptation"),
        ("Nb données critiques hors tolérance", f'=COUNTIF({rng("L")},"orange")+COUNTIF({rng("L")},"rouge")',
         "nb_donnees_hors_tolerance", "Amélioration (maillon faible) : à traiter même si la note agrégée est verte"),
        ("Conformité des restitutions QRT (hors note)",
         f'=IFERROR(COUNTIFS(Contrôles!$Q$2:$Q${LC},"OUI",Contrôles!$U$2:$U${LC},0)/(COUNTIFS(Contrôles!$Q$2:$Q${LC},"OUI",Contrôles!$U$2:$U${LC},0)+COUNTIFS(Contrôles!$Q$2:$Q${LC},"NON",Contrôles!$U$2:$U${LC},0)),"")',
         "taux_conformite_restitutions", "Contrôles état QRT vs source : seuil fixe, tout écart est une anomalie"),
    ]
    for i, (lib, formule, cle, lecture) in enumerate(lignes, 5):
        ws.cell(row=i, column=1, value=lib).font = NORMAL
        cb = ws.cell(row=i, column=2, value=formule); cb.font = GRAS
        ws.cell(row=i, column=3, value=ind.get(cle)).font = NORMAL
        ws.cell(row=i, column=4, value=indp.get(cle)).font = NORMAL
        ws.cell(row=i, column=5, value=lecture).font = NORMAL
        if cle not in ("nb_donnees_critiques", "nb_donnees_hors_tolerance"):
            for col in (2, 3, 4):
                ws.cell(row=i, column=col).number_format = PCT
    ws["A17"] = "SCR (formule standard simplifiée, M€)"; ws["C17"] = cour.scr_ref; ws["D17"] = prec.scr_ref if prec else None
    for col in "CD":
        ws[f"{col}17"].number_format = "#,##0.0"
    ws["A19"] = "Données critiques en alerte"; ws["A19"].font = GRAS
    alerte = ev.donnees[ev.donnees["statut"].isin(["orange", "rouge"])]
    for k, (idx, r) in enumerate(alerte.iterrows(), 20):
        ws.cell(row=k, column=1, value=f"{r.libelle} ({idx})")
        ws.cell(row=k, column=2, value=r.note).number_format = PCT
        ws.cell(row=k, column=3, value=r.note_min).number_format = PCT
        cs = ws.cell(row=k, column=4, value=r.statut); cs.fill = ROUGE if r.statut == "rouge" else ORANGE
    gv, gvp = cour.gouvernance or {}, (prec.gouvernance if prec else None) or {}
    ws["A26"] = "Gouvernance (valeurs du moteur)"; ws["A26"].font = GRAS
    for k, (lib, cle, fmt) in enumerate([
            ("Couverture des zones de risque (lignage, données critiques)", "taux_couverture_zones_risque", PCT),
            ("Zones de risque sans contrôle", "nb_zones_non_couvertes", "0"),
            ("Anomalies ouvertes", "nb_anomalies_ouvertes", "0"),
            ("dont gravité haute", "nb_anomalies_haute", "0"),
            ("dont échéance dépassée", "nb_anomalies_en_retard", "0"),
            ("Anomalies clôturées", "nb_anomalies_cloturees", "0")], 27):
        ws.cell(row=k, column=1, value=lib).font = NORMAL
        for col, src in ((3, gv), (4, gvp)):
            c_ = ws.cell(row=k, column=col, value=src.get(cle)); c_.number_format = fmt
    ws["A34"] = "Colonne B = formules Excel (se recalcule si vous modifiez Paramètres / Contrôles) ; colonne C = contrôle croisé du moteur Python."
    ws["A25"].font = Font(name=F, italic=True)
    ws.freeze_panes = "A5"

    # ---------------- Valeurs produites par le moteur ----------------
    wv = wb.create_sheet("Variation N-1 → N")
    v = variation.copy()
    _df(wv, v, pct_cols=("note", "impact"), widths=[54, 12, 12], table="Variation")
    wv.cell(row=len(v) + 3, column=1, value="Décomposition par substitutions successives (mémoire §3.1.3, tableau 20). Somme des impacts = variation totale.").font = Font(name=F, italic=True)

    for axe in axes:
        wa = wb.create_sheet(f"Axe {axe}")
        t = ev.par_axe(axe).reset_index()
        _df(wa, t, pct_cols=("note", "note_avant_degradation", "note_min", "ecart_objectif", "taux_validation", "taux_conformite"),
            widths=[26] + [14] * 8, table=f"Axe_{axe}")

    wsn = wb.create_sheet("Sensibilités")
    sn = cour.sensibilites.reset_index()
    _df(wsn, sn, pct_cols=[c for c in sn.columns if c.startswith("s") and c != "valeur"] + ["non_linearite"],
        widths=[36, 10, 11, 13, 13, 13, 12, 9], table="Sensibilites")
    wsn.cell(row=len(sn) + 3, column=1, value="Sensibilité = (|ΔSCR|/SCR) / choc. Linéaire si les sensibilités à -15 %, +5 %, +30 % s'écartent de moins de 10 % de celle à +15 %.").font = Font(name=F, italic=True)

    wr = wb.create_sheet("Dictionnaire des données")
    _df(wr, ev.donnees.reset_index()[["donnee_id", "libelle", "description", "localisation", "source", "usage",
                                      "proprietaire", "modalites", "frequence_maj", "regle_gestion",
                                      "format_attendu", "etats_qrt", "critique"]],
        widths=[34, 30, 50, 40, 26, 34, 24, 18, 13, 50, 20, 30, 9], table="Repertoire")

    if cour.couverture is not None:
        wl = wb.create_sheet("Lignage & couverture")
        cv = cour.couverture[["donnee_id", "libelle_donnee", "critique", "ordre", "flux_id", "systeme_source",
                              "systeme_cible", "traitement", "mode", "zone_risque", "couvert", "controles", "proprietaire"]]
        _df(wl, cv, widths=[34, 30, 9, 7, 8, 26, 26, 44, 15, 11, 9, 20, 24], table="Lignage")
        for i, r in enumerate(cv.itertuples(), 2):
            if r.zone_risque and r.critique and not r.couvert:
                for j in range(1, 14):
                    wl.cell(row=i, column=j).fill = ROUGE
        wl.cell(row=len(cv) + 3, column=1, value="Rouge : zone de risque d'une donnée critique sans contrôle de niveau 1 (notice ACPR, points 55-60).").font = Font(name=F, italic=True)
    if cour.registre is not None:
        wa = wb.create_sheet("Registre des anomalies")
        _df(wa, cour.registre, widths=[14, 20, 34, 34, 40, 9, 22, 10, 12, 12, 10, 8, 12, 12, 40, 50], table="Anomalies")
        _statuts(wa, f"M2:M{len(cour.registre) + 1}")
        wa.conditional_formatting.add(f"M2:M{len(cour.registre) + 1}", CellIsRule(operator="equal", formula=['"Ouverte"'], fill=ORANGE))
        wa.conditional_formatting.add(f"M2:M{len(cour.registre) + 1}", CellIsRule(operator="equal", formula=['"Récurrente"'], fill=ROUGE))
        wa.conditional_formatting.add(f"M2:M{len(cour.registre) + 1}", CellIsRule(operator="equal", formula=['"Clôturée"'], fill=VERT))
    if cour.journal is not None:
        wj = wb.create_sheet("Journal d'exécution")
        jr = pd.DataFrame([c.journal for c in campagnes])
        _df(wj, jr, widths=[20, 12, 10, 12, 12, 60, 60, 60, 10, 9, 10, 10], table="Journal")

    for w in wb.worksheets:
        for row in w.iter_rows():
            for cell in row:
                if cell.font is None or cell.font.name != F:
                    cell.font = Font(name=F, bold=cell.font.bold if cell.font else False,
                                     italic=cell.font.italic if cell.font else False,
                                     color=cell.font.color if cell.font else None,
                                     size=cell.font.size if cell.font else 11)
    wb.save(chemin)
    return Path(chemin)
