"""Constats de l'ACPR : référentiel complet et sourcé ; pages de l'application existantes ; aucun chiffre de
l'application écrit en dur (ils sont lus dans le moteur) ; faits de la campagne égaux au moteur."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

import constats_acpr
from constats_acpr import COUVERTURES, charger, faits_campagne, markdown

RACINE = Path(__file__).resolve().parents[1]
SOURCES = ("communiqué de presse du 11/01/2021", "n°144", "n°167")


def _pages() -> set:
    arbre = ast.parse((RACINE / "streamlit_app.py").read_text(encoding="utf-8"))
    for n in ast.walk(arbre):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "PAGES":
            return {k.value for k in n.value.keys}
    return set()


def test_referentiel_complet_et_source():
    df = charger()
    assert len(df) == 15 and df["id"].is_unique
    for col in df.columns:
        if col != "page_app":
            assert (df[col].str.strip() != "").all(), col
    assert set(df["couverture"]) <= set(COUVERTURES)
    assert all(any(s in src for s in SOURCES) for src in df["source"])
    assert df["page"].str.fullmatch(r"\d+").all()
    pages = _pages()
    assert set(df.loc[df["page_app"] != "", "page_app"]) <= pages
    # les chiffres de l'application ne sont pas écrits en dur dans le référentiel
    assert not df["dans_l_application"].str.contains(r"\d+ sur \d+").any()


def test_faits_de_la_campagne_lus_dans_le_moteur():
    from qdd_s2.campagne import Config, lancer_campagnes
    from qdd_s2.niveau2 import niveau2_par_campagne
    cfg = Config()
    camps, _ = lancer_campagnes(cfg)
    r = camps[-1]
    c = {"campagne": r.campagne, "gouv": r.gouvernance, "niveau2": niveau2_par_campagne(camps, cfg.referentiels)[-1],
         "donnees": r.evaluation.donnees.reset_index().rename(columns={"index": "donnee_id"})}
    faits = dict(faits_campagne(c))
    assert faits["Zones de risque critiques couvertes par un contrôle"] == "25 sur 33"
    assert faits["Données critiques par tests de sensibilité"].startswith("7 sur 8 (1 à dire d'expert")
    assert faits["Données externes documentées et contrôlées"] == "0 sur 2"


def test_grille_markdown():
    md = markdown(charger())
    assert md.count("## A") == 15 and "« Le dispositif de contrôle n'apparaît pas suffisamment robuste »" in md


def test_chaque_chiffre_porte_sa_source_et_sa_page():
    """Évaluation du 27/11/2026 : des chiffres de 2022 et 2024 étaient rangés sous la source de la citation (communiqué
    2021), et A07 indiquait 48 à 54 % au lieu de 48 à 70 % (graphique 14, n°167 p. 17)."""
    import re
    df = constats_acpr.charger()
    for r in df.itertuples():
        if "%" in r.chiffre:
            assert re.search(r"n°1(44|67) p\. \d+", r.chiffre), r.id
    assert "48 % (moyens) à 70 % (majeurs)" in df.set_index("id").loc["A07", "chiffre"]


def test_points_de_la_notice_et_constats_lies():
    n = constats_acpr.charger_notice()
    assert sorted(constats_acpr.numeros("20, 24, 29-30")) == [20, 24, 29, 30]
    assert constats_acpr.chercher_notice("50-51")["point"].tolist() == [50, 51]
    assert constats_acpr.chercher_notice("profondeur")["point"].tolist() == [34]
    for r in constats_acpr.charger().itertuples():  # chaque constat renvoie à des points qui existent
        assert constats_acpr.numeros(r.notice_points, n) <= set(n["point"]), r.id
    assert "A03" in constats_acpr.constats_lies({20})["id"].tolist()


def test_outil_notice_renvoie_les_constats_lies():
    import assistant_qdd as a
    r = a.notice_acpr("20")
    assert r["nombre"] == 1 and [x["id"] for x in r["constats_lies"]] == ["A03"]
    assert "Lire la notice" in r["page"]
