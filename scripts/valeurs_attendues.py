"""Régénère sas/donnees_demo/valeurs_attendues.csv : les 43 valeurs que sas/98_verifier.sas compare à l'exécution SAS.

À lancer après toute modification d'un calcul ou des données fictives (invariant de parité Python ↔ SAS) :
    python scripts/generer_donnees_btp.py && python scripts/valeurs_attendues.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from qdd_s2.campagne import Config, lancer_campagnes  # noqa: E402

INDICATEURS = ["note", "note_min", "note_avant_degradation", "ecart_objectif", "nb_donnees_critiques",
               "nb_donnees_hors_tolerance", "taux_validation", "taux_conformite_controles",
               "taux_conformite_restitutions"]
GOUVERNANCE = ["taux_couverture_zones_risque", "nb_zones_non_couvertes", "nb_anomalies_ouvertes",
               "nb_anomalies_haute", "nb_anomalies_recurrentes", "nb_anomalies_en_retard", "nb_anomalies_cloturees"]
NOMS_SAS = {"N-1": "N1", "N": "N"}


def lignes(base: Path) -> list[str]:
    camps, var = lancer_campagnes(Config(base=base))
    out = ["campagne;indicateur;valeur_attendue"]
    for c in camps:
        nom = NOMS_SAS[c.campagne]
        for k in INDICATEURS:
            out.append(f"{nom};{k};{float(c.evaluation.indicateurs[k]):.10f}")
        for k in GOUVERNANCE:
            out.append(f"{nom};{k};{float(c.gouvernance[k]):.10f}")
    for i, v in enumerate(var["note"]):
        out.append(f"VARIATION;etape_{i};{float(v):.10f}")
    return out


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "data" / "btp_fictif.duckdb"
    cible = RACINE / "sas" / "donnees_demo" / "valeurs_attendues.csv"
    cible.write_text("\n".join(lignes(base)) + "\n", encoding="utf-8")
    print(cible)
