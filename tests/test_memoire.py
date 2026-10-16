"""Non-régression : le moteur reproduit les exemples chiffrés du mémoire.

Tolérance 0,05 point : le mémoire arrondit ses entrées à 2 décimales.
Les incohérences internes du mémoire sont documentées dans les docstrings.
"""
import pandas as pd
import pytest

from qdd_s2 import (Etat, Parametres, analyse_variation, anteriorite, degrader, evaluer,
                    mesure_rapprochement, mesure_rapprochement_maille, ratio_anomalie)

TOL = 5e-4
SENS = {"Primes acquises": 0.1423, "Provisions math.": 0.0574, "Sexe": 0.0267}


def _donnees(sens):
    return pd.DataFrame({"sensibilite": sens})


def _un_ctrl_par_donnee(notes):
    return pd.DataFrame({"controle_id": [f"C{i}" for i in range(len(notes))],
                         "donnee_id": list(notes), "resultat_brut": list(notes.values()),
                         "anteriorite": 0.0})


def test_tableau_3_sensibilites():
    scr_ref = 150.0
    apres = {"Primes acquises": 153.20, "Provisions math.": 151.03, "Sexe": 150.60, "Taux de cession": 150.12}
    s = {k: abs(v - scr_ref) / scr_ref / 0.15 for k, v in apres.items()}
    assert s["Primes acquises"] == pytest.approx(0.1423, abs=TOL)
    # NB : le tableau 3 donne 4,57 % pour les provisions math. ; les tableaux 5 à 9 utilisent 5,74 %
    assert s["Provisions math."] == pytest.approx(0.0457, abs=TOL)
    assert s["Sexe"] == pytest.approx(0.0267, abs=TOL)
    assert s["Taux de cession"] == pytest.approx(0.0052, abs=TOL)


def test_tableau_5_note_agregee_ponderee_par_sensibilite():
    ev = evaluer(_donnees(SENS), _un_ctrl_par_donnee(
        {"Primes acquises": 0.9990, "Provisions math.": 0.7471, "Sexe": 0.8172}))
    w = ev.donnees["poids_dans_note"]
    assert w["Primes acquises"] == pytest.approx(0.6287, abs=TOL)
    assert w["Provisions math."] == pytest.approx(0.2535, abs=TOL)
    assert ev.indicateurs["note"] == pytest.approx(0.9137, abs=TOL)


def test_tableaux_6_7_tolerance_par_donnee():
    ev = evaluer(_donnees(SENS), _un_ctrl_par_donnee({k: 1.0 for k in SENS}),
                 Parametres(delta_scr_max=0.005))
    nm = ev.donnees["note_min"]
    assert nm["Primes acquises"] == pytest.approx(0.9649, abs=TOL)
    assert nm["Provisions math."] == pytest.approx(0.9128, abs=TOL)
    assert nm["Sexe"] == pytest.approx(0.8124, abs=5e-4 * 1.5)
    assert ev.sensibilite_moyenne == pytest.approx(0.0754, abs=TOL)
    assert ev.indicateurs["note_min"] == pytest.approx(0.9337, abs=TOL)


def test_tableau_9_tolerance_globale():
    ev = evaluer(_donnees(SENS), _un_ctrl_par_donnee({k: 1.0 for k in SENS}),
                 Parametres(mode_tolerance="globale", tolerance_globale=0.05))
    nm = ev.donnees["note_min"]
    assert nm["Primes acquises"] == pytest.approx(0.9735, abs=TOL)
    assert nm["Provisions math."] == pytest.approx(0.9342, abs=TOL)
    assert nm["Sexe"] == pytest.approx(0.8585, abs=TOL)
    assert ev.indicateurs["note_min"] == pytest.approx(0.95, abs=1e-9)


def test_coherence_tolerance_criticite():
    # §2.2.4 : seuil 1 %, sensibilité moyenne 5 % -> tolérance globale < 20 %
    with pytest.raises(ValueError):
        Parametres(mode_tolerance="globale", tolerance_globale=0.25,
                   seuil_significativite=0.01).verifier_coherence(0.05)
    with pytest.raises(ValueError):
        Parametres(delta_scr_max=0.02, seuil_significativite=0.01).verifier_coherence(0.05)


def test_tableau_11_note_donnee():
    ctrl = pd.DataFrame({"controle_id": [f"Ctrl_{i}" for i in range(1, 7)], "donnee_id": "Sexe",
                         "poids": [1, .91, .37, .72, 1, 3],
                         "resultat_brut": [1, .9776, .8751, .9247, .9948, .9654], "anteriorite": 0.0})
    ev = evaluer(_donnees({"Sexe": 0.0267}), ctrl)
    assert ev.donnees.loc["Sexe", "note"] == pytest.approx(0.9672, abs=TOL)


def test_tableau_14_poids_controles():
    ctrl = pd.DataFrame({
        "controle_id": ["Ctrl_10", "Ctrl_21", "Ctrl_22", "Ctrl_23", "Ctrl_30", "Ctrl_40"],
        "donnee_id": ["Primes acquises"] * 4 + ["Provisions math."] * 2,
        "poids": [1, .91, .37, .72, 1, 3],
        "resultat_brut": [1, .9776, .8751, .9247, .9948, .9654], "anteriorite": 0.0})
    ev = evaluer(_donnees({"Primes acquises": 0.1423, "Provisions math.": 0.0457}), ctrl)
    c = ev.controles.set_index("controle_id")
    assert c.loc["Ctrl_10", "poids_dans_note"] == pytest.approx(0.2524, abs=TOL)
    assert c.loc["Ctrl_40", "poids_dans_note"] == pytest.approx(0.1822, abs=TOL)
    assert ev.donnees.loc["Primes acquises", "note"] == pytest.approx(0.9598, abs=TOL)
    assert ev.indicateurs["note"] == pytest.approx(0.9629, abs=TOL)


