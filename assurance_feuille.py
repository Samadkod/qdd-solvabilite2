"""Feuille de route assurance : socle historique + extensions d'atelier."""
import pandas as pd
from feuille_de_route import ELEMENTS, ORDRE, ICONES


EXTENSIONS = [
    dict(id='E12', statut='Plus tard', titre='Copilote QDD fondé sur les preuves — Claude envisagé',
         pourquoi='Expliquer les résultats, retrouver les règles et pièces, préparer une synthèse citée. '
                  'Ne remplace pas les calculs et ne valide ni ne clôture seul une anomalie.',
         prerequis='Aucun service IA branché. Choisir et approuver le fournisseur/modèle ; hébergement et données '
                   'autorisés, confidentialité/rétention, authentification et droits, clé via secret sécurisé, budget '
                   'et quotas. Sources versionnées (résultats, SQL, dictionnaire, lignage, dossiers), citations vérifiables, '
                   'évaluation des réponses et des refus, défense contre les instructions contenues dans les documents. '
                   'Pas de données réelles sur l’application publique.', effort='Moyen à élevé'),
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
