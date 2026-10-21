"""Feuille de route de l'atelier : ce qui attend une décision, ce qui est prévu, ce qui reste à vérifier, ce qui est fait.

Point unique de suivi des évolutions (à tenir à jour à chaque livraison).
"""
from __future__ import annotations

import pandas as pd

ELEMENTS = [
    # ---------------------------------------------------------------- décisions
    dict(id="D1", statut="En attente de décision", titre="Corriger la date de survenance dans les données fictives (C07)",
         pourquoi="Le générateur tire la survenance sans tenir compte de la date d'effet du contrat : 2 282 sinistres "
                  "(46 %) sont signalés par C07 au lieu d'environ 1 % visé.",
         prerequis="Accord du propriétaire : la correction modifie les sinistres (triangles S.19.01, C06…) et peut "
                   "changer des valeurs de référence. Chaque chiffre qui change sera montré avant de pousser.",
         effort="Faible"),
    # ---------------------------------------------------------------- prévu plus tard
    dict(id="E4", statut="Plus tard", titre="Suivi de campagne étape par étape",
         pourquoi="Piloter une clôture : extraction, contrôles, calcul, validation, publication, avec pour chaque étape "
                  "son état (à venir, en cours, fait, en retard) et depuis quand.",
         prerequis="Définir les étapes et leurs échéances dans referentiels/plan_campagnes.csv (aujourd'hui : dates "
                   "d'arrêté et contrôles non réalisés seulement).",
         effort="Moyen"),
    dict(id="E5", statut="Plus tard", titre="Historique et tendances sur plusieurs trimestres",
         pourquoi="Montrer en comité l'évolution de la note, des contrôles conformes, des anomalies ouvertes et "
                  "clôturées, avec un tableau « détail par campagne » et la variation d'une campagne à l'autre.",
         prerequis="Au moins 6 à 8 campagnes : générer des trimestres fictifs supplémentaires (modifie les données, "
                   "décision du propriétaire) ; en entreprise, historiser les résultats à chaque campagne.",
         effort="Moyen"),
    dict(id="E6", statut="Plus tard", titre="Durées d'exécution des contrôles",
         pourquoi="Mission optimisation : repérer les traitements les plus longs, suivre leur durée dans le temps, "
                  "alerter si une durée double.",
         prerequis="Les durées sont déjà mesurées (page « Chargement & exécution ») ; reste à les historiser et à "
                   "afficher les contrôles les plus longs. Sur les données fictives, les durées sont de quelques "
                   "millisecondes : l'intérêt est la méthode.",
         effort="Faible"),
    # ---------------------------------------------------------------- à vérifier
    dict(id="V1", statut="À vérifier", titre="Exécuter la chaîne SAS complète",
         pourquoi="Le SAS est écrit et vérifié statiquement, jamais exécuté.",
         prerequis="SAS OnDemand for Academics : lancer sas/99_executer.sas, lire le journal et WORK.VERIFICATION "
                   "(43 valeurs comparées à la référence Python).",
         effort="Moyen"),
    dict(id="V2", statut="À vérifier", titre="Exécuter les corrigés des exercices SAS",
         pourquoi="Les 13 corrigés passent le contrôle statique mais n'ont jamais tourné.",
         prerequis="Après V1 ; comparer chaque sortie au résultat attendu affiché dans « SAS pratique ».",
         effort="Faible"),
    dict(id="V3", statut="À vérifier", titre="Charger le modèle dans Qlik Sense",
         pourquoi="Le script app/chargement_qdd.qvs et le gabarit ODBC n'ont jamais été exécutés.",
         prerequis="Accès à Qlik Sense ; vérifier l'absence de clé synthétique et de boucle dans le modèle.",
         effort="Moyen"),
    # ---------------------------------------------------------------- fait
    dict(id="F1", statut="Fait", titre="Contrôles de chargement (niveau 0) et échecs techniques",
         pourquoi="Séparer « la donnée n'est pas arrivée / le contrôle n'a pas tourné » de « la donnée est fausse ».",
         prerequis="Seuil de volumétrie de 10 % retenu par le propriétaire (justification dans la page « Chargement & "
                   "exécution ») ; règle en Python et en SAS (sas/08_chargement.sas).", effort="—"),
    dict(id="F2", statut="Fait", titre="Évolution depuis la campagne précédente sur chaque tuile",
         pourquoi="Voir d'un coup d'œil ce qui s'améliore ou se dégrade, coloré selon le sens de l'indicateur.",
         prerequis="—", effort="—"),
    dict(id="F3", statut="Fait", titre="Top des messages en anomalie (Pareto)",
         pourquoi="Corriger d'abord les messages qui pèsent le plus.", prerequis="—", effort="—"),
    dict(id="F4", statut="Fait", titre="Lignes en anomalie et catalogue des règles",
         pourquoi="Montrer quelles lignes sont fausses, avec un message en clair, et décrire chaque règle.",
         prerequis="—", effort="—"),
    dict(id="F5", statut="Fait", titre="ISIN fictifs à 12 caractères avec clé de contrôle valide",
         pourquoi="Le générateur produisait des codes à 13 caractères.", prerequis="—", effort="—"),
]

ORDRE = ["En attente de décision", "Plus tard", "À vérifier", "Fait"]
ICONES = {"En attente de décision": "🟠", "Plus tard": "🗓️", "À vérifier": "🔬", "Fait": "✅"}


def tableau() -> pd.DataFrame:
    return pd.DataFrame(ELEMENTS)


def afficher_feuille_de_route() -> None:
    import streamlit as st

    df = tableau()
    cols = st.columns(len(ORDRE))
    for col, s in zip(cols, ORDRE):
        col.metric(f"{ICONES[s]} {s}", int((df["statut"] == s).sum()))
    for s in ORDRE:
        st.markdown(f"#### {ICONES[s]} {s}")
        for e in [x for x in ELEMENTS if x["statut"] == s]:
            with st.container(border=True):
                st.markdown(f"**{e['id']} · {e['titre']}**" + (f"  ·  effort : {e['effort']}" if e["effort"] != "—" else ""))
                st.markdown(f"*Pourquoi* : {e['pourquoi']}")
                if e["prerequis"] != "—":
                    st.markdown(f"*Prérequis / décision* : {e['prerequis']}")
    st.download_button("⬇️ Exporter la feuille de route (CSV)", df.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="feuille_de_route.csv", mime="text/csv")
