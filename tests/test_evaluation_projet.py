"""Avis QDD sur un projet : la grille se déduit du lignage et de la campagne N, le niveau suit les règles écrites, la
fiche reprend les chiffres du moteur."""
from __future__ import annotations

import pytest

from evaluation_projet import EXEMPLE, REGLES, evaluer, flux, markdown, systemes
from qdd_s2.campagne import Config, lancer_campagnes


@pytest.fixture(scope="module")
def n():
    camps, _ = lancer_campagnes(Config())
    r = camps[-1]
    return {"campagne": r.campagne, "date": r.date_arrete, "controles": r.evaluation.controles,
            "donnees": r.evaluation.donnees.reset_index().rename(columns={"index": "donnee_id"}),
            "couverture": r.couverture}  # comme streamlit_app.charger


def test_exemple_chargement_des_sinistres(n):
    ev = evaluer(n, EXEMPLE["systemes"], EXEMPLE["flux"])
    assert list(ev["flux"]["flux_id"]) == ["F05"]
    assert len(ev["donnees"]) == len(ev["critiques"]) == 4  # provisions des 3 segments et date de survenance
    assert ev["niveau"] == "Élevé"
    assert [m[1] for m in ev["motifs"]] == [REGLES[0][1], REGLES[1][1]]
    assert "Provisions sinistres RC décennale" in ev["motifs"][0][2]  # Bloquante dans le moteur
    assert set(ev["lacunes"]["donnee_id"]) == {"date_survenance"}  # F05 sans contrôle pour cette donnée
    assert ev["qrt"] == ["S.17.01", "S.19.01"]
    # chaque point de contrôle retenu contrôle F05 ou une donnée touchée
    k = ev["controles"]
    assert all("F05" in str(f) or d in set(ev["donnees"]["donnee_id"]) for f, d in zip(k["flux"], k["donnee_id"]))
    assert "R03|RC_DECENNALE" in set(k["controle_id"])


def test_systeme_equivaut_a_ses_flux(n):
    par_systeme = evaluer(n, ["Relevé dépositaire"], [])
    par_flux = evaluer(n, [], ["F11", "F13"])
    assert list(par_systeme["flux"]["flux_id"]) == list(par_flux["flux"]["flux_id"]) == ["F11", "F13"]
    assert len(par_systeme["externes"]) == 2 and par_systeme["niveau"] == par_flux["niveau"]


def test_niveaux_moyen_et_vide(n):
    ev = evaluer(n, [], ["F03"])  # comptabilité → S.05.01 : primes RC décennale, conformes
    assert ev["niveau"] == "Moyen" and ev["motifs"][0][1] == REGLES[2][1] and ev["qrt"] == ["S.05.01"]
    assert evaluer(n, [], [])["niveau"] == "—"
    assert len(flux(n)) == 14 and "Outil SCR" in systemes(n)


def test_fiche_reprend_le_moteur(n):
    ev = evaluer(n, [], ["F05"])
    md = markdown({"nom": "Essai", "mep": "15/01/2027"}, ev, {"avis": "Favorable avec réserves", "auteur": "A. B."})
    assert "## Niveau de risque QDD : Élevé" in md and "point 18" in md and "15/01/2027" in md
    rc = ev["critiques"].set_index("donnee_id").loc["provisions_sinistres_RC_DECENNALE"]
    assert f"note {rc['note']:.2%}".replace(".", ",").replace("%", " %") in md
    assert "**Avis :** Favorable avec réserves" in md and "Rejouer R03" in md


def test_fiche_pdf(n):
    from evaluation_projet import ENTETE, PIED
    from export_pdf import pdf_depuis_markdown
    md = markdown({"nom": "Essai"}, evaluer(n, [], ["F05"]), {})
    assert pdf_depuis_markdown(md, "Avis QDD sur un projet", ENTETE, PIED)[:4] == b"%PDF"
