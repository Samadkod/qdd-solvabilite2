"""Régénère sas/donnees_demo/relances_scr.csv : les relances du moteur SCR que lit la version SAS.

La version SAS ne recalcule pas le SCR (en entreprise, c'est le moteur SCR de l'organisme qui le
fait) : elle lit, pour chaque arrêté du plan de campagnes et chaque donnée candidate, le SCR de
référence (choc 0) et le SCR relancé après chaque choc. %qdd_sensibilites en déduit sensibilité et
non-linéarité, comme qdd_s2.sensibilite.

À lancer après toute modification des données fictives ou du plan de campagnes :
    python scripts/generer_donnees_btp.py && python scripts/relances_scr.py && python scripts/valeurs_attendues.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from qdd_s2.campagne import Config, entrees_scr  # noqa: E402
from qdd_s2.sensibilite import scr_formule_standard_simplifiee as scr  # noqa: E402

# mêmes identifiants que le dictionnaire des données (voir qdd_s2.campagne.lancer_campagnes)
RENOMMER = {"placements_actions": "placements_ACTIONS", "placements_obligations": "placements_OBLIGATIONS"}
CHOCS = (0.0, -0.15, 0.05, 0.15, 0.30)  # 0 = référence ; 0,15 = choc retenu ; les autres = test de linéarité


def lignes(base: Path) -> list[str]:
    plan = pd.read_csv(RACINE / "referentiels" / "plan_campagnes.csv")
    out = ["arrete;donnee_id;choc;valeur;scr"]
    con = duckdb.connect(str(base), read_only=True)
    try:
        for arrete in plan["date_arrete"]:
            x = entrees_scr(con, arrete)
            for k, v in x.items():
                for c in CHOCS:
                    y = dict(x)
                    y[k] = v * (1 + c)
                    out.append(f"{arrete};{RENOMMER.get(k, k)};{c};{v!r};{scr(y)!r}")
    finally:
        con.close()
    return out


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Config().base
    cible = RACINE / "sas" / "donnees_demo" / "relances_scr.csv"
    cible.write_text("\n".join(lignes(base)) + "\n", encoding="utf-8")
    print(cible)
