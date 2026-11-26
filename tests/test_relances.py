"""Relances aux propriétaires : chaque point à relancer vient du registre ou des points de contrôle, comptes égaux
au moteur (tuiles de la Synthèse), message complet par responsable."""
from __future__ import annotations

import pytest

from qdd_s2.campagne import Config, lancer_campagnes
from relances import BIENTOT, DEPASSEE, RETARD, message, relances, synthese, tous_les_messages


@pytest.fixture(scope="module")
def n():
    camps, _ = lancer_campagnes(Config())
    r = camps[-1]
    ev = r.evaluation
    return {"campagne": r.campagne, "date": r.date_arrete, "registre": r.registre, "controles": ev.controles,
            "gouv": r.gouvernance}


def test_comptes_egaux_au_moteur(n):
    df = relances(n)
    g = n["gouv"]
    anomalies = df[df["nature"].str.startswith("Anomalie")]
    assert len(anomalies) == g["nb_anomalies_ouvertes"] == 14
    assert (df["urgence"] == DEPASSEE).sum() == g["nb_anomalies_en_retard"] == 11  # = tuile de la Synthèse
    assert (df["urgence"] == RETARD).sum() == int((n["controles"]["anteriorite"] > 0).sum()) == 6
    assert set(df.loc[df["urgence"] == BIENTOT, "reference"]) == {"ANO-2026-016", "ANO-2026-017"}  # 30/10/2026
    syn = synthese(df)
    assert syn["total"].sum() == len(df) and syn.iloc[0]["responsable"] == "Direction sinistres"


def test_message_complet_et_chiffres_du_moteur(n):
    df = relances(n)
    m = message("Contrôle de gestion", df, "N", n["date"])
    assert m.startswith("Objet : Qualité des données – campagne N (arrêté du 30/09/2026)")
    assert "R04 · RC_DECENNALE" in m and "94,59 %" in m and "99,32 %" in m and "Bloquant" in m
    assert "ANO-2026-016" in m and "ANO-2026-015" in m and "Contrôles à refaire (3)" in m
    assert "Atelier de résolution" in m and "Direction sinistres" not in m  # uniquement ses points
    tout = tous_les_messages(df, "N", n["date"])
    assert tout.count("Objet :") == df["responsable"].nunique()


def test_message_ecrit_a_la_francaise(n):
    m = message("Contrôle de gestion", relances(n), "N", n["date"])
    assert "94,59 % < seuil 99,32 %" in m and "94.59%" not in m
