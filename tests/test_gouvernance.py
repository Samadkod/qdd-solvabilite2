"""Tests des briques de gouvernance : couverture du lignage, registre des anomalies,
contrôles de restitution, journal."""
import json

import pandas as pd
import pytest

from qdd_s2 import Parametres, evaluer
from qdd_s2.gouvernance import (couverture_lignage, indicateurs_anomalies, indicateurs_couverture,
                                maj_registre)

FLUX = pd.DataFrame({"flux_id": ["F1", "F2", "F3"], "systeme_source": ["A", "B", "C"],
                     "systeme_cible": ["B", "C", "D"], "traitement": ["t1", "t2", "t3"],
                     "mode": "Automatique", "zone_risque": [True, True, False]})
LIG = pd.DataFrame({"donnee_id": ["d1", "d1", "d1", "d2"], "flux_id": ["F1", "F2", "F3", "F1"], "ordre": [1, 2, 3, 1]})


def _ev(resultats, anteriorites, sens=None, fixe=None, inclus=None):
    don = pd.DataFrame({"sensibilite": sens or {"d1": 0.10, "d2": 0.005},
                        "libelle": ["Donnée 1", "Donnée 2"], "proprietaire": ["P1", "P2"]}, index=["d1", "d2"])
    n = len(resultats)
    ctrl = pd.DataFrame({
        "controle_id": [f"K{i}|TOUS" for i in range(n)], "controle": [f"K{i}" for i in range(n)],
        "donnee_id": ["d1"] * n, "libelle": "ctrl", "responsable": "R", "flux": ["F1"] * n,
        "resultat_brut": resultats, "anteriorite": anteriorites,
        "seuil_fixe": fixe or [None] * n, "inclus_note": inclus or [1] * n})
    return evaluer(don, ctrl, Parametres(delta_scr_max=0.005))


def test_couverture_zone_risque():
    ev = _ev([1.0], [0])
    couv = couverture_lignage(LIG, FLUX, ev.controles, ev.donnees)
    ind = indicateurs_couverture(couv)
    # d1 critique : F1 couvert, F2 non couvert, F3 hors zone de risque ; d2 non critique : ignorée
    assert ind["nb_zones_risque_critiques"] == 2
    assert ind["nb_zones_non_couvertes"] == 1
    assert ind["flux_non_couverts"] == ["F2"]
    assert ind["taux_couverture_zones_risque"] == 0.5


def test_cycle_de_vie_registre():
    # Campagne 1 : K0 rouge réalisé (qualité), K1 dégradé par antériorité (non réalisé)
    ev1 = _ev([0.90, 0.99], [0, 3])
    c1 = couverture_lignage(LIG, FLUX, ev1.controles, ev1.donnees)
    r1 = maj_registre(None, "C1", "2026-03-31", ev1.controles, ev1.donnees, c1)
    assert set(r1["type"]) == {"Qualité de donnée", "Contrôle non réalisé", "Couverture"}
    assert (r1["statut"] == "Ouverte").all()
    haute = r1[r1["objet"] == "K0|TOUS"].iloc[0]
    assert haute["gravite"] == "Haute" and haute["echeance"] == "2026-04-30"

    # Campagne 2 : K0 réalisé et vert -> clôturée ; K1 toujours en retard -> récurrente
    ev2 = _ev([0.999, 0.99], [0, 4])
    c2 = couverture_lignage(LIG, FLUX, ev2.controles, ev2.donnees)
    r2 = maj_registre(r1, "C2", "2026-06-30", ev2.controles, ev2.donnees, c2)
    s = r2.set_index("objet")["statut"]
    assert s["K0|TOUS"] == "Clôturée"
    assert s["K1|TOUS"] == "Récurrente"
    assert indicateurs_anomalies(r2, "2026-06-30")["nb_anomalies_en_retard"] >= 1


