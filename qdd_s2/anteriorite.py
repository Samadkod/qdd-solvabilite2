"""Traitement des contrôles non réalisés (mémoire §2.4.2)."""
from __future__ import annotations

from datetime import date

import pandas as pd

# Fréquence -> nombre de mois entre deux réalisations attendues
FREQ_MOIS = {"M": 1, "T": 3, "S": 6, "A": 12}


def _dates_attendues(debut: date, fin: date, freq_mois: int) -> list[pd.Timestamp]:
    """Fins de période calendaires (mois multiples de freq) dans ]debut ; fin]."""
    ends = pd.date_range(pd.Timestamp(debut), pd.Timestamp(fin) + pd.offsets.MonthEnd(0), freq="ME")
    return [d for d in ends if d.month % freq_mois == 0 and pd.Timestamp(debut) < d <= pd.Timestamp(fin)]


def anteriorite(date_derniere_real, date_campagne, frequence: str, base: str = "frequence") -> float:
    """Éq. 34 / 35.

    base="frequence" : nombre de réalisations attendues manquées (AntFreq).
    base="annuelle"  : AntFreq exprimée en années (AntFreq x mois / 12).
    """
    if pd.isna(date_derniere_real):
        raise ValueError("Contrôle jamais réalisé : à traiter comme résultat 0 % (voir moteur).")
    fm = FREQ_MOIS[frequence]
    n = len(_dates_attendues(pd.Timestamp(date_derniere_real).date(), pd.Timestamp(date_campagne).date(), fm))
    return float(n) if base == "frequence" else n * fm / 12.0


def degrader(resultat: float, ant: float, coef: float, methode: str = "simple") -> float:
    """Éq. 36 (simple, retenue par le mémoire) ou éq. 37 (composée)."""
    if methode == "simple":
        return resultat * max(0.0, 1.0 - coef * ant)
    return resultat * (1.0 - coef) ** ant
