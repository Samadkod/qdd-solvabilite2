"""Fige les lignes en anomalie de chaque campagne du plan dans archives/donnees_en_defaut/ (notice QDD, point 37).

Usage : python scripts/archiver_donnees_en_defaut.py
Une campagne déjà archivée n'est jamais réécrite ; une différence avec l'archive arrête le script.
"""
from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import pandas as pd  # noqa: E402

from archives_defaut import archiver, verifier  # noqa: E402

if __name__ == "__main__":
    plan = pd.read_csv(RACINE / "referentiels" / "plan_campagnes.csv")
    nouvelles = archiver(RACINE / "data" / "btp_fictif.duckdb", plan)
    for a in nouvelles:
        print(f"Archivé : {a['fichier']} ({a['nb_lignes']} lignes, {a['sha256'][:12]}…)")
    v = verifier()
    print(f"{int(v['intacte'].sum())} archive(s) intacte(s) sur {len(v)}")