def test_pas_de_cloture_sans_realisation():
    """Une anomalie de qualité n'est pas clôturée si le contrôle n'a pas été refait, même s'il paraît vert."""
    ev1 = _ev([0.90], [0])
    c1 = couverture_lignage(LIG, FLUX, ev1.controles, ev1.donnees)
    r1 = maj_registre(None, "C1", "2026-03-31", ev1.controles, ev1.donnees, c1)
    ev2 = _ev([0.999], [1], sens={"d1": 0.10, "d2": 0.005})  # non réalisé, résultat ancien dégradé
    ev2.controles["statut"] = "vert"                          # même si le statut apparaît vert
    c2 = couverture_lignage(LIG, FLUX, ev2.controles, ev2.donnees)
    r2 = maj_registre(r1, "C2", "2026-06-30", ev2.controles, ev2.donnees, c2)
    q = r2[(r2["objet"] == "K0|TOUS") & (r2["type"] == "Qualité de donnée")].iloc[0]
    assert q["statut"] in ("Ouverte", "Récurrente")


def test_controle_restitution_exclu_de_la_note_mais_evalue():
    """Un contrôle QRT parfait ne doit pas améliorer la note d'une donnée dégradée (pas de dilution)."""
    seul = _ev([0.95], [0])
    avec = _ev([0.95, 1.0], [0, 0], fixe=[None, 0.999], inclus=[1, 0])
    assert avec.indicateurs["note"] == pytest.approx(seul.indicateurs["note"])
    c = avec.controles.set_index("controle_id")
    assert c.loc["K1|TOUS", "seuil"] == 0.999 and c.loc["K1|TOUS", "statut"] == "vert"
    ko = _ev([0.95, 0.997], [0, 0], fixe=[None, 0.999], inclus=[1, 0])
    assert ko.controles.set_index("controle_id").loc["K1|TOUS", "statut"] == "rouge"
    assert ko.indicateurs["taux_conformite_restitutions"] == 0.0


def test_journal_complet():
    from pathlib import Path
    from qdd_s2.gouvernance import entree_journal
    racine = Path(__file__).resolve().parents[1]
    j = entree_journal("N", "2026-09-30", Parametres(), racine, racine / "referentiels", {"t": 10}, 3, 5, {"note": 0.9})
    assert json.loads(j["parametres"])["delta_scr_max"] == 0.005
    assert "referentiel_controles.csv" in json.loads(j["empreinte_referentiels"])
    assert j["nb_controles_executes"] == 3


def test_modele_qlik_sans_cle_synthetique_ni_boucle(tmp_path):
    """Deux tables partagent au plus un champ, et le graphe des tables est un arbre (pas de boucle)."""
    import itertools
    from qdd_s2.campagne import Config, charger_lignage, lancer_campagnes
    from qdd_s2.export_qlik import exporter_qlik
    from scripts.generer_donnees_btp import generer
    base = tmp_path / "b.duckdb"
    generer(base)
    cfg = Config(base=base)
    camps, var = lancer_campagnes(cfg)
    ref = pd.read_csv(cfg.referentiels / "referentiel_controles.csv")
    _, flux = charger_lignage(cfg)
    fichiers = exporter_qlik(camps, var, ref, flux, tmp_path / "qlik")
    champs = {f.stem: set(pd.read_csv(f, sep=";", nrows=1).columns) for f in fichiers}
    # Clé synthétique : deux tables partagent plusieurs champs.
    for a, b in itertools.combinations(champs, 2):
        assert len(champs[a] & champs[b]) <= 1, (a, b, champs[a] & champs[b])
    # Référence circulaire : cycle dans le graphe biparti tables <-> champs partagés.
    partages = {c for c in set().union(*champs.values()) if sum(c in v for v in champs.values()) >= 2}
    aretes = [(t, c) for t, v in champs.items() for c in v & partages]
    noeuds = set(champs) | partages
    assert len(aretes) == len(noeuds) - 1          # arbre : n - 1 arêtes...
    vus, pile = set(), [next(iter(champs))]
    while pile:                                       # ... et connexe
        n = pile.pop()
        if n in vus:
            continue
        vus.add(n)
        pile += [c if t == n else t for t, c in aretes if n in (t, c)]
    assert vus == noeuds
