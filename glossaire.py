"""Glossaire de l'application : tous les mots du métier et de l'outil, en clair, avec la page où ils servent.

Source unique, utilisée par la page « Glossaire », le guide et l'assistant (consultation « glossaire »).
TERMES_REQUIS liste les mots employés par les pages : tests/test_glossaire.py vérifie que chacun est défini.
"""
from __future__ import annotations

# (terme, catégorie, définition, page de l'application où le terme sert — clé de PAGES, ou vide)
TERMES = [
    ('Solvabilité 2', 'Réglementation', "La réglementation européenne des assureurs (depuis 2016). Elle oblige à prouver qu'on a assez de capital, à bien gérer ses risques et à rendre des comptes au régulateur.", ''),
    ('ACPR', 'Réglementation', "Le gendarme français de l'assurance et de la banque. C'est lui qui reçoit les états réglementaires et qui contrôle.", ''),
    ('Commissaires aux comptes (CAC)', 'Réglementation', 'Les auditeurs externes qui certifient les comptes. Ils peuvent demander comment une donnée a été produite et contrôlée.', ''),
    ('SCR', 'Réglementation', "Le capital minimum exigé. Il doit permettre de survivre à une très mauvaise année, du genre qui n'arrive qu'une fois tous les 200 ans.", ''),
    ('MCR', 'Réglementation', "Un deuxième plancher de capital, plus bas que le SCR. En dessous, le régulateur peut retirer l'agrément.", ''),
    ('Provisions techniques / Best Estimate (BE)', 'Réglementation', "L'argent mis de côté pour payer les sinistres déjà arrivés ou à venir. Le Best Estimate est la meilleure estimation de ce qu'on paiera réellement.", ''),
    ('ORSA', 'Réglementation', "L'évaluation interne des risques et de la solvabilité : l'assureur projette lui-même sa situation sur plusieurs années, au moins une fois par an.", ''),
    ('QRT', 'Réglementation', 'Les tableaux officiels envoyés au régulateur, chaque trimestre et chaque année (S.02.01 = bilan, S.05.01 = primes et sinistres, S.06.02 = liste des placements, S.17.01 = provisions non-vie, S.19.01 = triangles de sinistres).', 'controles'),
    ('SFCR / RSR', 'Réglementation', 'Les rapports écrits de Solvabilité 2 : le SFCR est public, le RSR est réservé au régulateur.', ''),
    ('Fonction actuarielle', 'Réglementation', "L'équipe d'actuaires qui donne son avis sur les provisions, y compris sur la qualité des données utilisées. Elle écrit un rapport au moins une fois par an.", ''),
    ('QDD', 'Méthode QDD', "Qualité des données. Vérifier que les données sont complètes (rien ne manque), exactes (pas d'erreur) et pertinentes (adaptées à l'usage).", ''),
    ('Donnée critique', 'Méthode QDD', "Une donnée dont une erreur ferait bouger le SCR de façon notable. Ce sont celles qu'on surveille en priorité.", 'donnees'),
    ('Sensibilité', 'Méthode QDD', 'De combien le SCR bouge quand la donnée bouge. Forte sensibilité = donnée à surveiller de très près.', 'donnees'),
    ('Seuil de significativité', 'Méthode QDD', "L'erreur maximale acceptée sur le SCR, toutes données confondues. Au-delà, l'erreur est jugée grave.", ''),
    ('Tolérance / note minimum', 'Méthode QDD', "L'erreur acceptée sur une donnée. Plus la donnée pèse lourd, plus la tolérance est petite et plus la note minimum est haute.", 'donnees'),
    ('Contrôle', 'Contrôles et anomalies', 'Une vérification automatique ou manuelle : « y a-t-il des doublons ? », « la gestion et la comptabilité donnent-elles le même total ? »…', 'regles'),
    ('Contrôle de niveau 1 / niveau 2', 'Contrôles et anomalies', 'Niveau 1 : fait par les équipes qui produisent la donnée. Niveau 2 : fait par une équipe indépendante (risques, conformité, QDD).', 'controles'),
    ('Rapprochement', 'Contrôles et anomalies', "Comparer le même chiffre dans deux ou trois outils différents. S'ils ne sont pas égaux, au moins un des deux est faux.", ''),
    ('Antériorité', 'Méthode QDD', 'Le nombre de périodes écoulées depuis la dernière fois que le contrôle a été fait. 0 = fait à temps.', 'controles'),
    ('Dégradation', 'Méthode QDD', 'La pénalité appliquée à un contrôle trop ancien. Un contrôle vieux de 6 mois ne garantit plus grand-chose.', ''),
    ('Lignage', 'Données et lignage', "Le trajet d'une donnée, de sa saisie jusqu'au calcul du SCR, en passant par chaque outil.", 'lignage'),
    ('Flux', 'Données et lignage', "Un passage de la donnée d'un outil à un autre (exemple : le chargement nocturne de l'outil de gestion vers l'entrepôt).", 'lignage'),
    ('Zone de risque', 'Données et lignage', "Un flux où la donnée peut s'abîmer : ressaisie manuelle, chargement automatique, transformation…", 'lignage'),
    ('Propriétaire de données', 'Données et lignage', "La direction responsable d'une donnée. C'est elle qui doit corriger les erreurs, pas l'équipe QDD.", ''),
    ('Dictionnaire des données', 'Données et lignage', "La carte d'identité de chaque donnée : définition, règle de calcul, format, propriétaire, états où elle apparaît.", 'lignage'),
    ('Catalogue / MDM', 'Données et lignage', "Le catalogue recense toutes les données disponibles. Le MDM (gestion des données de référence) garantit qu'une même donnée de référence (un client, un code activité) a une seule version officielle.", ''),
    ('Registre des anomalies', 'Contrôles et anomalies', 'Le carnet de bord des problèmes détectés : qui doit corriger, pour quand, et où on en est.', 'anomalies'),
    ("Piste d'audit", 'Contrôles et anomalies', 'La trace de tout ce qui a été lancé, pour pouvoir prouver comment un chiffre a été obtenu.', 'dossier'),
    ('SAS / PROC SQL', 'Technique', "Le logiciel de traitement de données utilisé en actuariat. PROC SQL permet d'y écrire des requêtes SQL.", 'code'),
    ('ODBC', 'Technique', "Le « tuyau » standard qui permet à SAS ou à Qlik de lire directement les bases de données de l'entreprise.", ''),
    ('Qlik Sense', 'Technique', "L'outil de tableaux de bord : il affiche les résultats de façon visuelle pour les responsables.", ''),
    ('ISIN / CIC', 'Données et lignage', "ISIN : le numéro d'identité d'un titre financier. CIC : le code qui dit de quel type d'actif il s'agit (action, obligation…).", ''),
    ('Note QDD', 'Méthode QDD', 'Le pourcentage de fiabilité des données qui comptent dans le calcul du capital : moyenne des notes des données critiques, pondérée par leur sensibilité. 100 % = aucune erreur détectée.', 'synthese'),
    ('Objectif de note', 'Méthode QDD', "La note QDD minimum à atteindre, déduite du seuil de significativité : en dessous, l'erreur possible sur le SCR dépasse ce que l'entreprise accepte.", 'synthese'),
    ("Note d'une donnée", 'Méthode QDD', 'La moyenne pondérée des résultats des contrôles qui portent sur cette donnée, après pénalité de retard.', 'donnees'),
    ('Conforme / À corriger / Bloquant', 'Méthode QDD', "Les trois statuts d'une donnée ou d'un contrôle. Conforme : au-dessus de son minimum. À corriger : moins de 2 points en dessous. Bloquant : plus de 2 points en dessous (ou, pour une restitution QRT, sous son seuil fixe).", 'synthese'),
    ('Non noté', 'Méthode QDD', "Statut d'une donnée non critique ou d'un contrôle sans seuil : contrôlé, mais sans effet sur la note.", 'donnees'),
    ('Critères exactitude / exhaustivité / pertinence', 'Méthode QDD', "Les trois critères de qualité de Solvabilité 2 (notés E, X, P dans l'application) : pas d'erreur, rien ne manque, adapté à l'usage.", 'donnees'),
    ('Choc et test de linéarité', 'Méthode QDD', "Pour mesurer la sensibilité, on augmente la donnée de 15 % et on regarde le SCR. On refait le calcul à −15 %, +5 % et +30 % : si les résultats s'écartent de plus de 10 %, la sensibilité n'est pas linéaire.", 'donnees'),
    ("Criticité à dire d'expert", 'Méthode QDD', 'Donnée déclarée critique par jugement plutôt que par un test de sensibilité. La notice ACPR demande de formaliser cet avis.', 'donnees'),
    ('Point de contrôle', 'Contrôles et anomalies', 'Un contrôle appliqué à un segment (par exemple R04 sur la RC décennale). Un même contrôle peut avoir plusieurs points.', 'controles'),
    ('Segment (maille)', 'Données et lignage', "Le découpage de l'activité sur lequel on contrôle : RC décennale, dommages-ouvrage, flottes auto, actions, obligations, ou « tous ».", 'controles'),
    ('Contrôle de cohérence (C01 à C10)', 'Contrôles et anomalies', "Contrôle ligne par ligne d'une même table (doublon, montant négatif, date impossible, code inconnu). Il produit une liste de lignes fautives.", 'lignes'),
    ('Contrôle de rapprochement (R01 à R06)', 'Contrôles et anomalies', "Comparaison d'un même total entre deux ou trois outils (gestion, entrepôt, comptabilité, actuariat).", 'regles'),
    ('Restitution QRT (Q01 à Q04)', 'Contrôles et anomalies', "Contrôle qu'un état réglementaire reprend exactement sa source. Seuil fixe de 99,9 %, suivi à part et exclu de la note.", 'controles'),
    ("Seuil d'un contrôle", 'Contrôles et anomalies', "Le résultat minimum attendu d'un point de contrôle : la note minimum de la donnée qu'il contrôle, ou 99,9 % pour une restitution QRT.", 'controles'),
    ('Contrôle de chargement (niveau 0)', 'Contrôles et anomalies', 'Vérifie avant tout calcul que les tables sont arrivées (aucune table vide, pas de variation de volume inexpliquée) et que chaque requête de contrôle a pu tourner. Hors note.', 'chargement'),
    ('Lignes en anomalie', 'Contrôles et anomalies', 'Les contrats, sinistres ou titres précis qui font échouer un contrôle de cohérence, avec un message en clair.', 'lignes'),
    ('Anomalie', 'Contrôles et anomalies', 'Un problème inscrit au registre : constat, gravité, propriétaire, échéance, action attendue. Types : qualité de donnée, contrôle non réalisé, couverture, restitution QRT.', 'anomalies'),
    ('Anomalie récurrente', 'Contrôles et anomalies', 'Une anomalie déjà présente à la campagne précédente et toujours pas résolue.', 'anomalies'),
    ('Anomalie de couverture', 'Contrôles et anomalies', "Une zone de risque du lignage qu'aucun contrôle ne surveille. Elle se clôture dès qu'un contrôle couvre le flux.", 'anomalies'),
    ('Échéance', 'Contrôles et anomalies', "La date à laquelle une anomalie doit être traitée. Comparée à la date d'arrêté pour dire si elle est dépassée.", 'relances'),
    ("Clôture d'une anomalie", 'Contrôles et anomalies', "Une anomalie n'est clôturée que si le contrôle a été refait dans la campagne et n'est plus en anomalie.", 'anomalies'),
    ('Contrôle de niveau 2 (constats)', 'Contrôles et anomalies', "Dans l'application : 7 vérifications à règle écrite sur les contrôles eux-mêmes (référentiel complet, faits à temps, couverture, données externes…).", 'controles'),
    ('Campagne / arrêté', 'Méthode QDD', "Une campagne est l'exercice de contrôle mené pour une date d'arrêté (fin de trimestre). N = la plus récente, N-1 la précédente.", 'synthese'),
    ('Variation de la note', 'Méthode QDD', "La décomposition de l'écart de note entre deux campagnes, facteur par facteur (qualité mesurée, retard des contrôles, sensibilités…).", 'donnees'),
    ('Données externes', 'Données et lignage', "Données fournies par un tiers (ici, le dépositaire des titres). La notice ACPR exige qu'elles soient documentées et contrôlées comme les données internes.", 'lignage'),
    ('Entrepôt de données', 'Données et lignage', "La base centrale où les données des outils de gestion sont chargées avant d'être utilisées par l'actuariat.", 'lignage'),
    ("Mode d'alimentation", 'Données et lignage', "Automatique ou manuel : comment un flux passe d'un outil à l'autre. Un flux manuel est plus exposé aux erreurs.", 'lignage'),
    ('RC décennale', 'Assurance BTP', 'Responsabilité civile décennale : la garantie obligatoire du constructeur pendant 10 ans après la réception des travaux.', 'donnees'),
    ('Dommages-ouvrage', 'Assurance BTP', "Assurance obligatoire du maître d'ouvrage : elle préfinance les réparations des désordres relevant de la décennale.", 'donnees'),
    ('Taux de cession', 'Assurance BTP', 'La part des risques transférée au réassureur.', 'donnees'),
    ("Date de survenance / date d'effet", 'Assurance BTP', "Survenance : quand le sinistre s'est produit. Effet : quand le contrat commence. Un sinistre ne peut pas survenir avant l'effet du contrat (contrôle C07).", 'lignes'),
    ('Atelier de résolution', "Outils de l'application", "La correction d'une donnée sur une copie, suivie du recontrôle réel des 20 règles et d'une validation par une autre personne. La base de référence n'est jamais modifiée.", 'resolution'),
    ('Validation déclarative', "Outils de l'application", "La validation d'une correction par une autre personne, dont le nom est saisi : sans connexion des utilisateurs dans cette version.", 'resolution'),
    ("Données en défaut / fiche d'ajustement", "Outils de l'application", "Les lignes en anomalie sont figées et conservées avant toute correction (notice ACPR, point 37) ; la fiche d'ajustement documente chaque correction.", 'dossier'),
    ('Manifeste SHA-256', "Outils de l'application", "Une empreinte numérique de chaque fichier de preuve : si un fichier change d'un seul octet, l'empreinte change. Prouve que rien n'a été modifié.", 'dossier'),
    ('Document cadre', "Outils de l'application", 'Le document qui organise le dispositif QDD (périmètre, critères, rôles, comités, outils), exigé par la notice ACPR (points 16-17). Généré à partir des référentiels.', 'dossier'),
    ('Relances', "Outils de l'application", 'La page qui liste, par responsable, ses anomalies et ses contrôles à refaire, avec un message prêt à envoyer.', 'relances'),
    ('Dossier de comité', "Outils de l'application", 'Le document PDF à apporter en comité QDD : état, variation, qui doit agir, points à arbitrer, décisions à prendre.', 'dossier'),
    ('Gain de note', "Outils de l'application", 'Ce que rapporterait une correction : la note recalculée par le moteur si un point était refait ou corrigé.', 'donnees'),
    ('Mode diagnostic', "Outils de l'application", "Le mode d'enquête de l'assistant : il cherche la cause jusqu'à la ligne fautive et sépare ce qui est prouvé de ce qui est déduit.", 'assistant'),
    ('Notice ACPR qualité des données', 'Réglementation', "Le document de l'ACPR du 08/11/2023 qui précise comment elle contrôle la qualité des données Solvabilité 2 (74 points).", 'acpr'),
    ('Comité QDD', 'Réglementation', "L'instance qui suit les indicateurs de qualité, arbitre les priorités et décide des plans de remédiation (notice ACPR, points 21-24).", 'dossier'),
    ('Responsable QDD / relais', 'Réglementation', 'Le responsable QDD pilote le dispositif ; les relais sont ses correspondants dans les directions qui produisent les données.', 'guide'),
]

