"""Gouvernance de la donnée : lignage, couverture des zones de risque, registre des anomalies,
journal d'exécution.

Ces briques répondent aux attentes de la notice ACPR (cartographie des flux et lignage,
points 55 à 60 ; documentation et traçabilité) et aux missions de l'offre (dictionnaire,
lignage, contrôles, coordination de la résolution des anomalies, audits ACPR et CAC).
"""
from __future__ import annotations

import getpass
import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------------------
# 1. Lignage et couverture des zones de risque
# --------------------------------------------------------------------------------------
def couverture_lignage(lignage: pd.DataFrame, flux: pd.DataFrame, controles: pd.DataFrame,
                       donnees: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par (donnée, flux) du lignage, avec les contrôles qui sécurisent ce passage.

    Un passage (donnée d, flux f) est couvert s'il existe au moins un point de contrôle
    portant sur d et dont le référentiel déclare f dans sa colonne `flux`.
    Seuls les flux marqués « zone de risque » comptent dans le taux de couverture.

    controles : points de contrôle d'une campagne (colonnes donnee_id, controle, flux).
    donnees   : sortie du moteur (index donnee_id, colonnes critique, libelle, proprietaire).
    """
    c = controles[["donnee_id", "controle", "flux"]].copy()
    c["flux"] = c["flux"].astype(str).str.split(",")
    c = c.explode("flux")
    c["flux"] = c["flux"].str.strip()
    couv = (c.groupby(["donnee_id", "flux"])["controle"]
             .apply(lambda s: ", ".join(sorted(set(s)))).rename("controles").reset_index()
             .rename(columns={"flux": "flux_id"}))
    out = (lignage.merge(flux, on="flux_id", how="left")
                  .merge(couv, on=["donnee_id", "flux_id"], how="left"))
    out["couvert"] = out["controles"].notna()
    out["critique"] = out["donnee_id"].map(donnees["critique"]).fillna(False).astype(bool)
    out["proprietaire"] = out["donnee_id"].map(donnees["proprietaire"])
    out["libelle_donnee"] = out["donnee_id"].map(donnees["libelle"])
    out["zone_risque"] = out["zone_risque"].astype(bool)
    return out.sort_values(["donnee_id", "ordre"]).reset_index(drop=True)


def indicateurs_couverture(couv: pd.DataFrame) -> dict:
    z = couv[couv["zone_risque"] & couv["critique"]]
    non = z[~z["couvert"]]
    return {
        "taux_couverture_zones_risque": float(z["couvert"].mean()) if len(z) else float("nan"),
        "nb_zones_risque_critiques": int(len(z)),
        "nb_zones_non_couvertes": int(len(non)),
        "flux_non_couverts": sorted(non["flux_id"].unique().tolist()),
    }


# --------------------------------------------------------------------------------------
# 2. Registre des anomalies (cycle de vie entre campagnes)
# --------------------------------------------------------------------------------------
COLONNES_REGISTRE = ["anomalie_id", "type", "objet", "donnee_id", "libelle", "gravite", "proprietaire",
                     "campagne_detection", "date_detection", "echeance", "derniere_campagne", "nb_campagnes",
                     "statut", "date_cloture", "constat", "action_attendue"]
DELAI_JOURS = {"Haute": 30, "Moyenne": 60}


def maj_registre(registre: pd.DataFrame | None, campagne: str, date_arrete: str,
                 controles: pd.DataFrame, donnees: pd.DataFrame, couv: pd.DataFrame) -> pd.DataFrame:
    """Met à jour le registre après une campagne.

    Règles (déterministes, auditables) :
      - point de contrôle évalué en rouge ou orange -> anomalie ouverte (gravité Haute / Moyenne).
        Type « Contrôle non réalisé » si l'antériorité est > 0, « Restitution QRT » pour un contrôle
        état / source, sinon « Qualité de donnée » ;
      - zone de risque d'une donnée critique sans contrôle -> anomalie « Couverture » (Moyenne) ;
      - une anomalie déjà ouverte et toujours constatée passe en « Récurrente » ;
      - une anomalie de qualité n'est clôturée que si le point a été RÉALISÉ dans la campagne
        et qu'il est vert. Un point non réalisé ne prouve pas la correction ;
      - une anomalie « Contrôle non réalisé » est clôturée dès que le contrôle est réalisé ;
        s'il est alors sous son seuil, une anomalie de qualité est ouverte à la place ;
      - échéance = date de détection + 30 jours (Haute) ou 60 jours (Moyenne).
    """
    reg = (pd.DataFrame(columns=COLONNES_REGISTRE) if registre is None else registre.copy())
    d = pd.Timestamp(date_arrete)
    constats = []
    for r in controles[controles["statut"].notna()].itertuples():
        if r.statut in ("rouge", "orange"):
            restit = hasattr(r, "inclus_note") and not bool(r.inclus_note)
            typ = ("Contrôle non réalisé" if r.anteriorite > 0
                   else "Restitution QRT" if restit else "Qualité de donnée")
            constats.append({
                "objet": r.controle_id, "type": typ, "donnee_id": r.donnee_id,
                "libelle": r.libelle, "gravite": "Haute" if r.statut == "rouge" else "Moyenne",
                "proprietaire": r.responsable,
                "constat": (f"Résultat {r.resultat:.2%} < seuil {r.seuil:.2%}"
                            + (f" (antériorité {r.anteriorite:g})" if r.anteriorite > 0 else "")),
                "action_attendue": ("Réaliser le contrôle et transmettre le résultat" if typ == "Contrôle non réalisé"
                                    else "Aligner l'état sur sa source avant la remise et tracer l'ajustement"
                                    if typ == "Restitution QRT"
                                    else "Analyser l'écart, corriger la source, documenter l'ajustement (notice, point 37)"),
            })
    for r in couv[couv["zone_risque"] & couv["critique"] & ~couv["couvert"]].itertuples():
        constats.append({
            "objet": f"{r.donnee_id}|{r.flux_id}", "type": "Couverture", "donnee_id": r.donnee_id,
            "libelle": f"Flux {r.flux_id} non contrôlé : {r.systeme_source} → {r.systeme_cible}",
            "gravite": "Moyenne", "proprietaire": r.proprietaire,
            "constat": f"Zone de risque « {r.traitement} » sans contrôle de niveau 1",
            "action_attendue": "Concevoir un contrôle sur ce flux et l'ajouter au référentiel",
        })
    constats = pd.DataFrame(constats, columns=["objet", "type", "donnee_id", "libelle", "gravite",
                                               "proprietaire", "constat", "action_attendue"])
    constats = constats.sort_values(["type", "objet"]).reset_index(drop=True)  # identifiants déterministes (parité SAS)
    ouverts = reg["statut"].isin(["Ouverte", "Récurrente"])
    cle = lambda df: df["type"] + "§" + df["objet"]
    cles_constats = set(cle(constats)) if len(constats) else set()

    # Clôtures
    realises = set(controles.loc[controles["anteriorite"] == 0, "controle_id"])
    for i in reg.index[ouverts]:
        k = reg.at[i, "type"] + "§" + reg.at[i, "objet"]
        if k in cles_constats:
            continue
        typ, obj = reg.at[i, "type"], reg.at[i, "objet"]
        if typ == "Couverture" or (obj in realises):
            reg.at[i, "statut"] = "Clôturée"
            reg.at[i, "date_cloture"] = d.date().isoformat()
            reg.at[i, "derniere_campagne"] = campagne

    # Récurrences et nouvelles anomalies
    ouverts = reg["statut"].isin(["Ouverte", "Récurrente"])
    idx_ouverts = {reg.at[i, "type"] + "§" + reg.at[i, "objet"]: i for i in reg.index[ouverts]}
    n = len(reg)
    nouvelles = []
    for c in constats.itertuples(index=False):
        k = f"{c.type}§{c.objet}"
        if k in idx_ouverts:
            i = idx_ouverts[k]
            reg.at[i, "statut"] = "Récurrente"
            reg.at[i, "nb_campagnes"] = int(reg.at[i, "nb_campagnes"]) + 1
            reg.at[i, "derniere_campagne"] = campagne
            reg.at[i, "constat"] = c.constat
            if c.gravite == "Haute":
                reg.at[i, "gravite"] = "Haute"
        else:
            n += 1
            nouvelles.append({**c._asdict(), "anomalie_id": f"ANO-{d:%Y}-{n:03d}", "campagne_detection": campagne,
                              "date_detection": d.date().isoformat(),
                              "echeance": (d + pd.Timedelta(days=DELAI_JOURS[c.gravite])).date().isoformat(),
                              "derniere_campagne": campagne, "nb_campagnes": 1, "statut": "Ouverte",
                              "date_cloture": None})
    if nouvelles:
        reg = pd.concat([reg, pd.DataFrame(nouvelles)], ignore_index=True)
    return reg[COLONNES_REGISTRE].reset_index(drop=True)


def indicateurs_anomalies(reg: pd.DataFrame, date_arrete: str) -> dict:
    o = reg[reg["statut"].isin(["Ouverte", "Récurrente"])]
    d = pd.Timestamp(date_arrete)
    retard = o[pd.to_datetime(o["echeance"]) < d]
    return {
        "nb_anomalies_ouvertes": int(len(o)),
        "nb_anomalies_haute": int((o["gravite"] == "Haute").sum()),
        "nb_anomalies_recurrentes": int((o["statut"] == "Récurrente").sum()),
        "nb_anomalies_en_retard": int(len(retard)),
        "nb_anomalies_cloturees": int((reg["statut"] == "Clôturée").sum()),
    }


# --------------------------------------------------------------------------------------
# 3. Journal d'exécution (piste d'audit)
# --------------------------------------------------------------------------------------
def _sha256(chemin: Path) -> str:
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()[:16]


def version_code(racine: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(racine), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "hors-git"


def entree_journal(campagne: str, date_arrete: str, params, racine: Path, referentiels: Path,
                   volumetries: dict, nb_executes: int, nb_points: int, indicateurs: dict) -> dict:
    """Une ligne de journal : qui, quand, avec quels paramètres, quelle version du code,
    quels référentiels (empreinte SHA-256) et quelles volumétries sources."""
    return {
        "horodatage": datetime.now().isoformat(timespec="seconds"),
        "utilisateur": getpass.getuser(),
        "campagne": campagne,
        "date_arrete": date_arrete,
        "version_code": version_code(racine),
        "parametres": json.dumps(asdict(params), ensure_ascii=False),
        "empreinte_referentiels": json.dumps({p.name: _sha256(p) for p in sorted(referentiels.glob("*.csv"))}),
        "volumetries_sources": json.dumps(volumetries),
        "nb_controles_executes": nb_executes,
        "nb_points": nb_points,
        "note": indicateurs.get("note"),
        "note_min": indicateurs.get("note_min"),
    }
