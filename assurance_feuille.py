"""Feuille de route assurance : socle historique + extensions d'atelier."""
import pandas as pd
from feuille_de_route import ELEMENTS, ORDRE, ICONES


EXTENSIONS = [
    dict(id='F16', statut='Fait', titre='Assistant QDD (Claude) construit et publié',
         pourquoi='Page « Assistant QDD » : l’utilisateur pose sa question avec ses mots ; Claude (API Anthropic, '
                  'Opus 5.5) interroge le moteur par 9 outils en lecture seule et répond avec les chiffres de la '
                  'campagne affichée, sources visibles sous chaque réponse. Historique de la visite, dates, export, '
                  'coût de la session, plafond par visite ; refus hors sujet et consignes non contournables.',
         prerequis='Outils comparés au moteur, boucle testée avec un faux client, aucune clé dans le dépôt '
                   '(tests/test_assistant_qdd.py). Principes d’interface repris d’un outil d’entreprise, sans son contenu.',
         effort='—'),
    dict(id='F28', statut='Fait', titre='Assistant activé et évalué sur ses réponses réelles',
         pourquoi='Clé enregistrée le 26/11/2026. 15 questions réelles vérifiées une à une contre le moteur et la base : '
                  '9 en mode normal (3 erreurs de comptage, corrigées par F24 puis revérifiées), 3 revérifiées, 3 en mode '
                  'diagnostic (exactes). Verdict, hors sujet et tentative de contournement correctement traités.',
         prerequis='Coût total des évaluations : environ 1,50 $. À refaire après chaque changement des consignes ou des '
                   'consultations.', effort='—'),
    dict(id='F19', statut='Fait', titre='Assistant : fichier joint et jauge de consommation',
         pourquoi='Joindre un export de l’atelier (CSV, Excel, PDF, texte) pour se le faire expliquer ; jauge '
                  'circulaire du budget de la visite (0,50 $), qui remplace le plafond de 15 réponses, avec la part de '
                  'contexte.',
         prerequis='Tableaux limités à 500 lignes et fichiers à 5 Mo (annoncé à l’utilisateur) ; le fichier est traité '
                   'comme une donnée, jamais comme des consignes. En entreprise, accord de la DSI avant d’envoyer un '
                   'fichier réel à un service externe.', effort='—'),
    dict(id='F20', statut='Fait', titre='Assistant : suivi en direct, consultations détaillées, avis',
         pourquoi='Pendant la réponse, l’étape en cours et la durée s’affichent ; chaque réponse indique son temps, '
                  'ses consultations du moteur, ses jetons et son coût, avec trois onglets (réponse, ce qu’il a '
                  'consulté, réflexion). Un clic sur une consultation montre ce qu’il a demandé et ce qu’il a obtenu. '
                  'Avis utile / pas utile, régénérer la dernière réponse. Deux jauges (contexte, budget de la '
                  'visite) avec une info-bulle en langage simple ; réflexion et consultations cochées affichées '
                  'pendant la réponse.',
         prerequis='Avis gardés le temps de la visite et repris dans l’export ; les conserver suppose E14. Pas de '
                   'bouton « Arrêter » : Streamlit ne sait pas interrompre une réponse en cours.', effort='—'),
    dict(id='F21', statut='Fait', titre='Fiche de l’assistant',
         pourquoi='Une page de présentation : ce qu’il fait et ne fait pas, comment il marche (demander, il consulte, '
                  'reprendre), les données qu’il lit, le modèle et l’hébergement, la lecture seule, le budget, '
                  'les nouveautés et la version.',
         prerequis='Contenu lu dans le code de l’assistant et la feuille de route : la fiche ne peut pas dire '
                   'autre chose que ce qu’il fait (tests/test_fiche_assistant.py). Principe repris d’un outil '
                   'd’entreprise, sans son contenu.', effort='—'),
    dict(id='E16', statut='En attente de décision', titre='Mon espace : quotas, consommation, analyses, accès',
         pourquoi='Chaque utilisateur voit son budget du mois, sa consommation dans le temps, ses dernières questions '
                  '(durée, réussite) et ses accès.',
         prerequis='Dépend de E14 : connexion des utilisateurs et base de données pour garder la consommation d’une '
                   'visite à l’autre ; quotas par personne au lieu d’un budget par visite.', effort='Moyen'),
    dict(id='F25', statut='Fait', titre='Assistant : réponse et conversation en PDF',
         pourquoi='Exporter et Télécharger proposent désormais PDF (pour lire, imprimer, envoyer à un manager ou un '
                  'comité) ou Markdown (texte modifiable). Le PDF met en page le même contenu : titres, gras, listes, '
                  'tableaux, sources ; mention « données fictives » et numéro de page en pied.',
         prerequis='Bibliothèque fpdf2 (légère, sans dépendance) et police Liberation Sans embarquée (licence libre '
                   'OFL) pour les accents et symboles. PDF généré au clic.', effort='—'),
    dict(id='F24', statut='Fait', titre='Assistant : totaux fournis par le moteur, plus de comptage à la main',
         pourquoi='L’évaluation réelle a montré des erreurs de comptage (10 anomalies en retard au lieu de 11, '
                  '7 données conformes au lieu de 6, points de contrôle confondus avec contrôles). Les consultations '
                  'renvoient désormais les totaux (par statut, gravité, propriétaire, échéance dépassée), égaux aux '
                  'tuiles de la Synthèse, et une consigne interdit de compter soi-même.',
         prerequis='Totaux testés contre le moteur ; effet sur les réponses à confirmer en ligne (V4).', effort='—'),
    dict(id='F23', statut='Fait', titre='Téléphone : menu refermé après un choix, thème appliqué tout de suite',
         pourquoi='Sur téléphone, choisir n’importe quelle page du menu latéral le referme et montre la page, sans toucher '
                  'l’écran à côté. Passer en thème sombre ou clair (menu ⋮ > Settings) applique l’habillage aussitôt, '
                  'sans attendre un clic sur une autre page.',
         prerequis='Vérifié sur un iPhone simulé (Playwright) pour les 24 entrées du menu et quatre changements de thème ; '
                   'à confirmer sur un vrai téléphone.', effort='—'),
    dict(id='F22', statut='Fait', titre='Assistant : verdict, tableaux interactifs, réponse téléchargeable',
         pourquoi='Une question fermée reçoit d’abord un verdict clair. Les tableaux d’une réponse deviennent des '
                  'tableaux interactifs (recherche, plein écran, téléchargement CSV au survol). Chaque réponse se '
                  'télécharge seule, avec sa question, sa date et ses consultations.',
         prerequis='Pas de bouton « Copier » : le navigateur bloque souvent l’accès au presse-papiers depuis Streamlit ; '
                   'le téléchargement le remplace.', effort='—'),
    dict(id='F27', statut='Fait', titre='Assistant : mode diagnostic (enquête jusqu’à la ligne fautive)',
         pourquoi='Évalué en ligne le 27/11/2026 sur 3 enquêtes (C07, R04 RC décennale, origine du S.17.01) : gabarit '
                  'suivi, prouvé séparé du déduit, toutes les affirmations vérifiables exactes. Constats établis par '
                  'l’assistant lui-même : C07 et R04 sont bloquants à cause de la pénalité de retard (refaits sur les '
                  'données de septembre, 98,52 % et 99,71 %, au-dessus du seuil) ; les 60 sinistres de C07 ont tous '
                  '60 jours d’écart ; 172 sinistres RC décennale sont minorés au chargement vers l’entrepôt (F05), '
                  'pour 16,7 M€, alors que Q02 est conforme.',
         prerequis='Coût mesuré : 0,14 à 0,27 $ par enquête (moyenne 0,21 $), 31 à 74 s, 7 à 11 consultations ; '
                   'une ou deux enquêtes par visite avec le budget de 0,50 $.', effort='—'),
    dict(id='F29', statut='Fait', titre='Relances aux propriétaires, groupées par responsable',
         pourquoi='Page « Relances » : pour chaque responsable, ses anomalies échues ou à échéance dans les 30 jours '
                  'et ses contrôles à refaire, du plus urgent au moins urgent, avec un message prêt à copier ou à '
                  'télécharger (tous les messages en un fichier, liste complète en CSV). Sur la campagne N : '
                  '7 responsables, 11 échéances dépassées, 6 contrôles à refaire, 2 échéances sous 30 jours.',
         prerequis='Comptes égaux aux tuiles de la Synthèse (tests/test_relances.py). Rien n’est envoyé par '
                   'l’application : le chargé QDD relit et envoie.', effort='—'),
    dict(id='E17', statut='Plus tard', titre='Envoi des relances par la messagerie de l’entreprise',
         pourquoi='Envoyer les messages préparés par la page Relances directement aux propriétaires, et garder la '
                  'trace de l’envoi et de la réponse.',
         prerequis='En entreprise seulement : messagerie interne (courriel, Teams) avec l’accord de la DSI, annuaire '
                   'des propriétaires ; dépend de E13 (connexion, conservation).', effort='Moyen'),
    dict(id='E18', statut='Plus tard', titre='Contrôles des zones de risque non couvertes',
         pourquoi='8 zones de risque critiques sur 33 n’ont aucun contrôle (flux F04, F05, F06, F09, F13) : la note '
                  'ne mesure pas ce qui s’y passe. Ce sont aussi 8 anomalies « Couverture » récurrentes.',
         prerequis='Écrire chaque contrôle en SQL, en SAS et dans l’atelier HTML, avec son mode opératoire. Ajouter '
                   'des contrôles fait bouger la note et les valeurs de référence : à valider par le propriétaire '
                   'avant de régénérer les valeurs attendues SAS.', effort='Moyen'),
    dict(id='E19', statut='En attente de décision', titre='Sensibilité non linéaire des placements obligations',
         pourquoi='Le test de linéarité (chocs −15 %, +5 %, +30 %) donne 10,76 % d’écart pour les placements '
                  'obligations, au-dessus du seuil de 10 % : leur poids dépend du choc retenu. Les autres données '
                  'sont linéaires.',
         prerequis='Décider avec l’actuariat : garder le choc de 15 %, prendre la sensibilité la plus prudente, ou '
                   'relever le seuil. Toute option change le poids et donc la note : décision du propriétaire.',
         effort='Faible'),
    dict(id='E20', statut='Plus tard', titre='Profondeur d’historique des données',
         pourquoi='La notice ACPR demande de vérifier que l’historique est assez long pour les calculs (triangles). '
                  'Non testé : la base fictive n’a qu’une diagonale de paiements par arrêté.',
         prerequis='Triangles réels (années de survenance × années de développement), donc à faire après la prise '
                   'de poste sur les données de l’entreprise ; ne pas fabriquer de triangles fictifs.', effort='Moyen'),
    dict(id='F26', statut='Fait', titre='Assistant : garde-fous techniques',
         pourquoi='Délai maximal de 120 s par appel (au-delà, message clair, rien n’est facturé dans le budget de la '
                  'visite) ; budget revérifié après chaque tour de consultation : une enquête s’arrête dès que le '
                  'reste de la visite est dépensé ; réponse limitée à 8 000 jetons, réflexion comprise (au plus '
                  '0,16 $ en sortie par tour).',
         prerequis='Côté console Anthropic (propriétaire) : plafond de dépense mensuel et rechargement automatique '
                   'désactivé, seul vrai plafond entre les visites.', effort='—'),
    dict(id='F30', statut='Fait', titre='Dossier de comité en un clic (PDF)',
         pourquoi='En haut de la page Dossier de campagne : le document à apporter en comité, produit par le moteur '
                  'pour la campagne affichée. Où en est-on, pourquoi la note a bougé, données hors tolérance, '
                  'restitutions QRT non conformes, contrôles non refaits, qui doit agir, contrôle de niveau 2, points à '
                  'arbitrer (7 sur la campagne N, tirés de règles écrites), lignes de décision à remplir en séance, '
                  'empreinte SHA-256 des données en défaut. PDF ou Markdown.',
         prerequis='Chiffres égaux au moteur (tests/test_comite.py). Les décisions et le compte rendu restent au '
                   'comité : le dossier les prépare, il ne les écrit pas.', effort='—'),
    dict(id='F31', statut='Fait', titre='Gain de note avant correction',
         pourquoi='Page Note & données et dossier de comité : pour chaque point imparfait ou en retard, la note '
                  'recalculée par le moteur s’il était refait (même résultat, sans pénalité) ou corrigé (100 %), et '
                  'par donnée hors tolérance ce qu’il faut pour qu’elle repasse conforme. Campagne N : premier levier '
                  'R03 RC décennale (+1,06 pt) ; refaire C07 suffit à remettre la date de survenance conforme ; '
                  'la RC décennale ne redevient conforme qu’une fois ses points corrigés (+1,58 pt) ; 24 corrections '
                  'sans effet sur la note (données non critiques, restitutions QRT).',
         prerequis='Recalcul exact du moteur (sans hypothèse, la note est retrouvée à 1e-12 près), sur une copie ; '
                   'la vraie correction reste celle de l’Atelier de résolution (tests/test_gain.py).', effort='—'),
    dict(id='F33', statut='Fait', titre='Inventaire des tâches de l’équipe (gabarit de prise de poste)',
         pourquoi='Page Mise en place en entreprise : un tableau vide à remplir avec l’équipe (tâche, qui, fréquence, '
                  'heures, outil, automatisable, fonction de l’application qui la couvre) ; heures par an et heures '
                  'récupérables calculées ; téléchargement CSV.',
         prerequis='Aucune donnée inventée ni conservée par l’application ; les données réelles restent en interne.',
         effort='—'),
    dict(id='F34', statut='Fait', titre='Glossaire complet de l’application',
         pourquoi='Page « Glossaire » (Documentation › Comprendre) avec recherche : les mots du métier et de l’outil, '
                  'par catégorie, avec un lien vers la page où chacun sert. Source unique pour le guide et l’assistant.',
         prerequis='Test d’exhaustivité : chaque mot employé par les pages doit être défini (tests/test_glossaire.py).',
         effort='—'),
    dict(id='F35', statut='Fait', titre='Assistant : notice ACPR, constats de l’ACPR et glossaire',
         pourquoi='Trois consultations nouvelles : le texte exact des 74 points de la notice ACPR du 08/11/2023, les '
                  'constats sourcés de l’ACPR, les définitions du glossaire. L’assistant cite le point ou la source et '
                  'la page au lieu de répondre de mémoire.',
         prerequis='Notice découpée en points et vérifiée contre le texte du document ; à évaluer en ligne sur des '
                   'questions réglementaires.', effort='—'),
    dict(id='F36', statut='Fait', titre='Fiche de l’Atelier de résolution',
         pourquoi='En haut de l’Atelier de résolution : à quoi il sert, les 4 étapes (proposer, recontrôler, valider, '
                  'exporter), un exemple pas à pas sur les vraies lignes de la campagne (C05 · Flottes auto : 2 '
                  'sinistres à provision négative), ce qu’il fait et ne fait pas, et les 4 raisons pour lesquelles un '
                  'scénario est bloqué.',
         prerequis='Exemple rejoué de bout en bout dans les tests (correction, recontrôle sans blocage, validation '
                   'refusée au même nom puis acceptée) ; motifs de blocage alignés sur le code '
                   '(tests/test_fiche_atelier.py).', effort='—'),
    dict(id='F32', statut='Fait', titre='Constats de l’ACPR et couverture par l’application',
         pourquoi='Page « Constats de l’ACPR » (Documentation › Comprendre) : 15 faiblesses que l’ACPR relève le plus '
                  'souvent (communiqué du 11/01/2021, enquêtes 2022 et 2024), chacune avec ses chiffres, sa source, sa '
                  'page et une citation exacte, le point de la notice du 08/11/2023 concerné, ce que l’application '
                  'couvre (9 couverts, 5 partiels, 1 hors application) et ce qui reste à faire en entreprise ; chiffres '
                  'de la campagne lus dans le moteur ; grille téléchargeable.',
         prerequis='Documents de l’ACPR lus en entier ; les 15 citations vérifiées mot pour mot dans les textes. Les '
                   'enquêtes sont déclaratives (rappel de l’ACPR) ; les constats propres à un organisme restent '
                   'confidentiels et internes.', effort='—'),
    dict(id='E28', statut='Plus tard', titre='Évaluation QDD d’un projet informatique',
         pourquoi='Mission « intégrer les exigences QDD dans les projets de transformation » et notice ACPR point 18 '
                  '(le responsable QDD évalue le risque porté par les projets ; 41 % le font selon l’enquête 2024) : '
                  'une grille par projet (données critiques touchées, flux et contrôles impactés via le lignage, '
                  'recette des données, avis QDD).',
         prerequis='Repose sur le lignage et l’analyse d’impact existants ; aucun calcul nouveau.', effort='Faible'),
    dict(id='E29', statut='Plus tard', titre='Sinistralité grave : qualité des données des gros sinistres',
         pourquoi='Mission « sinistralité grave » : isoler les sinistres au-dessus d’un seuil et vérifier leurs '
                  'données une à une (dates, provision, règlements, segment), car une erreur sur un gros dossier '
                  'pèse lourd dans les provisions.',
         prerequis='Analyse hors note (aucune valeur de référence ne bouge) ; seuil de gravité à fixer avec '
                   'l’actuariat.', effort='Moyen'),
    dict(id='E30', statut='Plus tard', titre='Données de l’ORSA et de la tarification',
         pourquoi='Missions « études prospectives (ORSA) » et « analyses tarifaires » : identifier les données qui les '
                  'alimentent et leurs contrôles.',
         prerequis='À cadrer à la prise de poste : les projections ORSA et les modèles de tarif n’existent pas dans '
                   'la base fictive, et les inventer n’aurait pas de sens.', effort='Moyen'),
    dict(id='E31', statut='Plus tard', titre='Tables de correspondance maîtres (MDM)',
         pourquoi='Profil « catalogue, MDM » et notice ACPR point 62 (tables de correspondance entre branche, '
                  'segmentation propre et ligne d’activité Solvabilité 2) : une table maître segment ↔ ligne '
                  'd’activité S2, contrôlée et versionnée.',
         prerequis='Petit référentiel et un contrôle de cohérence ; les codes activité ont déjà leur référentiel.',
         effort='Faible'),
    dict(id='E32', statut='Plus tard', titre='Lecture d’une base distante par ODBC',
         pourquoi='Profil « environnements hétérogènes (bases distantes, ODBC) » : faire tourner la chaîne sur une '
                  'base distante plutôt que sur des fichiers locaux.',
         prerequis='Une base hébergée (par exemple la base Neon prévue pour E14) et un poste avec SAS et un pilote '
                   'ODBC ; SAS OnDemand ne le permet pas forcément.', effort='Moyen'),
    dict(id='E14', statut='En attente de décision', titre='Assistant : historique durable et notes sur les réponses',
         pourquoi='Retrouver ses conversations d’une visite à l’autre, noter les réponses pour améliorer l’assistant.',
         prerequis='Base de données extérieure (par exemple PostgreSQL hébergé) et connexion des utilisateurs '
                   '(compte Google ou Microsoft) ; information des utilisateurs et durée de conservation des questions. '
                   'Deux comptes à créer par le propriétaire ; à décider selon l’usage réel.', effort='Moyen'),
    dict(id='F17', statut='Fait', titre='Rapprochement avec la notice ACPR QDD',
         pourquoi='Référentiel des contrôles complété (risque, réalisation, mode opératoire), contrôle de niveau 2, '
                  'données en défaut archivées avec empreinte, fiche d’ajustement, origine des données externes, '
                  'document cadre généré. Valeurs de référence inchangées.',
         prerequis='Profondeur d’historique (point 34) non traitée : pas d’années de développement dans les données '
                   'fictives. Aucune conformité attestée.', effort='—'),
    dict(id='F18', statut='Fait', titre='Habillage entreprise et Synthèse refondue',
         pourquoi='Menu marine, en-tête compact, verdict sur une règle, points de vigilance en actions, panneaux '
                  'compacts, points critiques hors seuil, Pareto avec part cumulée ; thème sombre et anglais revus.',
         prerequis='Ancienne version conservée dans la branche sauvegarde-avant-refonte.', effort='—'),
    dict(id='E13', statut='Plus tard', titre='Workflow d’entreprise persistant et authentifié',
         pourquoi='Adapter les rôles, habilitations, échéances et validations à l’organisation après la prise de poste.',
         prerequis='Hébergement approuvé, stockage durable, authentification, séparation réelle des rôles, journal '
                   'd’audit et sauvegardes. La session Streamlit et les noms déclaratifs du bac à sable ne suffisent pas. '
                   'Étendre les corrections au-delà de C02/C05 avec clés techniques et preuves métier.', effort='Élevé'),
    dict(id='F12', statut='Fait', titre='Diagnostic explicable de campagne',
         pourquoi='Constats issus du moteur, résultat brut/retenu, antériorité, comparaison et accès aux preuves. '
                  'Hypothèses métier non affirmées.', prerequis='Tests locaux et navigation vérifiés ; données fictives uniquement.', effort='—'),
    dict(id='F13', statut='Fait', titre='Correction → recontrôle → validation en bac à sable',
         pourquoi='Corrections manuelles C02/C05 sur copie fictive, 20 règles SQL réellement rejouées, comparaison '
                  'avant/après et validation bloquée si les preuves ne passent pas. Registre historique inchangé.',
         prerequis='Parcours déclaration/recontrôle/validation vérifié dans le navigateur ; blocages et séparation déclarative testés. Usage réel couvert par E13.', effort='—'),
    dict(id='F14', statut='Fait', titre='Dossier de preuves avec manifeste SHA-256',
         pourquoi='ZIP de résultats, règles, référentiels, lignage, scénarios et événements, avec tableau des pièces '
                  'manquantes. Pas de certification ni d’audit immuable.', prerequis='ZIP téléchargé dans le navigateur ; intégrité et empreintes vérifiées.', effort='—'),
    dict(id='F15', statut='Fait', titre='Analyse d’impact sur lignage déclaré',
         pourquoi='Départ donnée, contrôle ou flux ; usages/restitutions documentés et étapes non couvertes. '
                  'Ni propagation aval prouvée ni chiffrage financier inventé.', prerequis='Jointures, lacunes et page vérifiées localement.', effort='—'),
]


