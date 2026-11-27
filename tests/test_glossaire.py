"""Glossaire : source unique, exhaustif sur les mots des pages, pages de renvoi existantes ; notice ACPR complète ;
inventaire des tâches : gabarit vide et calcul des heures."""
from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from glossaire import CATEGORIES, GLOSSAIRE, TERMES, TERMES_REQUIS, chercher
from inventaire_taches import calculer, gabarit

RACINE = Path(__file__).resolve().parents[1]


def _pages() -> set:
    arbre = ast.parse((RACINE / "streamlit_app.py").read_text(encoding="utf-8"))
    for n in ast.walk(arbre):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "PAGES":
            return {k.value for k in n.value.keys}
    return set()


def test_glossaire_exhaustif_et_coherent():
    termes = [t.lower() for t, *_ in TERMES]
    assert len(termes) == len(set(termes))  # pas de doublon
    manquants = [m for m in TERMES_REQUIS if not any(m.lower() in t for t in termes)]
    assert not manquants, f"mots employés par l'application sans définition : {manquants}"
    assert {c for _, c, _, _ in TERMES} <= set(CATEGORIES)
    assert {p for *_, p in TERMES if p} <= _pages()
    assert all(len(d) > 20 for _, _, d, _ in TERMES)
    import guide_terrain
    assert guide_terrain.GLOSSAIRE is GLOSSAIRE  # le guide lit la même source
    assert chercher("SCR") and not chercher("mot-qui-n-existe-pas")


def test_notice_acpr_complete():
    df = pd.read_csv(RACINE / "referentiels" / "notice_acpr.csv")
    assert list(df["point"]) == list(range(1, 75))
    assert (df["texte"].str.len() > 30).all() and (df["section"].str.len() > 3).all()
    assert df.loc[df["point"] == 48, "section"].iloc[0].startswith("4.")
    assert "responsables de fonction clé. regard" not in " ".join(df["texte"])  # note de bas de page retirée


def test_inventaire_gabarit_vide_et_calcul():
    assert gabarit().empty
    d = pd.DataFrame([{"Tâche": "Consolider les résultats des contrôles", "Fréquence": "Trimestrielle",
                       "Heures par occurrence": 16.0, "Automatisable": "Oui"},
                      {"Tâche": "Relancer les propriétaires", "Fréquence": "Mensuelle",
                       "Heures par occurrence": 3.0, "Automatisable": "En partie"},
                      {"Tâche": "", "Fréquence": "Mensuelle", "Heures par occurrence": 1.0, "Automatisable": "Oui"}])
    r = calculer(d)
    assert len(r) == 2
    assert list(r["Heures par an"]) == [64.0, 36.0] and list(r["Heures récupérables par an"]) == [64.0, 18.0]


def test_missions_du_poste_et_profil_coherents_avec_l_application():
    import guide_terrain as g
    arbre = ast.parse((RACINE / "streamlit_app.py").read_text(encoding="utf-8"))
    pages = next(n.value for n in ast.walk(arbre)
                 if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "PAGES")
    titres = {k.value: v.elts[1].value for k, v in zip(pages.keys, pages.values)}
    for bloc, mission, clair, cles, couverture, geste in g.MISSIONS:
        assert set(cles) <= set(titres), mission
        assert couverture in g.COUVERTURES_MISSION
    assert {k: titres[k] for k in g.TITRES_PAGES} == g.TITRES_PAGES  # titres identiques à ceux du menu
    assert all(c in g.COUVERTURES_MISSION for *_, c in g.PROFIL)
