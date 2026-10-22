"""Liste de suivi des contrôles : échéance cohérente avec l'antériorité, compteurs égaux au moteur."""
from pathlib import Path

import pandas as pd
import pytest

from qdd_s2.anteriorite import prochaine_echeance
from qdd_s2.campagne import Config, lancer_campagnes
from suivi_controles import detail_campagne, filtrer, liste_suivi

BASE = Path(__file__).resolve().parents[1] / "data" / "btp_fictif.duckdb"


@pytest.mark.parametrize("derniere,freq,attendu", [
    ("2025-12-31", "S", "2026-06-30"),   # C07 : semestriel, dépassée au 30/09/2026
    ("2026-03-31", "T", "2026-06-30"),   # C08
    ("2025-12-31", "A", "2026-12-31"),   # R05 : annuel, à jour
    ("2026-09-30", "T", "2026-12-31"),   # réalisé à l'arrêté
    ("2026-09-15", "T", "2026-09-30"),   # réalisé en cours de trimestre
])
def test_prochaine_echeance(derniere, freq, attendu):
    assert prochaine_echeance(derniere, freq) == pd.Timestamp(attendu)


@pytest.fixture(scope="module")
def vues():
    if not BASE.exists():
        pytest.skip("base fictive absente")
    camps, _ = lancer_campagnes(Config(base=BASE))
    return [{"campagne": c.campagne, "date": c.date_arrete, "controles": c.evaluation.controles} for c in camps]


def test_echeance_coherente_avec_l_anteriorite(vues):
    """En retard <=> échéance passée à l'arrêté, sur les 3 campagnes et tous les points."""
    for v in vues:
        df = liste_suivi(v)
        assert ((df["Échéance"] <= pd.Timestamp(v["date"])) == (df["Retard (périodes)"] > 0)).all(), v["campagne"]


def test_campagne_n(vues):
    df = liste_suivi(vues[-1])
    d = detail_campagne(df)
    assert (d["nb_controles"], d["nb_executes"], d["nb_non_realises"], d["nb_points"]) == (20, 16, 4, len(vues[-1]["controles"]))
    assert set(df.loc[df["Exécution"] == "Non réalisé", "Contrôle"]) == {"C07", "C08", "R04", "R05"}
    assert d["nb_rouge"] == 4 and d["nb_orange"] + d["nb_rouge"] + d["nb_vert"] + d["nb_non_noté"] == d["nb_points"]
    assert len(filtrer(df, resultats=["rouge"])) == 4
    # « en retard » (raccourci de la Synthèse) = points dont l'antériorité est > 0
    assert len(filtrer(df, resultats=["en retard"])) == int((vues[-1]["controles"]["anteriorite"] > 0).sum())
    # un point vert mais non refait reste « à surveiller »
    r05 = df[(df["Contrôle"] == "R05") & (df["Statut"] == "vert")]
    assert len(r05) and r05["À surveiller"].all()
    assert set(filtrer(df, periode="Avant cette campagne")["Contrôle"]) == {"C07", "C08", "R04", "R05"}


def test_saisi_hors_outil_en_n_moins_2(vues):
    """Au 31/03/2026, C08 n'est pas exécuté : son résultat vient de l'historique, daté de l'arrêté."""
    df = liste_suivi(vues[0])
    assert set(df.loc[df["Exécution"] == "Saisi hors outil", "Contrôle"]) == {"C08"}


def test_tendance_sur_les_campagnes(vues):
    """La tendance reprend le résultat du moteur à chaque campagne, jusqu'à celle affichée."""
    df = liste_suivi(vues[-1], None, vues).set_index(["Contrôle", "Segment"])
    assert df.loc[("R03", "RC décennale"), "Tendance"] == [98.59, 98.82, 95.98]   # incident entrepôt en N
    assert df.loc[("C06", "Transverse (tous segments)"), "Tendance"] == [95.64, 99.26, 99.74]  # corrigé après N-2
    assert (df["Tendance"].map(len) == 3).all()
    assert (liste_suivi(vues[1], None, vues[:2])["Tendance"].map(len) == 2).all()
