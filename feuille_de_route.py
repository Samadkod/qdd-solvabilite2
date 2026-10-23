"""Feuille de route de l'atelier : ce qui attend une décision, ce qui est prévu, ce qui reste à vérifier, ce qui est fait.

Point unique de suivi des évolutions (à tenir à jour à chaque livraison).
"""
from __future__ import annotations

import pandas as pd

ELEMENTS = [
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
         prerequis="Au moins 6 à 8 campagnes (3 aujourd'hui) : générer des trimestres fictifs supplémentaires, sur "
                   "le modèle de N-2 (un flux aléatoire par arrêté, données existantes inchangées) ; en entreprise, "
                   "historiser les résultats à chaque campagne.",
         effort="Moyen"),
    dict(id="E6", statut="Plus tard", titre="Durées d'exécution des contrôles",
         pourquoi="Mission optimisation : repérer les traitements les plus longs, suivre leur durée dans le temps, "
                  "alerter si une durée double.",
         prerequis="Les durées sont mesurées et affichées pour chaque contrôle (page « Contrôles ») ; reste à les "
                   "historiser d'une campagne à l'autre et à alerter si une durée double. Sur les données fictives, les durées sont de quelques "
                   "millisecondes : l'intérêt est la méthode.",
         effort="Faible"),
    dict(id="E7", statut="Plus tard", titre="Justifier le poids de la date de survenance",
         pourquoi="Cette donnée est critique à dire d'expert : faute de sensibilité mesurable, elle reçoit la moyenne des "
                  "sensibilités mesurées (17,27 %), ce qui en fait la 3e donnée la plus lourde de la note.",
         prerequis="Choix de méthode à documenter dans la politique QDD, ou à remplacer par une mesure (par exemple "
                   "l'effet d'un décalage d'année de survenance sur le Best Estimate).", effort="Moyen"),
    dict(id="E9", statut="Plus tard", titre="Statut « correction déclarée, à vérifier » dans le registre",
         pourquoi="Le propriétaire signale qu'il a corrigé ; l'anomalie attend la prochaine exécution du contrôle "
                  "avant d'être clôturée. Montre où en est la résolution entre deux campagnes.",
         prerequis="Touche la règle de clôture (règle de méthode n° 2) : accord explicite du propriétaire requis. "
                   "Suppose aussi un outil où chacun peut déclarer sa correction (pas l'application publique).",
         effort="Moyen"),
    # ---------------------------------------------------------------- à vérifier
    dict(id="V2", statut="À vérifier", titre="Exécuter les corrigés des exercices SAS",
         pourquoi="Exécutés sur SAS OnDemand le 23/10/2026 : E01, E02, E03, E07, E08 et E10 donnent exactement le "
                  "résultat attendu ; les 7 autres créent une table sans l'afficher.",
         prerequis="Lancer le bloc E99 (affiche les 6 tables restantes) et lire E11 dans le journal ; comparer à « SAS pratique ».",
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
    dict(id="F7", statut="Fait", titre="Recalcul des formules du rapport Excel vérifié",
         pourquoi="Prouver que le rapport Excel, avec ses propres formules, donne les mêmes chiffres que le moteur.",
         prerequis="Recalcul par LibreOffice : 11 valeurs sur 11 identiques ; test automatique ajouté.", effort="—"),
    dict(id="F8", statut="Fait", titre="Icônes Material et affichage sur téléphone",
         pourquoi="Une iconographie sobre et cohérente ; la note visible dès le premier écran sur téléphone.",
         prerequis="—", effort="—"),
    dict(id="F6", statut="Fait", titre="Dates de sinistres fictives réalistes (C07)",
         pourquoi="Le générateur tirait la survenance sans tenir compte de la date d'effet du contrat (2 282 sinistres "
                  "signalés par C07, 46 %) et laissait des déclarations après l'arrêté (182).",
         prerequis="Décision du propriétaire (octobre 2026). Après correction : 60 lignes C07 (1,2 %), aucune "
                   "déclaration après l'arrêté ; note N 97,45 % → 97,49 %, tous les compteurs inchangés.", effort="—"),
    dict(id="F11", statut="Fait", titre="Chaîne SAS exécutée : 59 valeurs sur 59 égales à Python",
         pourquoi="SAS OnDemand, 23/10/2026, lancer_qdd.sas : les 3 campagnes, la variation et le registre sont "
                  "identiques à la référence Python. La première exécution (44/59) a révélé un fichier de relances "
                  "SCR incomplet pour N-2, corrigé et désormais testé. Page « Vérification SAS » : 98_verifier.sas "
                  "écrit verification_sas.csv, que l'application affiche.",
         prerequis="—", effort="—"),
    dict(id="F10", statut="Fait", titre="Liste de suivi des contrôles",
         pourquoi="Chaque point de contrôle avec deux statuts séparés (exécution / résultat), sa dernière "
                  "réalisation, sa prochaine échéance, sa durée, sa tendance sur les campagnes ; filtres, points à surveiller, panneau "
                  "d'avancement de la campagne, et accès direct aux lignes en anomalie.",
         prerequis="Principes repris d'un outil de pilotage de migration (aucun contenu repris). Les boutons d'action "
                   "(suspendre, valider, relancer) sont écartés : ils supposent un vrai serveur et des utilisateurs.",
         effort="—"),
    dict(id="F9", statut="Fait", titre="Cycle de vie complet du registre (campagne N-2)",
         pourquoi="Avec deux campagnes, aucune anomalie n'était clôturée. La campagne fictive du 31/03/2026 ouvre "
                  "13 anomalies ; N-1 en clôture 3 (dates de survenance C06, règlements R04 RC décennale, primes "
                  "S.05.01 Q04 RC décennale). R04 RC décennale montre tout le parcours : ouverte, clôturée, puis "
                  "rouverte en N sous le type « Contrôle non réalisé ».",
         prerequis="Décision du propriétaire (octobre 2026). Données N-1 et N identiques au bit près ; note et "
                   "compteurs de N inchangés.", effort="—"),
    dict(id="F5", statut="Fait", titre="ISIN fictifs à 12 caractères avec clé de contrôle valide",
         pourquoi="Le générateur produisait des codes à 13 caractères.", prerequis="—", effort="—"),
]

ORDRE = ["En attente de décision", "Plus tard", "À vérifier", "Fait"]
ICONES = {"En attente de décision": ":material/pending:", "Plus tard": ":material/schedule:",
          "À vérifier": ":material/science:", "Fait": ":material/check_circle:"}


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
        if not any(x["statut"] == s for x in ELEMENTS):
            st.caption("Aucun élément.")
        for e in [x for x in ELEMENTS if x["statut"] == s]:
            with st.container(border=True):
                st.markdown(f"**{e['id']} · {e['titre']}**" + (f"  ·  effort : {e['effort']}" if e["effort"] != "—" else ""))
                st.markdown(f"*Pourquoi* : {e['pourquoi']}")
                if e["prerequis"] != "—":
                    st.markdown(f"*Prérequis / décision* : {e['prerequis']}")
    st.download_button("Exporter la feuille de route (CSV)", icon=":material/download:", data=df.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="feuille_de_route.csv", mime="text/csv")
