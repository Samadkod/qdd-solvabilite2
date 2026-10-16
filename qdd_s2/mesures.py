"""Résultat quantitatif d'un contrôle (mémoire §2.4.1).

Deux familles :
- rapprochement : mesure de non-QDD = écart entre sources ;
- cohérence : mesure de non-QDD = ratio d'anomalies.

Résultat du contrôle : C = 100 % - mesure de non-QDD, borné dans [0 ; 1]
(le mémoire ne borne pas l'éq. 27 : un écart max/min - 1 > 100 % donnerait
une note négative).
"""
from __future__ import annotations

from itertools import permutations
from typing import Iterable, Sequence

import numpy as np


# --------------------------------------------------------------------------
# Rapprochement
# --------------------------------------------------------------------------
def ecart_relatif(b_ref: float, b_comp: float) -> float:
    """Éq. 28 du mémoire : |b_comp / b_ref - 1| avec conventions si b_ref = 0."""
    if b_ref != 0:
        return abs(b_comp / b_ref - 1)
    return 0.0 if b_comp == b_ref else 1.0


def ecart_symetrique(a: float, b: float) -> float:
    """AMÉLIORATION : min(1, |a - b| / max(|a|, |b|)).

    - symétrique (pas besoin de source de référence),
    - borné dans [0 ; 1] (donc résultat de contrôle jamais négatif),
    - fonctionne avec des montants négatifs (recours, boni/mali) : deux
      montants de signes opposés = désaccord total (100 %).
    """
    m = max(abs(a), abs(b))
    return 0.0 if m == 0 else min(1.0, abs(a - b) / m)


def mesure_rapprochement(
    valeurs: Sequence[float],
    justifies: Iterable[tuple[int, int]] = (),
    methode: str = "memoire",
) -> float:
    """Éq. 30 : max des écarts relatifs injustifiés des sources deux à deux.

    justifies : paires d'indices (k, j) dont l'écart est justifié (exclu).
    methode : "memoire" (éq. 28, prudente, non bornée) ou "symetrique".
    """
    just = {tuple(p) for p in justifies} | {(j, k) for k, j in justifies}
    f = ecart_relatif if methode == "memoire" else ecart_symetrique
    ecarts = [f(valeurs[k], valeurs[j]) for k, j in permutations(range(len(valeurs)), 2)
              if (k, j) not in just]
    return max(ecarts) if ecarts else 0.0


def mesure_rapprochement_maille(
    table: Sequence[Sequence[float]], option: int = 3, methode: str = "memoire"
) -> float:
    """Contrôle de rapprochement formalisé par maille (tableau 17).

    table[m][k] = valeur de la maille m dans la source k.
    option 1 : écart des totaux ; 2 : moyenne simple des écarts par maille ;
    3 : moyenne pondérée par max_k |b_km| (éq. 32, retenue par le mémoire).
    """
    arr = np.asarray(table, dtype=float)
    if option == 1:
        return mesure_rapprochement(arr.sum(axis=0), methode=methode)
    e = np.array([mesure_rapprochement(row, methode=methode) for row in arr])
    if option == 2:
        return float(e.mean())
    w = np.abs(arr).max(axis=1)
    return float((w * e).sum() / w.sum()) if w.sum() else 0.0


# --------------------------------------------------------------------------
# Cohérence
# --------------------------------------------------------------------------
def ratio_anomalie(anomalies: Sequence[bool], montants: Sequence[float] | None = None) -> float:
    """Éq. 33 : nb anomalies / nb éléments contrôlés.

    AMÉLIORATION : si `montants` est fourni, ratio pondéré en montant
    (montant en anomalie / montant total), ce qui rend la mesure homogène
    avec un écart relatif de rapprochement et donc avec l'interprétation
    « 1 - note = incertitude relative sur la donnée » utilisée pour la tolérance.
    """
    a = np.asarray(anomalies, dtype=bool)
    if a.size == 0:
        return 0.0
    if montants is None:
        return float(a.mean())
    m = np.abs(np.asarray(montants, dtype=float))
    return float(m[a].sum() / m.sum()) if m.sum() else float(a.mean())


def resultat_controle(mesure_non_qdd: float) -> float:
    """Éq. 27 bornée : C = clip(1 - mesure, 0, 1)."""
    return float(min(1.0, max(0.0, 1.0 - mesure_non_qdd)))
