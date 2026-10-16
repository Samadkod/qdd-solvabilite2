"""CLI : python -m qdd_s2 [--symetrique] [--sortie output/]

1. (re)génère la base fictive si absente,
2. lance les campagnes du plan, 3. écrit le rapport Excel et l'export JSON.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

from .campagne import RACINE, Config, charger_lignage, lancer_campagnes
from .export_qlik import SCRIPT_QLIK, exporter_qlik
from .rapport_excel import ecrire_rapport


def _json_safe(o):
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else round(float(o), 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return str(o)


def exporter_json(campagnes, variation, chemin: Path):
    out = {"campagnes": [], "variation": variation.to_dict(orient="records")}
    for r in campagnes:
        ev = r.evaluation
        out["campagnes"].append({
            "campagne": r.campagne, "date_arrete": r.date_arrete, "scr": r.scr_ref,
            "parametres": asdict(ev.params), "indicateurs": ev.indicateurs,
            "donnees": ev.donnees.reset_index().rename(columns={"index": "donnee_id"}).to_dict(orient="records"),
            "controles": ev.controles.drop(columns=["detail"], errors="ignore").to_dict(orient="records"),
            "axes": {a: ev.par_axe(a).reset_index().to_dict(orient="records") for a in ("maille", "etape", "criteres", "responsable")},
            "gouvernance": r.gouvernance,
            "couverture": r.couverture.to_dict(orient="records"),
            "registre": r.registre.to_dict(orient="records"),
        })
    chemin.write_text(json.dumps(out, default=_json_safe, ensure_ascii=False, indent=1).replace("NaN", "null"), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Campagne QDD Solvabilité 2")
    ap.add_argument("--symetrique", action="store_true", help="écart de rapprochement symétrique borné (amélioration)")
    ap.add_argument("--sans-montant", action="store_true", help="ratio d'anomalie en nombre (méthode du mémoire)")
    ap.add_argument("--sortie", default=str(RACINE / "output"))
    a = ap.parse_args(argv)
    cfg = Config(methode_ecart="symetrique" if a.symetrique else "memoire", ponderation_montant=not a.sans_montant)
    if not cfg.base.exists():
        from scripts.generer_donnees_btp import generer  # noqa
        generer(cfg.base)
    camps, variation = lancer_campagnes(cfg)
    sortie = Path(a.sortie); sortie.mkdir(parents=True, exist_ok=True)
    x = ecrire_rapport(camps, variation, sortie / f"rapport_qdd_{camps[-1].date_arrete}.xlsx")
    exporter_json(camps, variation, sortie / "resultats_campagnes.json")
    # Registre des anomalies, lignage couvert, journal d'exécution (append), export Qlik
    camps[-1].registre.to_csv(sortie / "registre_anomalies.csv", sep=";", index=False)
    camps[-1].couverture.to_csv(sortie / "lignage_couverture.csv", sep=";", index=False)
    jrn = sortie / "journal_executions.csv"
    pd.DataFrame([c.journal for c in camps]).to_csv(jrn, sep=";", index=False, mode="a", header=not jrn.exists())
    ref = pd.read_csv(cfg.referentiels / "referentiel_controles.csv")
    _, flux = charger_lignage(cfg)
    exporter_qlik(camps, variation, ref, flux, sortie / "qlik")
    (sortie / "qlik" / "chargement_qdd.qvs").write_text(SCRIPT_QLIK, encoding="utf-8")
    ind = camps[-1].evaluation.indicateurs
    g = camps[-1].gouvernance
    print(f"Note QDD agrégée {camps[-1].campagne} : {ind['note']:.2%} (objectif {ind['note_min']:.2%}) | "
          f"restitutions QRT conformes {ind['taux_conformite_restitutions']:.0%} | couverture zones de risque "
          f"{g['taux_couverture_zones_risque']:.0%} | anomalies ouvertes {g['nb_anomalies_ouvertes']} -> {x}")


if __name__ == "__main__":
    main()
