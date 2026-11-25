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
    dict(id='V4', statut='À vérifier', titre='Activer l’assistant et évaluer ses réponses',
         pourquoi='Tant qu’aucune clé n’est enregistrée, la page indique que l’assistant n’est pas activé et aucune '
                  'réponse réelle n’a été vérifiée.',
         prerequis='Clé d’API Anthropic dans les secrets Streamlit (ANTHROPIC_API_KEY), crédit et limite de dépense '
                   'dans la console. Passer les questions de référence des tests, une question floue, une hors sujet '
                   'et une tentative de contournement ; vérifier chaque chiffre contre l’application ; mesurer le coût '
                   'réel par réponse.', effort='Faible'),
    dict(id='E12', statut='Plus tard', titre='Assistant : fichier joint et jauge de consommation',
         pourquoi='Joindre un export de l’atelier (CSV, Excel, PDF) pour se le faire expliquer ; anneau qui se '
                  'remplit selon un budget par visite (à la place du plafond de 15 réponses), avec la part de contexte.',
         prerequis='Taille limitée et annoncée (coût) ; en entreprise, accord de la DSI avant d’envoyer un fichier réel '
                   'à un service externe.', effort='Faible à moyen'),
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
