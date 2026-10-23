"""Page « Mise en place en entreprise » : ce qu'il faut changer une fois, puis faire chaque trimestre,
pour faire tourner la chaîne SAS (sas/) sur les vraies données.

La liste des tables sources et de leurs colonnes est lue dans sas/01_import_demo.sas et dans les en-têtes
des CSV de démonstration : elle suit le code (testé dans tests/test_passage_entreprise.py).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent
IMPORT = RACINE / "sas" / "01_import_demo.sas"
DEMO = RACINE / "sas" / "donnees_demo"

# Une fois pour toutes : fichier, ce qui change, qui fournit l'information
UNE_FOIS = [
    ("1", "lancer_qdd.sas", "`%let RACINE = …` : le dossier du projet sur le serveur SAS.", "Vous"),
    ("2", "00_config.sas", "`libname SI` : la bibliothèque des données sources (tables SAS existantes, ou base "
     "via ODBC : le modèle est en commentaire dans le fichier). `libname QDD` : un dossier **permanent** "
     "(le registre et l'historique doivent survivre d'un trimestre à l'autre).", "DSI / équipe données (DSN, droits en lecture)"),
    ("3", "Nouveau `01_sources.sas`", "Une **vue** par table attendue, qui renomme leurs colonnes avec nos noms "
     "(liste ci-dessous). Dans `99_executer.sas`, l'inclure à la place de `01_import_demo.sas`.",
     "Équipe données, propriétaires des données"),
    ("4", "Référentiels", "Réécrire avec les métiers : dictionnaire (`repertoire_donnees`), contrôles "
     "(`referentiel_controles`), lignage (`lignage_flux`, `lignage_donnees`). Garder leur import CSV : c'est la "
     "partie « Référentiels QDD » de `01_import_demo.sas`, à déplacer dans `01_sources.sas`.",
     "Vous, avec chaque propriétaire de donnée"),
    ("5", "Historique initial", "`historique_resultats.csv` : derniers résultats des contrôles déjà faits avant "
     "l'outil. À charger **une seule fois**, au premier lancement.", "Vous (résultats des campagnes passées)"),
    ("6", "relances_scr.csv", "Le SCR recalculé quand on fausse chaque donnée critique (chocs 0, −15 %, +5 %, "
     "+15 %, +30 %), au format `arrete;donnee_id;choc;valeur;scr`.", "Équipe qui calcule le SCR"),
    ("7", "99_executer.sas", "Supprimer la ligne qui vide le registre et le journal (« Démo : on repart d'un "
     "registre vide ») ; ne garder qu'**une** campagne par lancement (celle du trimestre) ; retirer l'appel à "
     "`98_verifier.sas`, propre à la démo (comparaison à Python).", "Vous"),
    ("8", "00_config.sas (paramètres)", "Faire valider puis écrire dans la politique QDD : seuil de "
     "significativité 1 %, écart de SCR toléré 0,5 %, pénalité de retard 5 %, marge orange 2 points, choc 15 %.",
     "Votre responsable, fonction actuarielle"),
    ("9", "07_export_qlik.sas", "Le dossier de sortie que Qlik Sense viendra lire (`&SORTIE`).", "Équipe BI / Qlik"),
]

# Où chercher chaque table attendue en entreprise
OU_TROUVER = {
    "gestion_contrats": "Outil de gestion des contrats : une ligne par contrat et par arrêté.",
    "dwh_contrats": "Entrepôt de données (datawarehouse), table des contrats.",
    "compta_primes": "Comptabilité : primes acquises par segment.",
    "gestion_sinistres": "Outil de gestion des sinistres : une ligne par sinistre.",
    "dwh_sinistres": "Entrepôt de données, table des sinistres.",
    "actuariat_inputs": "Données d'entrée de l'outil de provisionnement (totaux par segment).",
    "compta_reglements": "Comptabilité : règlements de sinistres par segment.",
    "reassurance_traites": "Service réassurance : taux de cession des traités en vigueur.",
    "modele_parametres": "Paramètres du modèle SCR (taux de cession utilisé).",
    "placements_depositaire": "Relevé du dépositaire (inventaire des titres, ISIN, CIC).",
    "placements_compta": "Comptabilité des placements (valeur de marché par titre).",
    "ref_activites_btp": "Nomenclature des codes activité (NAF du BTP ou nomenclature interne).",
    "actuariat_be": "Sortie de l'outil de provisionnement : best estimate par segment.",
    "qrt_s0501": "État S.05.01 remis (primes) : outil de reporting réglementaire.",
    "qrt_s1701": "État S.17.01 remis (provisions techniques non-vie).",
    "qrt_s1901_diagonale": "État S.19.01 remis (triangles), dernière diagonale.",
    "qrt_s0602": "État S.06.02 remis (liste des actifs).",
    "qrt_s0201": "État S.02.01 remis (bilan), postes de placements.",
}

DEMARRAGE = [
    "**Accès** : un espace SAS (SAS Studio ou Enterprise Guide), un dossier projet permanent, les droits en "
    "lecture sur les tables sources, et si besoin un DSN ODBC créé par la DSI.",
    "**Inventaire** : pour chaque table de la liste ci-dessous, trouver leur table et leurs colonnes "
    "équivalentes. Noter les écarts (colonne absente, autre découpage par segment).",
    "**Pilote réduit** : une donnée critique (par exemple les provisions d'un segment), 3 ou 4 contrôles, "
    "un arrêté **déjà clôturé**. Ne garder que ces lignes dans `referentiel_controles`.",
    "**Comparer** les résultats à ce que l'équipe sait déjà de cet arrêté (écarts connus, ajustements faits). "
    "Un écart inexpliqué se règle avant d'aller plus loin.",
    "**Référence de non-régression** : garder les résultats du pilote validé ; toute modification du code doit "
    "les retrouver à l'identique (le principe de `98_verifier.sas`, appliqué à vos chiffres).",
    "**Élargir** donnée par donnée, avec l'accord de votre responsable, puis faire valider les paramètres.",
    "**Planifier** le lancement trimestriel une fois deux ou trois campagnes réussies à la main.",
]

CHAQUE_TRIMESTRE = [
    "Recevoir les relances du SCR de l'arrêté et les ajouter à `relances_scr`.",
    "Dans `99_executer.sas`, renseigner la campagne : nom, date d'arrêté, contrôles **non réalisés** ce "
    "trimestre (`non_realises=`).",
    "Lancer `lancer_qdd.sas`, puis lire le journal : lignes `ERROR`, `WARNING`, contrôles de chargement "
    "(tables vides, variations de volume de plus de 10 %).",
    "Lire le rapport Excel : note, données hors tolérance, pourquoi la note a bougé.",
    "Registre des anomalies : relancer chaque propriétaire pour les anomalies ouvertes et en retard.",
    "Vérifier que l'export Qlik a été rechargé.",
]

A_NE_PAS_FAIRE = [
    "Modifier les macros de contrôle (`02_controles.sas`) pour coller à leurs noms de colonnes : passer par les "
    "vues de `01_sources.sas`, sinon chaque changement de leur côté casse les contrôles.",
    "Vider le registre ou recharger l'historique à chaque lancement : on perd le cycle de vie des anomalies et "
    "le calcul du retard des contrôles.",
    "Relancer toutes les campagnes passées chaque trimestre : une campagne par lancement, les précédentes restent "
    "dans la bibliothèque QDD.",
    "Changer un paramètre de méthode en cours d'année sans le tracer : l'analyse de variation le prendrait pour "
    "une évolution de la qualité. Un changement = une décision écrite, datée.",
    "Importer les sources avec PROC IMPORT : les types et longueurs devinés changent d'un fichier à l'autre.",
    "Ramener des tables entières sans filtrer sur la date d'arrêté dans la base (pass-through, modèle dans "
    "`00_config.sas`).",
]


def tables_attendues() -> pd.DataFrame:
    """Tables de la bibliothèque SI que lit la chaîne, avec leurs colonnes, tirées de 01_import_demo.sas."""
    texte = IMPORT.read_text(encoding="utf-8")
    lignes = []
    for nom in re.findall(r"%imp\((\w+),\s*SI,", texte):
        entete = (DEMO / f"{nom}.csv").read_text(encoding="utf-8").splitlines()[0]
        lignes.append({"Table attendue (SI.)": nom, "Colonnes": ", ".join(entete.split(";")),
                       "Où la trouver en entreprise": OU_TROUVER.get(nom, "")})
    return pd.DataFrame(lignes)


def afficher() -> None:
    import streamlit as st

    st.markdown(
        "La chaîne SAS (`sas/`) est la version à installer. **Seule l'entrée change** : les données sources et "
        "les référentiels. Le cœur (contrôles, notes, registre, rapport, export Qlik) reste tel quel : il a été "
        "vérifié valeur par valeur (59 sur 59, page Vérification SAS).")

    st.markdown("#### :material/build: À changer une fois pour toutes")
    for num, fichier, quoi, qui in UNE_FOIS:
        with st.container(border=True):
            st.markdown(f"**{num}. {fichier}** — {quoi}  \n:gray[Qui vous aide : {qui}]")

    st.markdown("#### :material/table_chart: Les tables que la chaîne attend")
    st.markdown("Pour chacune, une vue dans `01_sources.sas` qui donne **ces noms de colonnes** à leurs données. "
                "Exemple pour les sinistres :")
    st.code("proc sql;\n"
            "  create view SI.gestion_sinistres as\n"
            "  select DATE_ARRETE as arrete, NUM_SINISTRE as sinistre_id, NUM_CONTRAT as contrat_id,\n"
            "         SEGMENT_S2 as segment, DT_SURV as date_survenance, DT_DECL as date_declaration,\n"
            "         MT_REGL_CUMUL as reglements_cumules, MT_PROV_DD as provision_dossier\n"
            "  from SINISTRES.TABLE_GESTION;   /* noms de droite : à remplacer par les leurs */\n"
            "quit;", language="sql")
    st.dataframe(tables_attendues(), hide_index=True, width="stretch")
    st.caption("Liste lue dans `sas/01_import_demo.sas` : elle suit le code. Dates au format SAS, montants en "
               "euros, `segment` avec les mêmes valeurs que le référentiel des contrôles.")

    g, d = st.columns(2)
    with g:
        st.markdown("#### :material/flag: Démarrer, dans l'ordre")
        st.markdown("\n".join(f"{i}. {t}" for i, t in enumerate(DEMARRAGE, 1)))
    with d:
        st.markdown("#### :material/event_repeat: Chaque trimestre")
        st.markdown("\n".join(f"{i}. {t}" for i, t in enumerate(CHAQUE_TRIMESTRE, 1)))

    st.markdown("#### :material/block: À éviter (technique)")
    st.markdown("\n".join(f"- {t}" for t in A_NE_PAS_FAIRE))
