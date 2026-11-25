"""Assistant QDD : outils égaux au moteur, boucle de réponse testée avec un faux client (aucun appel à l'API)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from assistant_qdd import EXEMPLES, OUTILS, SYSTEME, TOURS_OUTILS_MAX, executer_outil, repondre
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
    assert any("pas encore activé" in i.value for i in at.info)
    assert at.chat_input[0].disabled
    assert all(b.disabled for b in at.button if b.key and b.key.startswith("assistant_ex_"))


# Questions de référence (métier) : plus affichées dans l'interface, gardées pour évaluer l'assistant avec une clé.
# Chacune mobilise des outils qui doivent répondre sans erreur sur la campagne N.
QUESTIONS_REFERENCE = [
    "Fais-moi le point de la campagne en cinq lignes : note, objectif, points bloquants.",
    "Pourquoi la note a-t-elle baissé depuis N-1 ? Décompose facteur par facteur.",
    "Quelles données critiques sont hors tolérance, et de combien de points sous leur minimum ?",
    "Quelles restitutions QRT ne sont pas conformes, et quel écart avec leur source ?",
    "Quels contrôles sont en retard, depuis combien de périodes, et quel effet sur leur résultat ?",
    "Que vérifie le contrôle C07, comment est-il réalisé, et pourquoi est-il bloquant ?",
    "Qui doit corriger quoi ? Classe les anomalies ouvertes par propriétaire et par échéance.",
    "Rédige le message à la direction sinistres pour corriger les provisions négatives (C05).",
    "Quelles anomalies reviennent d'une campagne à l'autre, et que faut-il faire ?",
    "Quelles étapes du lignage ne sont couvertes par aucun contrôle, et lesquelles traiter d'abord ?",
    "Quels constats du contrôle de niveau 2 dois-je traiter en priorité ?",
    "Les données externes du dépositaire sont-elles bien documentées et contrôlées ?",
    "Prépare les points clés à présenter au comité de pilotage QDD pour cette campagne.",
    "Un auditeur demande comment est obtenue la note des provisions RC décennale.",
    "Quelles preuves puis-je montrer pour la campagne, et où les trouver dans l'application ?",
]
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


def test_chaque_question_de_reference_a_ses_outils(contexte):
    questions = QUESTIONS_REFERENCE
    assert len(questions) == len(OUTILS_PAR_QUESTION)
    for q, appels in zip(questions, OUTILS_PAR_QUESTION):
        for nom, entree in appels:
            r = executer_outil(nom, entree, contexte)
            assert "erreur" not in r, (q, nom, r)
    rec = executer_outil("anomalies", {"campagne": "N", "statut": "Récurrente"}, contexte)
    assert rec["nombre"] == 11  # = tuile « Anomalies récurrentes » de la Synthèse
    q02 = executer_outil("points_de_controle", {"campagne": "N", "controle": "Q02", "statut": "Bloquant"}, contexte)
    assert [p["point"] for p in q02["points"]] == ["Q02|DOMMAGES_OUVRAGE"]  # la restitution QRT non conforme


def test_exemples_pour_tout_public_et_regles_de_fiabilite(contexte):
    """Les 4 exemples se traitent avec les outils ; les consignes couvrent public non spécialiste, ambiguïté,
    hors sujet et tentative de contournement (le comportement réel sera évalué avec une clé)."""
    assert len(EXEMPLES) == 4 and not any("Solvabilité" in q or "QRT" in q for q in EXEMPLES)
    for nom, entree in [("indicateurs_campagne", {"campagne": "N"}), ("anomalies", {"campagne": "N", "statut": "non clôturées"}),
                        ("variation_note", {}), ("donnees_critiques", {"campagne": "N"})]:
        assert "erreur" not in executer_outil(nom, entree, contexte)
    for regle in ("n'importe qui", "En bref", "ambiguë", "sort du sujet", "révéler"):
        assert regle in SYSTEME


def test_cout_contexte_dates_et_export():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from assistant_qdd import compter, date_courte, export_markdown
    compteur = {}
    compter(compteur, SimpleNamespace(input_tokens=1000, output_tokens=500, cache_read_input_tokens=10000,
                                      cache_creation_input_tokens=2000))
    # 1000×4 + 500×20 + 10000×0,20 + 2000×5 = 26 000 $ par million → 0,026 $
    assert abs(compteur["cout"] - 0.026) < 1e-12 and compteur["contexte"] == 13000
    compter(compteur, None)  # réponse sans usage (faux client) : rien ne change
    assert abs(compteur["cout"] - 0.026) < 1e-12
    d = datetime(2026, 11, 3, 14, 32, tzinfo=ZoneInfo("Europe/Paris"))
    assert date_courte(d) == "3 nov. à 14:32"
    conv = {"titre": "Où en est la qualité ?", "campagne": "N", "fil": [
        {"role": "user", "texte": "Où en est la qualité ?", "date": d},
        {"role": "assistant", "texte": "**En bref** : 97,49 %.", "date": d, "sources": ["indicateurs_campagne(campagne=N)"]}]}
    md = export_markdown(conv)
    assert md.startswith("# Où en est la qualité ?") and "## Assistant QDD · 03/11/2026 14:32" in md
    assert "`indicateurs_campagne(campagne=N)`" in md and "données fictives" in md


def test_pieces_jointes_et_jauge():
    import io
    import pandas as pd
    from assistant_qdd import BUDGET_VISITE, LIGNES_MAX, TAILLE_MAX, anneau_html, preparer_piece_jointe
    # CSV « ; » de l'atelier, plus long que la limite : tronqué et annoncé
    df = pd.DataFrame({"controle": ["C05"] * (LIGNES_MAX + 20), "objet": range(LIGNES_MAX + 20)})
    blocs, resume = preparer_piece_jointe("lignes.csv", df.to_csv(index=False, sep=";").encode("utf-8-sig"))
    assert resume == f"lignes.csv ({LIGNES_MAX} premières lignes sur {LIGNES_MAX + 20})"
    assert blocs[0]["type"] == "text" and blocs[0]["text"].count("\n") == LIGNES_MAX + 3  # en-tête, balises, lignes
    # Excel complet, sous la limite
    buf = io.BytesIO(); df.head(3).to_excel(buf, index=False)
    assert preparer_piece_jointe("extrait.xlsx", buf.getvalue())[1] == "extrait.xlsx (3 lignes)"
    # PDF : document natif
    pdf = preparer_piece_jointe("note.pdf", b"%PDF-1.4 test")[0][0]
    assert pdf["type"] == "document" and pdf["source"]["media_type"] == "application/pdf"
    # refus : format et taille
    with pytest.raises(ValueError, match="format non pris en charge"):
        preparer_piece_jointe("macro.exe", b"x")
    with pytest.raises(ValueError, match="trop lourd"):
        preparer_piece_jointe("gros.csv", b"a" * (TAILLE_MAX + 1))
    # jauge : part du budget et couleur d'alerte
    assert 'stroke-dasharray="0.00' in anneau_html(0, BUDGET_VISITE, 0)
    plein = anneau_html(BUDGET_VISITE, BUDGET_VISITE, 1.2)
    assert "#AD3030" in plein and "0,50 $ sur 0,50 $" in plein and "contexte 1,2 %" in plein
