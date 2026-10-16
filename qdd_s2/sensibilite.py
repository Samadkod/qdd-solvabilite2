"""Sensibilité du SCR aux données (mémoire §2.2.1) + test de linéarité.

s_d = (|SCR_d - SCR_ref| / SCR_ref) / choc_d          (éq. 4)

AMÉLIORATION : le mémoire pose l'hypothèse « forte » de linéarité sans la
tester (sauf sur les primes). On calcule ici la sensibilité pour plusieurs
chocs (+/-) et un indicateur de non-linéarité = écart relatif max entre les
sensibilités obtenues. Au-delà d'un seuil (10 % par défaut), la sensibilité
de la donnée doit être revue à dire d'expert.

Le module fournit aussi une formule standard SIMPLIFIÉE (non-vie primes &
réserves + marché + opérationnel) pour un assureur dommages BTP fictif.
Paramètres inspirés du règlement délégué 2015/35 (annexe II pour les
écarts-types) mais NON réglementaires : à remplacer par le moteur SCR
de l'organisme.
"""
from __future__ import annotations

from typing import Callable, Mapping

import numpy as np
import pandas as pd

# Écarts-types (prime, réserve) par segment — inspirés de l'annexe II du RD 2015/35
SIGMA = {
    "RC_DECENNALE": (0.14, 0.11),   # responsabilité civile générale
    "DOMMAGES_OUVRAGE": (0.08, 0.10),  # incendie et autres dommages aux biens
    "AUTO_FLOTTE": (0.08, 0.08),    # autre assurance des véhicules à moteur
}
# Corrélations entre segments : ILLUSTRATIVES
CORR_SEG = pd.DataFrame(
    [[1, 0.25, 0.25], [0.25, 1, 0.25], [0.25, 0.25, 1]],
    index=list(SIGMA), columns=list(SIGMA))


def scr_formule_standard_simplifiee(x: Mapping[str, float]) -> float:
    """SCR jouet. Entrées attendues (montants en M€) :
    primes_acquises_<SEG>, provisions_sinistres_<SEG>, taux_cession,
    placements_actions, placements_obligations.
    """
    net = 1 - x["taux_cession"]
    sig, vol = {}, {}
    for seg, (sp, sr) in SIGMA.items():
        vp = x[f"primes_acquises_{seg}"] * net
        vr = x[f"provisions_sinistres_{seg}"] * net
        v = vp + vr
        sig[seg] = np.sqrt((sp * vp) ** 2 + sp * vp * sr * vr + (sr * vr) ** 2) / v if v else 0
        vol[seg] = v
    sv = np.array([sig[s] * vol[s] for s in SIGMA])
    scr_nl = 3 * np.sqrt(sv @ CORR_SEG.values @ sv)
    scr_mkt = np.sqrt((0.39 * x["placements_actions"]) ** 2 + (0.045 * x["placements_obligations"]) ** 2)
    bscr = np.sqrt(scr_nl ** 2 + scr_mkt ** 2 + 2 * 0.25 * scr_nl * scr_mkt)
    primes = sum(x[f"primes_acquises_{s}"] for s in SIGMA)
    prov = sum(x[f"provisions_sinistres_{s}"] for s in SIGMA)
    op = min(0.3 * bscr, max(0.03 * primes, 0.03 * prov))
    return float(bscr + op)


def sensibilites(
    scr: Callable[[Mapping[str, float]], float],
    entrees: Mapping[str, float],
    choc: float = 0.15,
    chocs_test: tuple = (-0.15, 0.05, 0.30),
    seuil_non_linearite: float = 0.10,
) -> pd.DataFrame:
    """Sensibilité de chaque entrée + diagnostic de linéarité."""
    ref = scr(entrees)
    lignes = []
    for k, v in entrees.items():
        def s_pour(c):
            x = dict(entrees)
            x[k] = v * (1 + c)
            return abs(scr(x) - ref) / ref / abs(c)
        s = s_pour(choc)
        tests = [s_pour(c) for c in chocs_test]
        nl = max(abs(t - s) for t in tests) / s if s > 0 else 0.0
        lignes.append({"donnee_id": k, "valeur": v, "sensibilite": s,
                       **{f"s_choc_{c:+.0%}": t for c, t in zip(chocs_test, tests)},
                       "non_linearite": nl, "lineaire": nl <= seuil_non_linearite})
    out = pd.DataFrame(lignes).set_index("donnee_id")
    out.attrs["scr_ref"] = ref
    return out
