"""Dossier de comité : chaque chiffre vient du moteur (valeurs de référence de la campagne N), points à arbitrer
tirés de règles écrites, PDF généré sans glyphe manquant."""
from __future__ import annotations

import logging

import pytest

from comite import markdown_comite, points_a_arbitrer
from export_pdf import pdf_depuis_markdown
from qdd_s2.campagne import Config, lancer_campagnes
from qdd_s2.niveau2 import niveau2_par_campagne


@pytest.fixture(scope="module")
def camps():
    cfg = Config()
    res, var = lancer_campagnes(cfg)
    n2 = niveau2_par_campagne(res, cfg.referentiels)
    out = [{"campagne": r.campagne, "date": r.date_arrete, "ind": r.evaluation.indicateurs,
            "donnees": r.evaluation.donnees.reset_index().rename(columns={"index": "donnee_id"}),
            "controles": r.evaluation.controles, "gouv": r.gouvernance, "registre": r.registre, "niveau2": niv}
           for r, niv in zip(res, n2)]
    return out, var


def test_dossier_comite_chiffres_du_moteur(camps):
    out, var = camps
    md = markdown_comite(out[-1], out[-2], var, genere_le="2026-11-27 09:00")
    for attendu in ("# Comité qualité des données — campagne N", "Arrêté du 30/09/2026",
                    "**Note QDD : 97,49 %** pour un objectif de 97,10 %", "Campagne précédente (N-1) : 98,79 %",
                    "hors tolérance : 2 sur 8", "Restitutions QRT conformes : 10 sur 11", "couvertes : 25 sur 33",
                    "Anomalies ouvertes : 14**, dont 4 de gravité haute", "11 à échéance dépassée",
                    "| Antériorité des contrôles | -0,59 pt |", "Q02 · DOMMAGES_OUVRAGE", "ANO-2026-017",
                    "## 9. Décisions du comité", "données fictives"):
        assert attendu in md, attendu
    assert "conforme ACPR" not in md


def test_points_a_arbitrer_par_regles(camps):
    out, _ = camps
    pts = points_a_arbitrer(out[-1])
    texte = " ".join(pts)
    assert texte.count("Plan de correction") == 2  # les 2 données critiques hors tolérance
    assert pts[0].startswith("Plan de correction pour **Provisions sinistres RC décennale** (Bloquant")
    assert "1 période de retard" in texte and "période(s)" not in texte
    for attendu in ("Provisions sinistres RC décennale", "Date de survenance", "Q02 · DOMMAGES_OUVRAGE",
                    "C07 · TOUS", "R04 · RC_DECENNALE", "8 zones de risque", "Placements obligations"):
        assert attendu in texte, attendu


def test_pdf_du_dossier_sans_glyphe_manquant(camps, caplog):
    out, var = camps
    with caplog.at_level(logging.WARNING):
        from comite import ENTETE, PIED
        pdf = pdf_depuis_markdown(markdown_comite(out[-1], out[-2], var), "Comité QDD", ENTETE, PIED)
    assert pdf.startswith(b"%PDF-") and not [r for r in caplog.records if "glyph" in r.getMessage().lower()]
