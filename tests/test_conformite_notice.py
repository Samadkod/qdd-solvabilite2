"""Écarts avec la notice ACPR QDD traités dans le dispositif (référentiel des contrôles, niveau 2, données en
défaut conservées, fiche d'ajustement, données externes, document cadre). Valeurs vérifiées sur la campagne N."""
from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from archives_defaut import DOSSIER, archiver, contenu, lire_manifeste, sha256, verifier
from operations_qdd.correction import COLONNES_FICHE, fiche_ajustement
from qdd_s2.campagne import Config, lancer_campagnes
from qdd_s2.document_cadre import _pct, markdown, valeurs
from qdd_s2.niveau2 import CHAMPS_REFERENTIEL, charger_referentiels, niveau2_par_campagne, referentiel_complet

RACINE = Path(__file__).resolve().parents[1]
REFS = RACINE / "referentiels"


@pytest.fixture(scope="module")
def campagnes():
    cfg = Config()
    camps, _ = lancer_campagnes(cfg)
    return cfg, camps


@pytest.fixture(scope="module")
def n2(campagnes):
    cfg, camps = campagnes
    return niveau2_par_campagne(camps, cfg.referentiels)[-1].set_index("id")


# --------------------------------------------------------------- référentiel des contrôles (points 67-70)
def test_referentiel_des_controles_complet_et_propre_a_chaque_controle():
    ref = pd.read_csv(REFS / "referentiel_controles.csv", dtype=str, keep_default_na=False)
    for col in CHAMPS_REFERENTIEL:
        vides = ref.loc[ref[col].str.strip() == "", "controle_id"].tolist()
        assert not vides, f"colonne {col} vide pour {vides}"
    assert set(ref["mode_realisation"]) <= {"Manuel", "Automatique"}
    # rédigés contrôle par contrôle : aucun texte copié-collé d'un contrôle à l'autre
    assert ref["risque_couvert"].is_unique and ref["mode_operatoire"].is_unique
    # la copie lue par SAS a le même contenu (colonnes ajoutées en fin : l'import SAS les ignore)
    sas = pd.read_csv(RACINE / "sas" / "donnees_demo" / "referentiel_controles.csv", sep=";", dtype=str,
                      keep_default_na=False)
    pd.testing.assert_frame_equal(ref, sas)


def test_niveau2_signale_un_champ_obligatoire_vide():
    ref, _, _ = charger_referentiels(REFS)
    ref.loc[ref["controle_id"] == "C05", "mode_operatoire"] = ""
    r = referentiel_complet(ref)
    assert (r["valeur"], r["statut"], r["detail"]) == ("19 sur 20", "orange", "C05 : mode opératoire")


# --------------------------------------------------------------- contrôle de niveau 2
def test_niveau2_valeurs_campagne_n(n2):
    attendu = {
        "N2-01": ("20 sur 20", "vert"), "N2-02": ("17 sur 20", "orange"), "N2-03": ("7 sur 19", "À revoir"),
        "N2-04": ("8 sur 8", "vert"), "N2-05": ("22 sur 24", "orange"), "N2-06": ("25 sur 33", "orange"),
        "N2-07": ("0 sur 2", "orange"),
    }
    assert {i: (r.valeur, r.statut) for i, r in n2.iterrows()} == attendu
    assert n2.loc["N2-02", "detail"] == "C07 (1 période de retard) ; C08 (2 périodes de retard) ; R04 (1 période de retard)"
    assert n2.loc["N2-05", "detail"] == "date_survenance : exhaustivité ; taux_cession : exhaustivité"
    assert n2.loc["N2-07", "detail"] == ("placements_ACTIONS : flux externe F13 sans contrôle ; "
                                         "placements_OBLIGATIONS : flux externe F13 sans contrôle")
    assert "rouge" not in set(n2["statut"])  # aucun seuil de gravité inventé pour le niveau 2


def test_niveau2_concorde_avec_le_moteur(campagnes, n2):
    _, camps = campagnes
    n = camps[-1]
    g, ind, ctrl = n.gouvernance, n.evaluation.indicateurs, n.evaluation.controles
    assert n2.loc["N2-06", "nb_ecarts"] == g["nb_zones_non_couvertes"]
    assert n2.loc["N2-06", "valeur"] == f"{g['nb_zones_risque_critiques'] - g['nb_zones_non_couvertes']} sur {g['nb_zones_risque_critiques']}"
    assert n2.loc["N2-04", "nb_ecarts"] == len(ind["donnees_critiques_non_controlees"])
    assert n2.loc["N2-02", "nb_ecarts"] == ctrl.loc[ctrl["anteriorite"] > 0, "controle"].nunique()
    # « jamais en anomalie » : vrai sur chacune des trois campagnes, pour chaque contrôle cité
    for code in [d.split(" ")[0] for d in n2.loc["N2-03", "detail"].split(" ; ")]:
        for c in camps:
            st = c.evaluation.controles.loc[c.evaluation.controles["controle"] == code, "statut"]
            assert not st.isin(["orange", "rouge"]).any()