GLOSSAIRE = [(t, d) for t, _, d, _ in TERMES]  # forme historique (terme, définition) utilisée par le guide
CATEGORIES = ["Réglementation", "Méthode QDD", "Contrôles et anomalies", "Données et lignage", "Assurance BTP",
              "Outils de l'application", "Technique"]

# Mots employés dans les pages de l'application : chacun doit avoir une entrée (recherche sans casse).
TERMES_REQUIS = [
    "Note QDD", "Objectif", "Donnée critique", "Sensibilité", "Seuil de significativité", "note minimum", "Antériorité",
    "Dégradation", "Conforme", "À corriger", "Bloquant", "Non noté", "exactitude", "linéarité", "dire d'expert",
    "Point de contrôle", "Segment", "cohérence", "Rapprochement", "Restitution QRT", "Seuil d'un contrôle",
    "Contrôle de chargement", "Lignes en anomalie", "Anomalie", "récurrente", "couverture", "Échéance", "Clôture",
    "niveau 2", "Campagne", "Variation", "Lignage", "Flux", "Zone de risque", "Données externes", "Entrepôt",
    "Mode d'alimentation", "Dictionnaire des données", "Propriétaire", "RC décennale", "Dommages-ouvrage",
    "Taux de cession", "survenance", "Atelier de résolution", "Validation déclarative", "Données en défaut",
    "SHA-256", "Document cadre", "Relances", "Dossier de comité", "Gain de note", "Mode diagnostic", "Notice ACPR",
    "Comité QDD", "SCR", "QRT", "ACPR", "Provisions techniques", "Fonction actuarielle", "Piste d'audit",
]


