"""Les explications « d'où sortent les chiffres » recalculent exactement les résultats du moteur."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from explications import decortiquer_donnee, decortiquer_globale, lire_axe, lire_variation, texte_controle  # noqa: E402
from qdd_s2.campagne import Config, lancer_campagnes  # noqa: E402
from qdd_s2.moteur import Parametres  # noqa: E402

BASE = Path(__file__).resolve().parents[1] / "data" / "btp_fictif.duckdb"


def _vue(c):
    """Même structure que la campagne vue par l'application (streamlit_app.campagnes)."""
    ev = c.evaluation
    return {"campagne": c.campagne, "date": c.date_arrete, "scr": c.scr_ref, "ind": ev.indicateurs,
            "donnees": ev.donnees.reset_index().rename(columns={"index": "donnee_id"}), "controles": ev.controles,
            "sens": c.sensibilites.reset_index(), "params": ev.params,
            "axes": {"criteres": ev.par_axe("criteres").reset_index()}}


@pytest.fixture(scope="module", params=[Parametres(), Parametres(coef_degradation=0.10, methode_degradation="composee")])
def campagnes(request):
    if not BASE.exists():
        pytest.skip("base fictive absente (lancer scripts/generer_donnees_btp.py)")
    camps, var = lancer_campagnes(Config(base=BASE, params=request.param))
    return [_vue(c) for c in camps], var


def test_recalcul_par_donnee_identique_au_moteur(campagnes):
    for c in campagnes[0]:
        d = c["donnees"].set_index("donnee_id")
        for did in d.index[d["critique"] & (d["nb_controles"] > 0)]:
            x = decortiquer_donnee(c, did)
            assert x["note"] == pytest.approx(d.loc[did, "note"], abs=1e-12), did
            assert x["note_min"] == pytest.approx(d.loc[did, "note_min"], abs=1e-12), did
            assert x["statut"] == d.loc[did, "statut"], did
            assert (x["controles"]["recalcul"] - x["controles"]["resultat"]).abs().max() < 1e-12, did


def test_recalcul_global_identique_au_moteur(campagnes):
    for c in campagnes[0]:
        gl = decortiquer_globale(c)
        assert gl["note"] == pytest.approx(c["ind"]["note"], abs=1e-12)
        assert gl["objectif"] == pytest.approx(c["ind"]["note_min"], abs=1e-12)
        assert gl["objectif_formule"] == pytest.approx(c["ind"]["note_min"], abs=1e-12)


def test_textes_campagne_n():
    if not BASE.exists():
        pytest.skip("base fictive absente")
    camps, var = lancer_campagnes(Config(base=BASE))
    c = _vue(camps[-1])
    ctrl = c["controles"]
    c06 = ctrl[ctrl["controle_id"] == "C06|TOUS"].iloc[0]
    assert "**19 lignes en erreur sur 4957**" in texte_controle(c06, c["date"]) and "**99,74 %**" in texte_controle(c06, c["date"])
    c07 = ctrl[ctrl["controle_id"] == "C07|TOUS"].iloc[0]
    assert "n'a pas été refait" in texte_controle(c07, c["date"])
    r04 = ctrl[ctrl["controle_id"] == "R04|RC_DECENNALE"].iloc[0]
    assert texte_controle(r04, c["date"]).startswith("*Mesuré lors de la campagne du 30/06/2026")
    x = decortiquer_donnee(c, "date_survenance")
    assert round(x["note"], 4) == 0.9671 and x["statut"] == "orange"
    lv = lire_variation(var)
    assert "baisse de 1,29 point" in lv and "-0,70 point" in lv and "-0,59 point" in lv
    assert "Comment lire ce graphique" in lire_axe(c["axes"]["criteres"].rename(columns={"criteres": "modalite"}),
                                                   "criteres")


def test_donnee_a_dire_d_expert():
    if not BASE.exists():
        pytest.skip("base fictive absente")
    camps, _ = lancer_campagnes(Config(base=BASE))
    x = decortiquer_donnee(_vue(camps[-1]), "date_survenance")
    assert x["a_dire_expert"] and x["sensibilite"] == pytest.approx(x["moyenne_mesurees"], abs=1e-12)
    y = decortiquer_donnee(_vue(camps[-1]), "provisions_sinistres_RC_DECENNALE")
    assert not y["a_dire_expert"]