def test_tableaux_16_17_rapprochement():
    assert mesure_rapprochement([196.33, 191.53, 193.07]) == pytest.approx(0.0251, abs=TOL)
    t = [[89.68, 92.93, 92.93], [36.40, 24.03, 37.20], [70.25, 74.57, 62.94]]
    assert mesure_rapprochement_maille(t, 1) == pytest.approx(0.0251, abs=TOL)
    assert mesure_rapprochement_maille(t, 2) == pytest.approx(0.2564, abs=TOL)
    assert mesure_rapprochement_maille(t, 3) == pytest.approx(0.1834, abs=TOL)


def test_rapprochement_ecart_justifie_et_symetrique():
    assert mesure_rapprochement([100, 80, 100], justifies=[(0, 1), (1, 2)]) == 0.0
    # montants négatifs : la formule du mémoire explose, la symétrique reste bornée
    assert mesure_rapprochement([-10, 5]) > 1
    assert mesure_rapprochement([-10, 5], methode="symetrique") <= 1


def test_ratio_anomalie_compte_et_montant():
    assert ratio_anomalie([True, False, False, False]) == 0.25
    assert ratio_anomalie([True, False, False, False], [900, 50, 25, 25]) == 0.9


def test_figure_12_anteriorite():
    assert anteriorite("2022-06-30", "2022-09-30", "S") == 0
    assert anteriorite("2022-06-30", "2023-03-30", "S") == 1
    assert anteriorite("2022-06-30", "2023-03-30", "S", base="annuelle") == 0.5
    # figure 13 : deux ans après, base annuelle = 2 quelle que soit la fréquence
    for f in "AST":
        assert anteriorite("2022-12-31", "2024-12-31", f, base="annuelle") == 2


def test_figure_14_degradation():
    assert degrader(1.0, 3, 0.20, "simple") == pytest.approx(0.40)
    assert degrader(1.0, 6, 0.20, "simple") == 0.0
    assert degrader(1.0, 3, 0.20, "composee") == pytest.approx(0.512)


def _campagnes_tableau_21():
    sens_p = {"Primes acquises": .1423, "Provisions math.": .0457, "Sexe": .0267, "Taux de cession": .0052}
    sens_c = {"Primes acquises": .1989, "Provisions math.": .1109, "Sexe": .0161, "Taux de cession": .0220}
    don = ["Primes acquises"] * 4 + ["Provisions math.", "Sexe", "Taux de cession"]
    ids = [f"Ctrl_{i}" for i in range(1, 8)]
    poids = [1, 1, 2, 1, 1, 1, 2]
    prec = pd.DataFrame({"controle_id": ids, "donnee_id": don, "poids": poids,
                         "resultat_brut": [.9133, 1, .9998, .9998, .8770, .9869, .6806],
                         "anteriorite": [0, 0, 1, 1, 0, 0, 0]})
    cour = pd.DataFrame({"controle_id": ids, "donnee_id": don, "poids": poids,
                         "resultat_brut": [.9998, .9998, .9998, .9998, .8771, .9672, .6896],
                         "anteriorite": [0, 0, 2, 2, 0, 0, 0]})
    return (Etat(_donnees(sens_p), prec, Parametres(coef_degradation=.05)),
            Etat(_donnees(sens_c), cour, Parametres(coef_degradation=.04)))


def test_tableau_22_analyse_de_variation():
    prec, cour = _campagnes_tableau_21()
    av = analyse_variation(prec, cour).set_index("etape")
    attendu = {
        "Note QDD agrégée N-1": .9408,
        "QDD mesurée par les contrôles (antériorité intacte)": .9498,
        "Antériorité des contrôles": .9299,
        "Coefficient de dégradation": .9378,
        "Sensibilités des données critiques": .9272,
        "Entrée de données critiques": .9121,
        "Note QDD agrégée N": .9121,
    }
    for etape, note in attendu.items():
        assert av.loc[etape, "note"] == pytest.approx(note, abs=TOL), etape
    # la somme des impacts explique exactement la variation
    assert av["impact"].sum() == pytest.approx(av["note"].iloc[-1] - av["note"].iloc[0])


def test_tableau_24_axe_entite():
    sens = {"Primes acquises": .1423, "Provisions math.": .0457, "Sexe": .0267}
    ctrl = pd.DataFrame({
        "controle_id": [f"Ctrl_{i}" for i in range(1, 6)],
        "donnee_id": ["Primes acquises", "Primes acquises", "Provisions math.", "Provisions math.", "Sexe"],
        "entite": ["1", "2", "1", "2", "1"],
        "resultat_brut": [.9998, .9620, .9847, .9414, .9716], "anteriorite": 0.0})
    ev = evaluer(_donnees(sens), ctrl, Parametres(delta_scr_max=.005))
    ax = ev.par_axe("entite")
    assert ax.loc["1", "note"] == pytest.approx(.9931, abs=TOL)
    assert ax.loc["2", "note"] == pytest.approx(.9570, abs=TOL)
    assert ax.loc["1", "note_min"] == pytest.approx(.9301, abs=TOL)
    assert ax.loc["2", "note_min"] == pytest.approx(.9468, abs=TOL)
    assert ev.indicateurs["note"] == pytest.approx(.9760, abs=TOL)
    assert ev.indicateurs["note_min"] == pytest.approx(.9301, abs=TOL)
