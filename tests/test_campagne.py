"""Tests bout en bout sur le SI fictif + parité SQL / Python."""
from pathlib import Path

import duckdb
import pytest

from qdd_s2.campagne import RACINE, Config, lancer_campagnes
from qdd_s2.sensibilite import scr_formule_standard_simplifiee, sensibilites
from scripts.generer_donnees_btp import generer


@pytest.fixture(scope="module")
def campagnes(tmp_path_factory):
    base = tmp_path_factory.mktemp("db") / "btp.duckdb"
    generer(base)
    return lancer_campagnes(Config(base=base))


def test_deux_campagnes_et_variation(campagnes):
    camps, var = campagnes
    assert [c.campagne for c in camps] == ["N-1", "N"]
    # la décomposition explique exactement la variation de la note
    assert var["impact"].sum() == pytest.approx(var["note"].iloc[-1] - var["note"].iloc[0], abs=1e-12)
    assert var["note"].iloc[-1] == pytest.approx(camps[-1].evaluation.indicateurs["note"], abs=1e-12)


def test_incident_entrepot_detecte(campagnes):
    """L'incident injecté en N (provisions RC décennale altérées dans l'entrepôt) passe au rouge."""
    camps, _ = campagnes
    d = camps[-1].evaluation.donnees
    assert d.loc["provisions_sinistres_RC_DECENNALE", "statut"] == "rouge"
    assert camps[0].evaluation.donnees.loc["provisions_sinistres_RC_DECENNALE", "statut"] != "rouge"


def test_controles_non_realises_degrades(campagnes):
    camps, _ = campagnes
    c = camps[-1].evaluation.controles.set_index("controle_id")
    assert c.loc["C08|ACTIONS", "anteriorite"] == 2          # dernier : 31/03 ; attendus 30/06 et 30/09
    assert c.loc["R04|RC_DECENNALE", "anteriorite"] == 1     # réalisé en N-1 seulement
    assert c.loc["C07|TOUS", "anteriorite"] == 1             # semestriel, dernier 31/12/2025
    assert c.loc["R05|DOMMAGES_OUVRAGE", "anteriorite"] == 0  # annuel, échéance 31/12 non atteinte
    r = c.loc["C08|ACTIONS"]
    assert r.resultat == pytest.approx(r.resultat_brut * (1 - 0.05 * 2))


def test_parite_sql_python(campagnes):
    camps, _ = campagnes
    ev = camps[-1].evaluation
    con = duckdb.connect()
    pts = ev.controles[["controle_id", "donnee_id", "poids", "resultat_brut", "anteriorite", "inclus_note"]].copy()
    pts["inclus_note"] = pts["inclus_note"].astype(int)
    con.register("points", pts)
    don = ev.donnees.reset_index().rename(columns={"index": "donnee_id"})
    don["critique"] = don["critique"].astype(int)
    con.register("donnees", don[["donnee_id", "sensibilite", "critique"]])
    sql = (RACINE / "sql" / "agregation_note_qdd.sql").read_text(encoding="utf-8")
    note, note_min, note_brute, n = con.execute(sql, {"coef": ev.params.coef_degradation,
                                                      "dscr": ev.params.delta_scr_max}).fetchone()
    i = ev.indicateurs
    assert note == pytest.approx(i["note"], abs=1e-12)
    assert note_min == pytest.approx(i["note_min"], abs=1e-12)
    assert note_brute == pytest.approx(i["note_avant_degradation"], abs=1e-12)
    assert n == i["nb_donnees_critiques"]


def test_linearite_scr_jouet():
    x = {"primes_acquises_RC_DECENNALE": 60, "primes_acquises_DOMMAGES_OUVRAGE": 25, "primes_acquises_AUTO_FLOTTE": 15,
         "provisions_sinistres_RC_DECENNALE": 400, "provisions_sinistres_DOMMAGES_OUVRAGE": 120,
         "provisions_sinistres_AUTO_FLOTTE": 18, "taux_cession": .2, "placements_actions": 40,
         "placements_obligations": 360}
    s = sensibilites(scr_formule_standard_simplifiee, x)
    assert s.loc["provisions_sinistres_RC_DECENNALE", "sensibilite"] > s.loc["primes_acquises_RC_DECENNALE", "sensibilite"]
    assert s["lineaire"].dtype == bool


def test_parite_javascript(campagnes, tmp_path):
    """Le moteur JavaScript de l'atelier donne exactement les mêmes résultats (si Node est disponible)."""
    import json
    import shutil
    import subprocess
    if shutil.which("node") is None:
        pytest.skip("Node non disponible")
    from qdd_s2.__main__ import exporter_json
    camps, var = campagnes
    f = tmp_path / "r.json"
    exporter_json(camps, var, f)
    r = subprocess.run(["node", str(RACINE / "tests" / "parite_js.mjs"), str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:]
