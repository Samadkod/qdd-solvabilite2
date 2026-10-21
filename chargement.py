"""Contrôles de chargement (niveau 0) : les données sont-elles arrivées, et les contrôles ont-ils pu tourner ?

Une erreur technique (table vide, chargement partiel, requête en échec) n'est pas une erreur de donnée :
un contrôle qui n'a pas pu s'exécuter ne dit rien de la qualité. Ces vérifications passent donc avant les
autres et sont suivies à part ; elles ne modifient pas la note QDD.

Règle de volumétrie (miroir SAS : sas/08_chargement.sas, macro %qdd_volumetrie) :
  - table absente ou vide à l'arrêté                         -> « Bloquant »
  - table de moins de PETITE_TABLE lignes au trimestre précédent (une ligne par segment, par poste…) :
    tout changement du nombre de lignes                      -> « À expliquer » (segment apparu ou disparu)
  - sinon, variation absolue du nombre de lignes > SEUIL_VARIATION -> « À expliquer »
  - sinon                                                    -> « Normal »
Justification du seuil de 10 % : sur le SI fictif, la variation trimestrielle normale ne dépasse pas 1,2 %
(portefeuille stable : affaires nouvelles moins résiliations). 10 % laisse une marge de plus de huit fois
le normal, sans fausse alerte, tout en détectant un chargement partiel ou doublé (perte d'un segment, d'un
mois, filtre oublié). À recalibrer sur l'historique réel : plus forte variation observée sur 8 trimestres,
plus une marge.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb
import pandas as pd

SEUIL_VARIATION = 0.10
PETITE_TABLE = 50
SQL_CONTROLES = Path(__file__).resolve().parent / "sql" / "controles"


def _volumes(c: dict | None) -> dict[str, int]:
    if not c or not c.get("journal"):
        return {}
    v = c["journal"]["volumetries_sources"]
    return json.loads(v) if isinstance(v, str) else dict(v)


def statut_volume(prec: int | None, cour: int | None) -> tuple[str, str]:
    """(statut, explication) pour une table, selon la règle décrite en tête de module."""
    if cour is None:
        return "Bloquant", "Table absente du chargement."
    if cour == 0:
        return "Bloquant", "Table vide à la date d'arrêté."
    if not prec:  # pas de trimestre précédent, ou table vide au trimestre précédent (comme en SAS)
        return "Sans référence", "Pas de trimestre précédent pour comparer."
    if prec < PETITE_TABLE:
        if cour != prec:
            return "À expliquer", (f"Petite table ({prec} lignes, une par segment ou poste) : le nombre de lignes "
                                   f"a changé ({prec} → {cour}).")
        return "Normal", "Même nombre de lignes qu'au trimestre précédent."
    var = round(cour / prec - 1, 10)  # arrondi : +10 % pile reste sous le seuil (même règle en SAS)
    v, s = f"{var * 100:+.1f} %".replace(".", ","), f"{SEUIL_VARIATION * 100:.0f} %"
    if abs(var) > SEUIL_VARIATION:
        return "À expliquer", f"Variation de {v} : au-delà du seuil de {s}."
    return "Normal", f"Variation de {v}, sous le seuil de {s}."


def volumetrie(c: dict, prev: dict | None) -> pd.DataFrame:
    """Une ligne par table source : lignes au trimestre précédent, à l'arrêté, variation et statut."""
    cour, prec = _volumes(c), _volumes(prev)
    lignes = []
    for t in sorted(set(cour) | set(prec)):
        a, b = prec.get(t) if prev else None, cour.get(t)
        statut, expl = statut_volume(a, b)
        lignes.append({"Table": t, "Trimestre précédent": a, "Arrêté": b,
                       "Variation": (b / a - 1) if (a and b is not None) else None,
                       "Statut": statut, "Explication": expl})
    return pd.DataFrame(lignes)


def execution(base: Path | str, arrete: str, referentiel: pd.DataFrame) -> pd.DataFrame:
    """Rejoue chaque requête de contrôle et note si elle s'exécute, en combien de temps, et l'erreur sinon."""
    out = []
    con = duckdb.connect(str(base), read_only=True)
    try:
        for r in referentiel.itertuples():
            sql = (SQL_CONTROLES / r.fichier_sql).read_text(encoding="utf-8")
            t0 = time.perf_counter()
            try:
                n = len(con.execute(sql, {"arrete": arrete}).df())
                statut, message = ("Exécuté", "") if n else ("Échec technique", "La requête ne renvoie aucune ligne.")
            except Exception as e:  # noqa: BLE001 — on consigne toute erreur technique, sans arrêter la campagne
                n, statut, message = 0, "Échec technique", f"{type(e).__name__} : {e}"[:300]
            out.append({"Contrôle": r.controle_id, "Fichier": r.fichier_sql, "Statut": statut,
                        "Durée (ms)": round((time.perf_counter() - t0) * 1000, 1), "Mailles renvoyées": n,
                        "Message": message})
    finally:
        con.close()
    return pd.DataFrame(out)