def chercher(terme: str = "") -> list[dict]:
    """Entrées dont le terme ou la définition contient le mot cherché (sans casse) ; tout si vide."""
    m = (terme or "").strip().lower()
    return [{"terme": t, "categorie": c, "definition": d, "page": p} for t, c, d, p in TERMES
            if not m or m in t.lower() or m in d.lower()]


def afficher(aller, pages: dict) -> None:
    import streamlit as st

    st.markdown("Tous les mots du métier et de l'application, en clair. Cherchez un mot, ou parcourez par catégorie.")
    q = st.text_input("Chercher un mot", placeholder="ex. antériorité, SCR, relances…", key="glossaire_q",
                      label_visibility="collapsed")
    res = chercher(q)
    st.caption(f"{len(res)} terme{'s' if len(res) > 1 else ''} sur {len(TERMES)}.")
    for cat in CATEGORIES:
        bloc = [r for r in res if r["categorie"] == cat]
        if not bloc:
            continue
        st.markdown(f"#### {cat}")
        for r in sorted(bloc, key=lambda x: x["terme"].lower()):
            g, d = st.columns([1, 3], vertical_alignment="top")
            g.markdown(f"**{r['terme']}**")
            d.markdown(r["definition"])
            if r["page"] in pages and r["page"] != "glossaire":
                if d.button(f"Où le voir : {pages[r['page']][1]}", key=f"glo_{r['terme']}", type="tertiary",
                            icon=":material/arrow_forward:"):
                    aller(r["page"])
