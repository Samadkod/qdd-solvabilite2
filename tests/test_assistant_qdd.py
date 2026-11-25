"""Assistant QDD : outils égaux au moteur, boucle de réponse testée avec un faux client (aucun appel à l'API)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from assistant_qdd import OUTILS, QUESTIONS, TOURS_OUTILS_MAX, executer_outil, repondre
from qdd_s2.campagne import Config, lancer_campagnes
from qdd_s2.niveau2 import niveau2_par_campagne

RACINE = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def contexte():
    """Même forme que les campagnes de l'application (streamlit_app.campagnes)."""
    cfg = Config()
    camps, var = lancer_campagnes(cfg)
    n2 = niveau2_par_campagne(camps, cfg.referentiels)
    out = []
    for r, niv2 in zip(camps, n2):
        ev = r.evaluation
        out.append({"campagne": r.campagne, "date": r.date_arrete, "ind": ev.indicateurs,
                    "donnees": ev.donnees.reset_index().rename(columns={"index": "donnee_id"}),
                    "controles": ev.controles, "gouv": r.gouvernance, "couverture": r.couverture,
                    "registre": r.registre, "niveau2": niv2})
    return {"camps": out, "var": var, "base": cfg.base}


def test_schemas_stricts_et_complets():
    noms = [o["name"] for o in OUTILS]
    assert len(noms) == len(set(noms)) == 9
    for o in OUTILS:
        s = o["input_schema"]
        assert o["strict"] is True and s["additionalProperties"] is False
        assert set(s["required"]) == set(s["properties"])  # mode strict : toutes les propriétés requises
    assert sum(len(v) for v in QUESTIONS.values()) == 15


def test_indicateurs_egaux_aux_valeurs_de_reference(contexte):
    r = executer_outil("indicateurs_campagne", {"campagne": "N"}, contexte)
    assert (r["note_qdd"], r["objectif_note_minimum"], r["ecart_objectif_points"]) == ("97,49 %", "97,10 %", 0.39)
    assert (r["donnees_critiques_hors_tolerance"], r["donnees_critiques"]) == (2, 8)
    assert (r["restitutions_qrt_conformes"], r["restitutions_qrt"]) == (10, 11)
    assert (r["zones_de_risque_critiques"], r["zones_de_risque_non_couvertes"]) == (33, 8)
    assert (r["anomalies_ouvertes"], r["anomalies_gravite_haute"], r["anomalies_cloturees"]) == (14, 4, 3)
    assert json.dumps(r, ensure_ascii=False)  # sérialisable tel quel pour l'API


def test_points_donnees_anomalies_concordent(contexte):
    retard = executer_outil("points_de_controle", {"campagne": "N", "controle": "", "statut": "en retard"}, contexte)
    assert retard["nombre"] == 6 and {p["point"].split("|")[0] for p in retard["points"]} == {"C07", "C08", "R04"}
    bloq = executer_outil("points_de_controle", {"campagne": "N", "controle": "", "statut": "Bloquant"}, contexte)
    assert bloq["nombre"] == 4
    don = executer_outil("donnees_critiques", {"campagne": "N"}, contexte)["donnees"]
    assert sum(d["critique"] for d in don) == 8
    assert sum(d["statut"] in ("À corriger", "Bloquant") for d in don) == 2
    ouv = executer_outil("anomalies", {"campagne": "N", "statut": "non clôturées"}, contexte)
    assert ouv["nombre"] == 14


def test_regle_lignes_variation_niveau2_lignage(contexte):
    r = executer_outil("regle_controle", {"controle": "c07"}, contexte)
    assert r["controle"] == "C07" and r["risque_couvert"] and "SELECT" in r["sql"]
    l = executer_outil("lignes_en_anomalie", {"campagne": "N", "controle": "C05"}, contexte)
    from lignes_anomalie import lignes
    attendu = lignes(str(contexte["base"]), "2026-09-30")
    assert l["nombre_lignes"] == int(attendu.loc[attendu["controle"] == "C05", "poids"].sum()) > 0
    assert "erreur" in executer_outil("lignes_en_anomalie", {"campagne": "N", "controle": "R04"}, contexte)
    v = executer_outil("variation_note", {}, contexte)
    assert v["etapes"][0]["note"] == "98,79 %" and v["etapes"][-1]["note"] == "97,49 %"
    n2 = executer_outil("controle_niveau2", {"campagne": "N"}, contexte)["constats"]
    assert [c["valeur"] for c in n2][:2] == ["20 sur 20", "17 sur 20"]
    nc = executer_outil("lignage", {"campagne": "N", "donnee": "", "seulement_non_couverts": True}, contexte)
    assert nc["nombre"] == 8


def test_erreurs_rendues_au_modele(contexte):
    assert "erreur" in executer_outil("inconnu", {}, contexte)
    assert "erreur" in executer_outil("indicateurs_campagne", {"campagne": "N-9"}, contexte)
    assert "erreur" in executer_outil("regle_controle", {"controle": "Z99"}, contexte)