# --------------------------------------------------------------- données externes
def test_donnees_externes_identifiees_sans_en_creer():
    _, dic, flux = charger_referentiels(REFS)
    assert set(dic["origine"]) == {"Interne", "Externe"} and set(flux["origine"]) == {"Interne", "Externe"}
    ext = dic[dic["origine"] == "Externe"]
    assert list(ext.index) == ["placements_ACTIONS", "placements_OBLIGATIONS"]  # source : relevé dépositaire
    assert (ext["source"] == "Relevé dépositaire").all()
    assert (ext["fournisseur"].str.strip() != "").all() and (ext["traitement_externe"].str.strip() != "").all()
    assert sorted(flux.loc[flux["origine"] == "Externe", "flux_id"]) == ["F11", "F13"]
    assert (flux.loc[flux["origine"] == "Externe", "systeme_source"] == "Relevé dépositaire").all()


# --------------------------------------------------------------- données en défaut conservées (point 37)
def test_archives_intactes_et_egales_aux_donnees_avant_ajustement(tmp_path):
    from scripts.generer_donnees_btp import generer

    base = tmp_path / "fictif.duckdb"
    generer(base)  # base régénérée de zéro : l'archive doit être exactement la donnée en défaut d'origine
    man = lire_manifeste()["archives"]
    plan = pd.read_csv(REFS / "plan_campagnes.csv")
    assert [(a["campagne"], a["arrete"]) for a in man] == list(zip(plan["campagne"], plan["date_arrete"]))
    assert verifier()["intacte"].all()
    for a in man:
        data = contenu(base, a["arrete"])
        assert sha256(data) == a["sha256"] and data.count(b"\n") - 1 == a["nb_lignes"]


def test_archive_jamais_ecrasee(tmp_path):
    dossier = tmp_path / "archives"
    shutil.copytree(DOSSIER, dossier)
    plan = pd.read_csv(REFS / "plan_campagnes.csv")
    base = RACINE / "data" / "btp_fictif.duckdb"
    assert archiver(base, plan, dossier) == []  # déjà archivé : rien n'est réécrit
    cible = dossier / lire_manifeste(dossier)["archives"][-1]["fichier"]
    cible.write_bytes(cible.read_bytes() + b"ligne ajoutee\n")
    with pytest.raises(RuntimeError, match="rien n'est écrasé"):
        archiver(base, plan, dossier)
    assert not verifier(dossier)["intacte"].iloc[-1]


# --------------------------------------------------------------- fiche d'ajustement (points 36-37)
def test_fiche_ajustement_reprend_le_scenario_et_l_archive():
    dossier = {
        "campagne": "N", "date": "2026-09-30", "code": "C05", "maille": "AUTO_FLOTTE",
        "edits": [{"objet": "SAU0001", "ancienne": -120.5, "nouvelle": 0.0}],
        "auteur": "Alice", "justification": "Pièce fictive", "statut": "Validée dans le bac à sable",
        "configuration": {"role_correction": "Propriétaire", "role_validation": "QDD", "separation": True},
        "preuve": {"blocages": []},
        "evenements": [{"date": "2026-11-11T10:00:00Z", "action": "Déclaration", "acteur": "Alice"},
                       {"date": "2026-11-11T11:00:00Z", "action": "Validation déclarative", "acteur": "Bob",
                        "role": "QDD", "commentaire": "ok"}],
    }
    f = fiche_ajustement(dossier)
    assert list(f) == COLONNES_FICHE
    arch = next(a for a in lire_manifeste()["archives"] if a["campagne"] == "N")
    assert f["Donnée"] == "provisions_sinistres_AUTO_FLOTTE"
    assert f["Empreinte SHA-256 de l’archive"] == arch["sha256"]
    assert f["Valeurs ajustées"] == "SAU0001 : -120.50 → 0.00"
    assert f["Responsable de la correction"] == "Alice (Propriétaire)"
    assert f["Responsable de la validation"] == "Bob (QDD)" and f["Validé le (UTC)"] == "2026-11-11T11:00:00Z"
    assert f["Risque couvert"].startswith("Provision dossier négative")
    non_valide = dict(dossier, statut="Recontrôle bloquant", evenements=dossier["evenements"][:1])
    assert fiche_ajustement(non_valide)["Responsable de la validation"] == "Non validé"


# --------------------------------------------------------------- document cadre (points 16-17)
def test_document_cadre_chiffres_egaux_au_moteur(campagnes):
    cfg, camps = campagnes
    n = camps[-1]
    ev = n.evaluation
    ref, dic, flux = charger_referentiels(cfg.referentiels)
    v = valeurs(n, ref, dic, flux, cfg.choc_sensibilite)
    md = markdown(v)
    crit = ev.donnees[ev.donnees["critique"]]
    assert v["nb_critiques"] == ev.indicateurs["nb_donnees_critiques"] == 8
    assert v["note_min_globale"] == ev.indicateurs["note_min"]
    assert v["seuil_significativite"] == ev.params.seuil_significativite
    assert v["delta_scr_max"] == ev.params.delta_scr_max
    assert v["nb_zones_non_couvertes"] == n.gouvernance["nb_zones_non_couvertes"]
    assert v["nb_controles_note"] == int(ev.controles.groupby("controle")["inclus_note"].first().sum())
    for d, s in crit["sensibilite"].items():
        assert f"| {d} | {_pct(s)}" in md and _pct(crit.loc[d, "note_min"]) in md
    for texte in (_pct(ev.indicateurs["note_min"]), _pct(ev.indicateurs["tolerance_globale_effective"]),
                  _pct(ev.params.delta_scr_max), f"{v['nb_donnees']} données", f"{v['nb_controles']} contrôles"):
        assert texte in md
    assert md.count("À compléter par l'organisme") >= 5  # validation, revue, rôles, comitologie, seuil
    assert "conforme ACPR" not in md and "fictives" in md