def tableau():
    rows = [dict(e) for e in ELEMENTS]
    for e in rows:
        if e['id'] == 'E9':
            e['titre'] = 'Statut de correction déclarée dans le registre d’entreprise'
            e['prerequis'] += ' Le bac à sable assurance possède ce parcours séparément, sans modifier le registre historique ; voir F13 et E13.'
    return pd.DataFrame(rows + EXTENSIONS)


def afficher_feuille_de_route():
    import streamlit as st
    df = tableau()
    st.caption('Extensions assurance sur données fictives. « Fait » désigne une fonctionnalité d’atelier vérifiée, '
               'pas une mise en production ni une validation de l’organisation.')
    for col, statut in zip(st.columns(len(ORDRE)), ORDRE):
        col.metric(f'{ICONES[statut]} {statut}', int((df.statut == statut).sum()))
    for statut in ORDRE:
        st.markdown(f'#### {ICONES[statut]} {statut}')
        rows = df[df.statut == statut]
        if rows.empty:
            st.caption('Aucun élément.')
        for e in rows.to_dict('records'):
            with st.container(border=True):
                st.markdown(f'**{e["id"]} · {e["titre"]}**' + (f' · effort : {e["effort"]}' if e['effort'] != '—' else ''))
                st.write('Pourquoi :', e['pourquoi'])
                if e['prerequis'] != '—':
                    st.write('Prérequis / décision :', e['prerequis'])
    st.download_button('Exporter la feuille de route (CSV)', df.to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name='feuille_de_route.csv', mime='text/csv')
