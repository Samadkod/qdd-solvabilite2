"""Export en modèle en étoile pour Qlik Sense (CSV ; séparateur « ; », UTF-8).

Le schéma est pensé pour éviter les clés synthétiques et les boucles dans Qlik :
  D_CAMPAGNE (campagne) ─ F_NOTE_DONNEE (campagne, donnee_id, cle_cd) ─ D_DONNEE (donnee_id)
  F_NOTE_DONNEE ─ F_RESULTAT (cle_cd, point_id, controle_id) ─ D_CONTROLE (controle_id)
  D_DONNEE ─ B_LIGNAGE (donnee_id, flux_id) ─ D_FLUX (flux_id)
  D_DONNEE ─ F_ANOMALIE (donnee_id ; campagne renommée campagne_detection pour éviter une boucle)
  D_CAMPAGNE ─ F_INDICATEUR, F_VARIATION
Un seul champ commun entre deux tables, et un seul chemin entre deux tables.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


# Préfixes courts : noms de champs valides en SAS (pas de point, 32 caractères max)
PREFIXES = {"D_CAMPAGNE": "cp", "D_DONNEE": "dd", "D_CONTROLE": "dc", "D_FLUX": "fx", "B_LIGNAGE": "lg",
            "F_NOTE_DONNEE": "nd", "F_RESULTAT": "rs", "F_INDICATEUR": "ind", "F_ANOMALIE": "an", "F_VARIATION": "vr"}
CLES = {
    "D_CAMPAGNE": {"campagne"}, "F_INDICATEUR": {"campagne"}, "F_VARIATION": {"campagne"},
    "F_NOTE_DONNEE": {"campagne", "donnee_id", "cle_cd"}, "D_DONNEE": {"donnee_id"},
    "F_RESULTAT": {"cle_cd", "controle_id"}, "D_CONTROLE": {"controle_id"},
    "B_LIGNAGE": {"donnee_id", "flux_id"}, "D_FLUX": {"flux_id"}, "F_ANOMALIE": {"donnee_id"},
}


def _w(df: pd.DataFrame, chemin: Path):
    df.to_csv(chemin, sep=";", index=False, encoding="utf-8", float_format="%.10g")


def exporter_qlik(campagnes, variation: pd.DataFrame, referentiel: pd.DataFrame, flux: pd.DataFrame,
                  dossier: Path) -> list[Path]:
    dossier.mkdir(parents=True, exist_ok=True)
    der = campagnes[-1]
    d_camp = pd.DataFrame([{"campagne": c.campagne, "date_arrete": c.date_arrete, "scr_m_eur": round(c.scr_ref, 3)}
                           for c in campagnes])
    don = der.evaluation.donnees.reset_index().rename(columns={"index": "donnee_id"})
    d_don = don[["donnee_id", "libelle", "description", "localisation", "source", "usage", "proprietaire",
                 "modalites", "frequence_maj", "critique_expert", "regle_gestion", "format_attendu", "etats_qrt"]]
    d_ctl = referentiel.copy()
    flux = flux.assign(zone_risque=flux["zone_risque"].astype(int))
    f_note, f_res, f_ind = [], [], []
    for c in campagnes:
        d = c.evaluation.donnees.reset_index().rename(columns={"index": "donnee_id"})
        d["cle_cd"] = c.campagne + "|" + d["donnee_id"]
        d["campagne"] = c.campagne
        d["critique"] = d["critique"].astype(int)
        f_note.append(d[["cle_cd", "campagne", "donnee_id", "sensibilite", "critique", "note",
                         "note_avant_degradation", "note_min", "statut", "nb_controles", "criteres_couverts"]])
        x = c.evaluation.controles.copy()
        x["cle_cd"] = c.campagne + "|" + x["donnee_id"]
        x = x.rename(columns={"controle_id": "point_id", "controle": "controle_id", "mesure_non_qdd": "mesure"})
        x["inclus_note"] = x["inclus_note"].astype(int)
        f_res.append(x[["cle_cd", "point_id", "controle_id", "maille", "resultat_brut", "mesure",
                        "anteriorite", "resultat", "seuil", "statut", "inclus_note", "date_derniere_real"]])
        ind = {**c.evaluation.indicateurs, **c.gouvernance}
        f_ind += [{"campagne": c.campagne, "indicateur": k, "valeur": v} for k, v in ind.items()
                  if isinstance(v, (int, float)) and not isinstance(v, bool)]
    b_lig = der.couverture[["donnee_id", "flux_id", "ordre", "couvert", "controles"]].rename(
        columns={"controles": "controles_couvrants"}).assign(couvert=lambda x: x["couvert"].astype(int))
    f_ano = der.registre.rename(columns={"campagne_detection": "campagne_detection"})
    f_var = variation.assign(campagne=der.campagne, ordre=range(len(variation)))
    fichiers = {
        "D_CAMPAGNE": d_camp, "D_DONNEE": d_don, "D_CONTROLE": d_ctl, "D_FLUX": flux,
        "B_LIGNAGE": b_lig, "F_NOTE_DONNEE": pd.concat(f_note), "F_RESULTAT": pd.concat(f_res),
        "F_INDICATEUR": pd.DataFrame(f_ind), "F_ANOMALIE": f_ano, "F_VARIATION": f_var,
    }
    # Qualification : seuls les champs de liaison gardent leur nom ; les autres sont préfixés
    # par la table, ce qui garantit l'absence de clés synthétiques et de boucles.
    for nom, df in fichiers.items():
        fichiers[nom] = df.rename(columns={c: f"{PREFIXES[nom]}_{c}" for c in df.columns if c not in CLES[nom]})
    out = []
    for nom, df in fichiers.items():
        p = dossier / f"{nom}.csv"
        _w(df, p)
        out.append(p)
    return out


SCRIPT_QLIK = """// =====================================================================
// Chargement du modèle QDD Solvabilité 2 dans Qlik Sense
// Prérequis : une connexion de type dossier nommée QDD_EXPORT pointant sur le dossier des CSV
// (export Python : output/qlik/ ; export SAS : sas/sorties/qlik/).
// =====================================================================
SET ThousandSep=' '; SET DecimalSep='.';

