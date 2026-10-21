"""Synthèse : chaque tuile reprend le moteur et compte exactement les lignes de la liste qu'elle ouvre."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from synthese import tuiles  # noqa: E402
from qdd_s2.campagne import Config, lancer_campagnes  # noqa: E402

BASE = Path(__file__).resolve().parents[1] / "data" / "btp_fictif.duckdb"


@pytest.fixture(scope="module")
def t():
    if not BASE.exists():
        pytest.skip("base fictive absente")
    camps, _ = lancer_campagnes(Config(base=BASE))
    vues = []
    for c in camps:
        ev = c.evaluation
        vues.append({"campagne": c.campagne, "date": c.date_arrete, "ind": ev.indicateurs, "gouv": c.gouvernance,
                     "donnees": ev.donnees.reset_index().rename(columns={"index": "donnee_id"}),
                     "controles": ev.controles, "couverture": c.couverture, "registre": c.registre,
                     "journal": c.journal})
    return {x.cle: x for x in tuiles(vues[-1], vues[-2])}


def test_valeurs_de_reference(t):
    assert t["note"].valeur == "97,49 %" and t["note"].ton == "vert"
    assert t["objectif"].valeur == "97,10 %"
    assert t["variation"].valeur == "-1,29 pt" and t["variation"].ton == "rouge"
    assert t["hors_tol"].valeur == "2 sur 8"
    assert t["qrt_ko"].valeur == "1 sur 11"
    assert t["zones"].valeur == "8 sur 33"
    assert (t["ouvertes"].valeur, t["haute"].valeur, t["retard"].valeur, t["cloturees"].valeur) == ("14", "4", "11", "3")
    assert t["recurrentes"].valeur == "11"
    assert (t["ctrl_notes"].valeur, t["ctrl_retard"].valeur, t["ctrl_rouges"].valeur, t["ctrl_oranges"].valeur) == \
        ("28", "6", "4", "2")


def test_chaque_liste_correspond_a_sa_tuile(t):
    for x in t.values():
        if x.liste is not None and x.nombre is not None:
            assert len(x.liste) == x.nombre, x.cle
            assert x.valeur.split()[0] == str(x.nombre), x.cle
    assert set(t["hors_tol"].liste["Donnée"]) == {"Provisions sinistres RC décennale", "Date de survenance des sinistres"}
    assert set(t["zones"].liste["Flux"]) == {"F04", "F05", "F06", "F09", "F13"}


def test_bloc_exploitation(t):
    assert t["non_executes"].valeur == "4 sur 20" and t["non_executes"].ton == "orange"
    assert set(t["non_executes"].liste["Contrôle"]) == {"C07", "C08", "R04", "R05"}


def test_evolutions_coloree_selon_le_sens():
    from synthese import Tuile, evolutions
    cour = [Tuile("ouvertes", "b", "t", "14", "orange", "", mesure=14, mieux="bas"),
            Tuile("cloturees", "b", "t", "2", "vert", "", mesure=2, mieux="haut"),
            Tuile("note", "b", "t", "", "vert", "", mesure=0.9745, mieux="haut", unite="point"),
            Tuile("lues", "b", "t", "", "gris", "", mesure=100)]
    prec = [Tuile("ouvertes", "b", "t", "11", "orange", "", mesure=11, mieux="bas"),
            Tuile("cloturees", "b", "t", "0", "gris", "", mesure=0, mieux="haut"),
            Tuile("note", "b", "t", "", "vert", "", mesure=0.9876, mieux="haut", unite="point"),
            Tuile("lues", "b", "t", "", "gris", "", mesure=100)]
    t = {x.cle: x for x in evolutions(cour, prec, "N-1")}
    assert t["ouvertes"].delta == "▲ +3 depuis N-1" and t["ouvertes"].delta_ton == "rouge"  # plus d'anomalies : rouge
    assert t["cloturees"].delta_ton == "vert"
    assert t["note"].delta == "▼ -1,31 pt depuis N-1" and t["note"].delta_ton == "rouge"
    assert t["lues"].delta == "= stable depuis N-1" and t["lues"].delta_ton == "gris"
