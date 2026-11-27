"""Fiche de l'Atelier de résolution : l'exemple pas à pas va bien jusqu'à la validation sur la campagne N, et la
fiche décrit les mêmes étapes et motifs de blocage que le code."""
from __future__ import annotations

import inspect

from fiche_atelier import BLOCAGES, ETAPES
from operations_qdd import correction as co
from qdd_s2.campagne import Config, lancer_campagnes


def test_exemple_de_la_fiche_valide_de_bout_en_bout():
    cfg = Config()
    camps, _ = lancer_campagnes(cfg)
    r = camps[-1]
    ev = r.evaluation
    c = {"campagne": r.campagne, "date": r.date_arrete, "controles": ev.controles, "params": ev.params,
         "donnees": ev.donnees.reset_index().rename(columns={"index": "donnee_id"})}
    df = co.candidats(cfg.base, c["date"], "C05", "AUTO_FLOTTE")
    assert len(df) == 2 and df["modifiable"].all() and (df["ancienne"] < 0).all()
    rec = co.declarer(c, cfg.base, "C05", "AUTO_FLOTTE", [{"objet": o, "nouvelle": 0.0} for o in df["objet"]],
                      "Alice", "Pièce fictive", {"role_correction": "Propriétaire", "role_validation": "QDD",
                                                 "separation": True},
                      {"methode_ecart": cfg.methode_ecart, "ponderation_montant": cfg.ponderation_montant})
    co.rejouer(rec, cfg.base, c["params"])
    assert rec["statut"] == "Recontrôle réussi · à valider" and not rec["preuve"]["blocages"]
    comp = {x["Point"]: x for x in rec["preuve"]["comparaison"]}
    assert comp["C05|AUTO_FLOTTE"]["Après"] == 1.0
    try:
        co.valider(rec, "Alice", "QDD", "x")
        raise AssertionError("le même nom aurait dû être refusé")
    except ValueError:
        pass
    co.valider(rec, "Bob", "QDD", "ok")
    assert rec["statut"] == "Validée dans le bac à sable"
    assert ("C05", "AUTO_FLOTTE") in co.ESSAIS_VALIDABLES["N"]


def test_fiche_alignee_sur_le_code():
    assert [t for t, _ in ETAPES] == ["Proposer", "Recontrôler", "Valider", "Exporter"]
    code = inspect.getsource(co.rejouer)
    for motif in ("seuil QDD non calculé", "encore en anomalie sur la cible", "nouvelle non-conformité",
                  "encore dégradé"):
        assert motif in code  # les 4 motifs expliqués par la fiche existent bien dans le recontrôle
    assert len(BLOCAGES) == 4 and set(co.REGLES) == {"C02", "C05"}



def test_une_valeur_par_ligne_dans_une_meme_declaration_se_valide():
    """Demande du propriétaire : 500 € pour un sinistre, 0 € pour l'autre, dans une seule déclaration."""
    cfg = Config()
    camps, _ = lancer_campagnes(cfg)
    r = camps[-1]
    ev = r.evaluation
    c = {"campagne": r.campagne, "date": r.date_arrete, "controles": ev.controles, "params": ev.params,
         "donnees": ev.donnees.reset_index().rename(columns={"index": "donnee_id"})}
    objets = list(co.candidats(cfg.base, c["date"], "C05", "AUTO_FLOTTE")["objet"])
    edits = [{"objet": objets[0], "nouvelle": 500.0}, {"objet": objets[1], "nouvelle": 0.0}]
    meth = {"methode_ecart": cfg.methode_ecart, "ponderation_montant": cfg.ponderation_montant}
    cfgr = {"role_correction": "Propriétaire", "role_validation": "QDD", "separation": True}
    rec = co.declarer(c, cfg.base, "C05", "AUTO_FLOTTE", edits, "Alice", "Pièces fictives", cfgr, meth)
    assert [e["nouvelle"] for e in rec["edits"]] == [500.0, 0.0]
    co.rejouer(rec, cfg.base, c["params"])
    assert rec["statut"] == "Recontrôle réussi · à valider"
    co.valider(rec, "Bob", "QDD", "ok")
    assert rec["statut"] == "Validée dans le bac à sable"
    # une seule ligne corrigée : l'autre reste fautive, la validation est bloquée (d'où la saisie ligne par ligne)
    seul = co.declarer(c, cfg.base, "C05", "AUTO_FLOTTE", edits[:1], "Alice", "Pièce fictive", cfgr, meth)
    co.rejouer(seul, cfg.base, c["params"])
    assert seul["statut"] == "Recontrôle bloquant"
    assert any("encore en anomalie sur la cible" in b for b in seul["preuve"]["blocages"])
