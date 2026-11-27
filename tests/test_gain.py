"""Gain de note avant correction : recalcul par le moteur sur une copie, hypothèses explicites, valeurs de N."""
from __future__ import annotations

import pytest

from gain import _entrees, _recalcul, par_donnee, simulations
from qdd_s2.campagne import Config, lancer_campagnes


@pytest.fixture(scope="module")
def n():
    camps, var = lancer_campagnes(Config())
    r = camps[-1]
    ev = r.evaluation
    c = {"campagne": r.campagne, "date": r.date_arrete, "ind": ev.indicateurs, "gouv": r.gouvernance,
         "registre": r.registre, "controles": ev.controles, "params": ev.params,
         "donnees": ev.donnees.reset_index().rename(columns={"index": "donnee_id"})}
    return c, camps, var


def test_sans_hypothese_le_recalcul_redonne_la_note(n):
    c, _, _ = n
    don, base, crit = _entrees(c)
    assert _recalcul(c, c["params"], base, don, crit).indicateurs["note"] == pytest.approx(c["ind"]["note"], abs=1e-12)


def test_gains_point_par_point(n):
    c, _, _ = n
    s = simulations(c, c["params"]).set_index(["point", "hypothese"])
    top = s["gain_points"].idxmax()
    assert top == ("R03|RC_DECENNALE", "Corrigé et refait") and s.loc[top, "gain_points"] == pytest.approx(1.064, abs=1e-3)
    assert s.loc[("C10|TOUS", "Corrigé et refait"), "gain_points"] == pytest.approx(0, abs=1e-9)  # non critique
    assert s.loc[("Q02|DOMMAGES_OUVRAGE", "Corrigé et refait"), "gain_points"] == pytest.approx(0, abs=1e-9)  # QRT
    refait = s.loc[("C07|TOUS", "Refait (même résultat)")]
    assert refait["statut_donnee_apres"] == "Conforme" and refait["gain_points"] == pytest.approx(0.308, abs=1e-3)
    assert s.loc[("R04|RC_DECENNALE", "Refait (même résultat)"), "statut_point_apres"] == "Conforme"


def test_par_donnee_et_plan_complet(n):
    c, _, _ = n
    p = par_donnee(c, c["params"]).set_index(["donnee_id", "hypothese"])
    rc = "provisions_sinistres_RC_DECENNALE"
    assert p.loc[(rc, "Tous ses contrôles en retard refaits"), "statut_apres"] == "À corriger"
    assert p.loc[(rc, "Tous ses contrôles corrigés et refaits"), "statut_apres"] == "Conforme"
    assert p.loc[("date_survenance", "Tous ses contrôles en retard refaits"), "statut_apres"] == "Conforme"
    assert p.loc[("toutes", "Plan complet : tout corrigé et refait"), "note_apres"] == pytest.approx(1.0)


def test_dossier_de_comite_avec_les_gains(n):
    from comite import markdown_comite
    c, camps, var = n
    md = markdown_comite(dict(c, niveau2=None), None, None, gains=simulations(c, c["params"]),
                         par_donnee=par_donnee(c, c["params"]))
    assert "## 8. Ce que rapporteraient les corrections" in md and "## 10. Décisions du comité" in md
    assert "| R03 · RC_DECENNALE | Corrigé et refait | +1,06 pt |" in md