class FauxClient:
    """Rejoue des réponses préparées et enregistre les requêtes envoyées."""

    def __init__(self, reponses):
        self.reponses, self.requetes = list(reponses), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.requetes.append(kw)
        return self.reponses.pop(0)


def _bloc(**kw):
    return SimpleNamespace(**kw)


def test_boucle_appelle_l_outil_puis_repond(contexte):
    outil = _bloc(type="tool_use", id="t1", name="indicateurs_campagne", input={"campagne": "N"})
    client = FauxClient([
        SimpleNamespace(stop_reason="tool_use", content=[outil]),
        SimpleNamespace(stop_reason="end_turn", content=[_bloc(type="text", text="La note est de 97,49 %.")]),
    ])
    messages = [{"role": "user", "content": "Quelle est la note ?"}]
    texte, appels, hist = repondre(client, messages, contexte)
    assert texte == "La note est de 97,49 %." and appels == ["indicateurs_campagne(campagne=N)"]
    resultat = hist[2]["content"][0]
    assert resultat["tool_use_id"] == "t1" and not resultat["is_error"]
    assert json.loads(resultat["content"])["note_qdd"] == "97,49 %"
    req = client.requetes[0]
    assert req["model"] == "claude-opus-5-5" and req["fallbacks"] == "default" and "temperature" not in req
    assert req["tools"] == OUTILS and req["cache_control"] == {"type": "ephemeral"}


def test_refus_et_boucle_bornee(contexte):
    refus = FauxClient([SimpleNamespace(stop_reason="refusal", content=[])])
    texte, _, _ = repondre(refus, [{"role": "user", "content": "x"}], contexte)
    assert texte.startswith("Je ne peux pas répondre")
    outil = _bloc(type="tool_use", id="t", name="variation_note", input={})
    sans_fin = FauxClient([SimpleNamespace(stop_reason="tool_use", content=[outil])] * (TOURS_OUTILS_MAX + 1))
    texte, appels, _ = repondre(sans_fin, [{"role": "user", "content": "x"}], contexte)
    assert texte.startswith("Trop d'étapes") and len(appels) == TOURS_OUTILS_MAX + 1


def test_page_sans_cle_annonce_l_assistant_non_configure(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(str(RACINE / "streamlit_app.py"), default_timeout=300)
    at.session_state["page"] = "assistant"
    at.run()
    assert not at.exception
    assert any("Assistant non configuré" in i.value for i in at.info)
    assert at.chat_input[0].disabled


# outils que chaque question proposée mobilise : ils doivent tous répondre sans erreur sur la campagne N
OUTILS_PAR_QUESTION = [
    [("indicateurs_campagne", {"campagne": "N"}), ("points_de_controle", {"campagne": "N", "controle": "", "statut": "Bloquant"})],
    [("variation_note", {})],
    [("donnees_critiques", {"campagne": "N"})],
    [("points_de_controle", {"campagne": "N", "controle": "Q02", "statut": "tous"})],
    [("points_de_controle", {"campagne": "N", "controle": "", "statut": "en retard"})],
    [("regle_controle", {"controle": "C07"}), ("points_de_controle", {"campagne": "N", "controle": "C07", "statut": "tous"})],
    [("anomalies", {"campagne": "N", "statut": "non clôturées"})],
    [("lignes_en_anomalie", {"campagne": "N", "controle": "C05"}), ("regle_controle", {"controle": "C05"})],
    [("anomalies", {"campagne": "N", "statut": "Récurrente"})],
    [("lignage", {"campagne": "N", "donnee": "", "seulement_non_couverts": True})],
    [("controle_niveau2", {"campagne": "N"})],
    [("controle_niveau2", {"campagne": "N"}), ("lignage", {"campagne": "N", "donnee": "placements_ACTIONS", "seulement_non_couverts": False})],
    [("indicateurs_campagne", {"campagne": "N"}), ("controle_niveau2", {"campagne": "N"}), ("variation_note", {})],
    [("donnees_critiques", {"campagne": "N"}), ("points_de_controle", {"campagne": "N", "controle": "", "statut": "tous"})],
    [("indicateurs_campagne", {"campagne": "N"}), ("controle_niveau2", {"campagne": "N"})],
]


def test_chaque_question_proposee_a_ses_outils(contexte):
    questions = [q for liste in QUESTIONS.values() for q in liste]
    assert len(questions) == len(OUTILS_PAR_QUESTION)
    for q, appels in zip(questions, OUTILS_PAR_QUESTION):
        for nom, entree in appels:
            r = executer_outil(nom, entree, contexte)
            assert "erreur" not in r, (q, nom, r)
    rec = executer_outil("anomalies", {"campagne": "N", "statut": "Récurrente"}, contexte)
    assert rec["nombre"] == 11  # = tuile « Anomalies récurrentes » de la Synthèse
    q02 = executer_outil("points_de_controle", {"campagne": "N", "controle": "Q02", "statut": "Bloquant"}, contexte)
    assert [p["point"] for p in q02["points"]] == ["Q02|DOMMAGES_OUVRAGE"]  # la restitution QRT non conforme
