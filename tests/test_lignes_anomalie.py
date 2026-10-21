"""Lignes en anomalie : maille par maille, autant de lignes que d'anomalies comptées par le contrôle agrégé."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lignes_anomalie as la  # noqa: E402

BASE = Path(__file__).resolve().parents[1] / "data" / "btp_fictif.duckdb"


@pytest.mark.parametrize("arrete", ["2026-06-30", "2026-09-30"])
def test_lignes_egales_au_controle_agrege(arrete):
    if not BASE.exists():
        pytest.skip("base fictive absente")
    lig = la.lignes(BASE, arrete)
    agg = la.comptes_agreges(BASE, arrete)
    m = (lig.groupby(["controle", "maille"])["poids"].sum().rename("lignes").reset_index()
         .merge(agg, on=["controle", "maille"], how="outer").fillna(0))
    assert (m["lignes"] == m["n_anomalies"]).all(), m[m["lignes"] != m["n_anomalies"]]
    assert set(agg["controle"]) == {f"C{i:02d}" for i in range(1, 11)}


def test_valeurs_campagne_n():
    if not BASE.exists():
        pytest.skip("base fictive absente")
    lig = la.lignes(BASE, "2026-09-30")
    n = lig.groupby("controle")["poids"].sum().to_dict()
    assert (n["C01"], n["C03"], n["C04"], n["C06"], n["C08"], n["C10"]) == (54, 6, 12, 42, 14, 89)
    g = la.regroupements(lig)
    assert g["Lignes en anomalie"].sum() == lig["poids"].sum()


def test_catalogue_couvre_les_20_regles():
    import pandas as pd
    ctrl = pd.DataFrame({"controle_id": ["C01|RC_DECENNALE"], "statut": ["vert"], "realise_campagne": [True]})
    cat = la.catalogue(ctrl, pd.DataFrame(columns=["controle", "poids"]))
    assert len(cat) == 20 and set(cat["ID"]) == set(la.MESSAGES)
