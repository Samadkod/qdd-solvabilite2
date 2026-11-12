"""Langue de l'interface : français par défaut, anglais pour la navigation, les en-têtes, la Synthèse et les statuts.

Le contenu détaillé (guide, explications pas à pas, exercices SAS, documentation) reste en français ; une ligne
le signale sur chaque page en mode anglais. t(texte) renvoie la traduction anglaise si elle existe, sinon le
texte français : un oubli de traduction affiche du français, jamais une erreur.
"""
from __future__ import annotations

import re

LANGUES = {"fr": "Français", "en": "English"}

EN = {
    # rubriques et menu
    "Pilotage QDD": "Data quality steering", "Exploitation": "Operations", "Évolutions": "Roadmap",
    "Comprendre": "Understand", "Se former": "Learn", "Technique": "Technical",
    "Campagne affichée": "Campaign shown", "Documentation": "Documentation",
    "Retour à l'atelier QDD": "Back to the DQ workshop", "Paramètres de la méthode": "Method parameters",
    "Langue": "Language", "Campagne": "Campaign",
    # pages : titres
    "Synthèse": "Overview", "Note & données": "Score & data", "Contrôles": "Controls", "Anomalies": "Issues",
    "Lignes en anomalie": "Failing rows", "Règles de contrôle": "Control rules",
    "Lignage & dictionnaire": "Lineage & data dictionary", "Chargement & exécution": "Loading & execution",
    "Atelier de résolution": "Resolution workshop", "Dossier de campagne": "Campaign evidence file",
    "Vérification SAS": "SAS verification", "Feuille de route": "Roadmap",
    "D'où sortent les chiffres": "Where the figures come from", "Guide terre à terre": "Plain-language guide",
    "Visite de l'application": "App tour", "SAS pratique": "SAS practice", "Atelier QDD": "DQ workshop",
    "Mise en place en entreprise": "Rolling out in a company", "Code SAS / SQL": "SAS / SQL code",
    # pages : descriptions
    "Tout l'état de la campagne en un écran. Cliquez sur ↗ pour le détail.":
        "The whole campaign on one screen. Click ↗ for details.",
    "La note de chaque donnée, pourquoi elle a bougé et où sont les écarts.":
        "Each data item's score, why it moved and where the gaps are.",
    "Liste de suivi : exécution, résultat, échéance et durée de chaque point de contrôle.":
        "Tracking list: run status, result, due date and duration of each control point.",
    "Le registre : qui doit corriger quoi, pour quand.": "The issue log: who must fix what, by when.",
    "Chaque ligne en erreur, contrôle par contrôle : quoi corriger, exactement.":
        "Every failing row, control by control: exactly what to fix.",
    "Le catalogue des 20 contrôles : famille, message, responsable, état dans la campagne.":
        "The catalogue of the 20 controls: family, message, owner, status in the campaign.",
    "Le trajet des données, les étapes sans contrôle, la carte d'identité de chaque donnée.":
        "How data flows, the steps without controls, and each data item's ID card.",
    "Les données sont-elles bien arrivées, et chaque contrôle a-t-il pu tourner ?":
        "Did the data arrive in full, and could every control run?",
    "Correction sur copie, recontrôle réel et validation déclarative sur données fictives.":
        "Fix on a copy, real re-run of the controls and declared sign-off, on fictitious data.",
    "Preuves, résultats, règles et pièces manquantes de la campagne.":
        "Evidence, results, rules and missing items for the campaign.",
    "La même campagne calculée par la chaîne SAS, comparée valeur par valeur au moteur Python.":
        "The same campaign computed by the SAS chain, compared value by value with the Python engine.",
    "Ce qui reste à faire, ce qui attend une décision, et ce qui a été fait.":
        "What is left to do, what awaits a decision, and what has been done.",
    "Le calcul pas à pas, sur les vrais chiffres.": "The calculation step by step, on the actual figures.",
    "Le métier, les chiffres et le poste, sans jargon.": "The job, the figures and the role, without jargon.",
    "Chaque page en une ligne : à quoi elle sert, quand l'ouvrir.": "Each page in one line: what it is for, when to use it.",
    "13 exercices progressifs, corrigés, avec le résultat attendu.": "13 progressive exercises with solutions and expected results.",
    "Résolution fictive et atelier de révision conservé.": "Fictitious resolution and the revision workshop.",
    "Ce qu'il faut changer une fois, puis faire chaque trimestre, pour faire tourner la chaîne SAS sur les vraies données.":
        "What to change once, then do each quarter, to run the SAS chain on real data.",
    "La version production en SAS / PROC SQL et les 20 contrôles SQL.": "The production version in SAS / PROC SQL and the 20 SQL controls.",
    # bandeau et Synthèse
    "SOLVABILITÉ II / PILOTAGE DE LA QUALITÉ DES DONNÉES": "SOLVENCY II / DATA QUALITY STEERING",
    "Pilotage de la qualité des données": "Data quality steering",
    "Arrêté du": "Reporting date",
    "Identifier les écarts. Prioriser la revue. Documenter les contrôles.":
        "Spot the gaps. Prioritise the review. Document the controls.",
    "Environnement de démonstration · données fictives": "Demo environment · fictitious data",
    "Assurance dommages · BTP": "Non-life insurance · construction",
    "Vue d’ensemble": "At a glance", "Les indicateurs clés de la campagne": "The campaign's key indicators",
    "Conforme": "Compliant", "Vigilance prioritaire": "Priority attention", "À suivre": "To monitor",
    "Repère": "Reference", "Périmètre": "Scope", "Voir le détail ↗": "See details ↗",
    "Objectif global atteint": "Overall target met", "Objectif global non atteint": "Overall target not met",
    "des points de vigilance restent à traiter.": "some attention points remain.",
    "donnée(s) critique(s) hors tolérance": "critical data item(s) out of tolerance",
    "restitution(s) QRT non conforme(s)": "non-compliant QRT report(s)",
    "anomalie(s) grave(s)": "severe issue(s)", "échéance(s) dépassée(s)": "overdue item(s)",
    "La note agrégée ne remplace pas la revue des risques individuels.":
        "The overall score does not replace the review of individual risks.",
    "Aucun point de vigilance dans ces quatre catégories.": "No attention point in these four categories.",
    "Agir sur les points de vigilance": "Act on attention points",
    "Voir les données hors tolérance": "See out-of-tolerance data", "Voir les contrôles bloquants": "See blocking controls",
    "Voir les anomalies ouvertes": "See open issues",
    "Indicateurs détaillés · note, contrôles, anomalies et exploitation":
        "Detailed indicators · score, controls, issues and operations",
    "Performance de la qualité": "Quality performance", "Objectif et évolution de la note": "Target and score trend",
    "Contrôles & restitutions réglementaires": "Controls & regulatory reports",
    "Résultats, retards et couverture des risques": "Results, delays and risk coverage",
    "Suivi des anomalies": "Issue tracking", "Gravité, échéances et cycle de vie": "Severity, due dates and lifecycle",
    "Fiabilité de l’exploitation": "Operational reliability",
    "Chargement des sources et exécution technique": "Source loading and technical execution",
    "Où concentrer les corrections ?": "Where to focus fixes?", "Les 5 messages les plus fréquents": "The 5 most frequent messages",
    "Autres actions & accès rapides": "Other actions & shortcuts",
    "Exports de la campagne": "Campaign exports",
    "Des livrables pour documenter et partager la revue": "Deliverables to document and share the review",
    "Registre des anomalies · CSV": "Issue log · CSV", "Contrôles en anomalie · CSV": "Failing controls · CSV",
    "Rapport complet · Excel": "Full report · Excel",
    # titres des tuiles
    "Note QDD agrégée": "Overall DQ score", "Objectif (note minimum)": "Target (minimum score)",
    "Écart à l'objectif": "Gap to target", "Données critiques hors tolérance": "Critical data out of tolerance",
    "Contrôles qui comptent dans la note": "Controls counted in the score", "Contrôles en retard": "Overdue controls",
    "Contrôles bloquants": "Blocking controls", "Contrôles à corriger": "Controls to fix",
    "États QRT non conformes": "Non-compliant QRT reports", "Étapes à risque sans contrôle": "Risk steps without controls",
    "Anomalies ouvertes": "Open issues", "Anomalies graves": "Severe issues", "Échéance dépassée": "Overdue",
    "Anomalies récurrentes": "Recurring issues", "Anomalies clôturées": "Closed issues",
    "Tables sources en alerte de volume": "Source tables with volume alert",
    "Contrôles en échec technique": "Controls with technical failure",
    "Contrôles non exécutés ce trimestre": "Controls not run this quarter",
    "Lignes lues dans les sources": "Rows read from sources", "Lignes en anomalie (cohérence)": "Failing rows (consistency)",
    # statuts (pastilles)
    "À corriger": "To fix", "Bloquant": "Blocking", "Non noté": "Not rated",
    "Exécuté": "Run", "Saisi hors outil": "Entered manually", "Non réalisé": "Not run", "Échec technique": "Technical failure",
    "Ouverte": "Open", "Récurrente": "Recurring", "Clôturée": "Closed", "Haute": "High", "Moyenne": "Medium",
    "Normal": "Normal", "À expliquer": "To explain", "Sans référence": "No baseline", "En retard": "Overdue",
    "Disponible": "Available", "Manquant": "Missing", "Incomplet": "Incomplete", "Non produit": "Not produced",
    "Non acquise": "Not obtained", "À revoir": "To review", "Contrôle de niveau 2": "Second-level control",
    "Filtres": "Filters", "Réalisé": "Done", "Exécution": "Execution", "Résultat": "Result",
    "Points de contrôle": "Control points", "Diagnostic explicable de la campagne": "Explainable campaign diagnosis",
    "Solvabilité 2 · données fictives": "Solvency II · fictitious data",
    # divers
    "Contenu détaillé de cette page en français ; l'anglais couvre le menu, les en-têtes, la Synthèse et les statuts.":
        "Detailed content of this page is in French; English covers the menu, headings, the Overview and statuses.",
}
_MOTIFS = [  # libellés construits (évolutions, titres variables)
    (re.compile(r"^Variation depuis (.+)$"), r"Change since \1"),
    (re.compile(r"^= stable depuis (.+)$"), r"= stable since \1"),
    (re.compile(r"^(.+) depuis (.+)$"), r"\1 since \2"),
    (re.compile(r"^(\d+) sur (\d+)$"), r"\1 of \2"),
    (re.compile(r"^Dernière exécution \(à (.+)\)$"), r"Last run (at \1)"),
]


def langue() -> str:
    try:
        import streamlit as st
        return st.session_state.get("langue") or "fr"
    except Exception:  # noqa: BLE001 — hors application (tests, scripts) : français
        return "fr"


def t(texte: str) -> str:
    """Traduit si l'interface est en anglais et qu'une traduction existe ; sinon renvoie le texte tel quel."""
    if langue() != "en" or not isinstance(texte, str):
        return texte
    if texte in EN:
        return EN[texte]
    for motif, rempl in _MOTIFS:
        if motif.match(texte):
            return motif.sub(rempl, texte)
    return texte