D_CAMPAGNE:    LOAD * FROM [lib://QDD_EXPORT/D_CAMPAGNE.csv]    (txt, utf8, embedded labels, delimiter is ';', msq);
D_DONNEE:      LOAD * FROM [lib://QDD_EXPORT/D_DONNEE.csv]      (txt, utf8, embedded labels, delimiter is ';', msq);
D_CONTROLE:    LOAD * FROM [lib://QDD_EXPORT/D_CONTROLE.csv]    (txt, utf8, embedded labels, delimiter is ';', msq);
D_FLUX:        LOAD * FROM [lib://QDD_EXPORT/D_FLUX.csv]        (txt, utf8, embedded labels, delimiter is ';', msq);
B_LIGNAGE:     LOAD * FROM [lib://QDD_EXPORT/B_LIGNAGE.csv]     (txt, utf8, embedded labels, delimiter is ';', msq);
F_NOTE_DONNEE: LOAD * FROM [lib://QDD_EXPORT/F_NOTE_DONNEE.csv] (txt, utf8, embedded labels, delimiter is ';', msq);
F_RESULTAT:    LOAD * FROM [lib://QDD_EXPORT/F_RESULTAT.csv]    (txt, utf8, embedded labels, delimiter is ';', msq);
F_INDICATEUR:  LOAD * FROM [lib://QDD_EXPORT/F_INDICATEUR.csv]  (txt, utf8, embedded labels, delimiter is ';', msq);
F_ANOMALIE:    LOAD * FROM [lib://QDD_EXPORT/F_ANOMALIE.csv]    (txt, utf8, embedded labels, delimiter is ';', msq);
F_VARIATION:   LOAD * FROM [lib://QDD_EXPORT/F_VARIATION.csv]   (txt, utf8, embedded labels, delimiter is ';', msq);

// Contrôle du modèle : aucune table $Syn ne doit apparaître dans le visionneur de modèle.
"""
