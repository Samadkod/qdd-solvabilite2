"""Onglet « Guide terre à terre » de l'application Streamlit.

Explique le dispositif sans jargon, pour une prise de poste. Tous les chiffres cités
viennent de la campagne sélectionnée (aucune valeur recopiée à la main) : si un calcul
ou une donnée change, le texte suit. Les dates du calendrier sont calculées à partir
de la date de prise de poste saisie.

Le dépôt est public : aucun nom d'employeur, aucune information personnelle.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from explications import ETAPES_EN_CLAIR, afficher_d_ou_sortent

DATE_PRISE_DE_POSTE = dt.date(2026, 11, 6)  # valeur par défaut, modifiable dans l'onglet


# missions de l'offre (reformulées) -> en clair, où les voir dans l'application, premier geste
MISSIONS = [
    ("Qualité & gouvernance", "Piloter le dispositif QDD et coordonner la résolution des anomalies",
     "Savoir à tout moment quelles données sont fiables, et faire corriger les autres par les bons services",
     "Synthèse · Anomalies (registre) · Lignes en anomalie",
     "Tenir un registre où chaque anomalie a un propriétaire et une échéance"),
    ("Qualité & gouvernance", "Produire et maintenir dictionnaire, cartographie et lignage des flux, contrôles, reporting qualité",
     "Les « cartes d'identité » des données, le plan des tuyaux entre les outils, la liste des vérifications",
     "Lignage & dictionnaire · Règles de contrôle · dossier referentiels/",
     "Partir de l'existant et le mettre au format des référentiels du projet"),
    ("Qualité & gouvernance", "Concevoir, développer et automatiser les traitements de fiabilisation (SAS avancé, SQL)",
     "Écrire des programmes qui vérifient les données tout seuls, à chaque arrêté",
     "Documentation → Code SAS / SQL (02_controles.sas, sql/controles/)",
     "Automatiser un premier contrôle aujourd'hui fait à la main"),
    ("Qualité & gouvernance", "Sensibiliser les métiers et accompagner leurs contributions",
     "Expliquer aux gestionnaires, comptables, actuaires pourquoi leurs données comptent et quoi corriger",
     "Documentation → ce guide, D'où sortent les chiffres, Atelier (fiches)",
     "Préparer une présentation de 15 minutes « la QDD en clair »"),
    ("Qualité & gouvernance", "Tenir le corpus documentaire et contribuer aux audits (ACPR, commissaires aux comptes)",
     "Pouvoir prouver, documents à l'appui, comment chaque chiffre a été obtenu et contrôlé",
     "Chargement & exécution (journal) · rapport Excel",
     "Lister les documents existants et leur date de dernière mise à jour"),
    ("Qualité & gouvernance", "Intégrer la QDD dans les projets de transformation et les groupes de travail IT",
     "Quand un outil change, vérifier que les données restent justes avant, pendant et après",
     "Lignage & dictionnaire (quels flux un projet touche)",
     "Demander la liste des projets IT en cours qui touchent des données critiques"),
    ("Optimisation & automatisation", "Analyser les processus et proposer des améliorations",
     "Repérer ce qui est lent, manuel ou fragile, et proposer mieux",
     "Synthèse (étapes sans contrôle) · Chargement & exécution (durées)",
     "Chronométrer une clôture : où part le temps ?"),
    ("Optimisation & automatisation", "Déployer les bonnes pratiques de développement et de documentation",
     "Code lisible, commenté, versionné, testé, rejouable par un collègue",
     "Ce dépôt lui-même (tests, CLAUDE.md, README)",
     "Proposer une convention simple : nommage, en-tête de programme, journal"),
    ("Optimisation & automatisation", "Appui expert SAS, SQL, Qlik Sense",
     "Être la personne qu'on vient voir quand un programme ou un tableau de bord coince",
     "Documentation → Code SAS / SQL · app/chargement_qdd.qvs",
     "Se former à Qlik Sense en s'appuyant sur Power BI (sous-onglet « Se former »)"),
    ("Travaux actuariels", "Provisions techniques, Solvabilité 2, ORSA, tarification, sinistralité grave, réassurance, sensibilités",
     "Fournir aux actuaires des données fiables et participer à leurs analyses",
     "Note & données (sensibilités du SCR) · sous-onglet « L'assurance en clair »",
     "Assister à une revue de provisions et noter quelles données y entrent"),
]

GLOSSAIRE = [
    ("Solvabilité 2", "La réglementation européenne des assureurs (depuis 2016). Elle oblige à prouver qu'on a assez de capital, à bien gérer ses risques et à rendre des comptes au régulateur."),
    ("ACPR", "Le gendarme français de l'assurance et de la banque. C'est lui qui reçoit les états réglementaires et qui contrôle."),
    ("Commissaires aux comptes (CAC)", "Les auditeurs externes qui certifient les comptes. Ils peuvent demander comment une donnée a été produite et contrôlée."),
    ("SCR", "Le capital minimum exigé. Il doit permettre de survivre à une très mauvaise année, du genre qui n'arrive qu'une fois tous les 200 ans."),
    ("MCR", "Un deuxième plancher de capital, plus bas que le SCR. En dessous, le régulateur peut retirer l'agrément."),
    ("Provisions techniques / Best Estimate (BE)", "L'argent mis de côté pour payer les sinistres déjà arrivés ou à venir. Le Best Estimate est la meilleure estimation de ce qu'on paiera réellement."),
    ("ORSA", "L'évaluation interne des risques et de la solvabilité : l'assureur projette lui-même sa situation sur plusieurs années, au moins une fois par an."),
    ("QRT", "Les tableaux officiels envoyés au régulateur, chaque trimestre et chaque année (S.02.01 = bilan, S.05.01 = primes et sinistres, S.06.02 = liste des placements, S.17.01 = provisions non-vie, S.19.01 = triangles de sinistres)."),
    ("SFCR / RSR", "Les rapports écrits de Solvabilité 2 : le SFCR est public, le RSR est réservé au régulateur."),
    ("Fonction actuarielle", "L'équipe d'actuaires qui donne son avis sur les provisions, y compris sur la qualité des données utilisées. Elle écrit un rapport au moins une fois par an."),
    ("QDD", "Qualité des données. Vérifier que les données sont complètes (rien ne manque), exactes (pas d'erreur) et pertinentes (adaptées à l'usage)."),
    ("Donnée critique", "Une donnée dont une erreur ferait bouger le SCR de façon notable. Ce sont celles qu'on surveille en priorité."),
    ("Sensibilité", "De combien le SCR bouge quand la donnée bouge. Forte sensibilité = donnée à surveiller de très près."),
    ("Seuil de significativité", "L'erreur maximale acceptée sur le SCR, toutes données confondues. Au-delà, l'erreur est jugée grave."),
    ("Tolérance / note minimum", "L'erreur acceptée sur une donnée. Plus la donnée pèse lourd, plus la tolérance est petite et plus la note minimum est haute."),
    ("Contrôle", "Une vérification automatique ou manuelle : « y a-t-il des doublons ? », « la gestion et la comptabilité donnent-elles le même total ? »…"),
    ("Contrôle de niveau 1 / niveau 2", "Niveau 1 : fait par les équipes qui produisent la donnée. Niveau 2 : fait par une équipe indépendante (risques, conformité, QDD)."),
    ("Rapprochement", "Comparer le même chiffre dans deux ou trois outils différents. S'ils ne sont pas égaux, au moins un des deux est faux."),
    ("Antériorité", "Le nombre de périodes écoulées depuis la dernière fois que le contrôle a été fait. 0 = fait à temps."),
    ("Dégradation", "La pénalité appliquée à un contrôle trop ancien. Un contrôle vieux de 6 mois ne garantit plus grand-chose."),
    ("Lignage", "Le trajet d'une donnée, de sa saisie jusqu'au calcul du SCR, en passant par chaque outil."),
    ("Flux", "Un passage de la donnée d'un outil à un autre (exemple : le chargement nocturne de l'outil de gestion vers l'entrepôt)."),
    ("Zone de risque", "Un flux où la donnée peut s'abîmer : ressaisie manuelle, chargement automatique, transformation…"),
    ("Propriétaire de données", "La direction responsable d'une donnée. C'est elle qui doit corriger les erreurs, pas l'équipe QDD."),
    ("Dictionnaire des données", "La carte d'identité de chaque donnée : définition, règle de calcul, format, propriétaire, états où elle apparaît."),
    ("Catalogue / MDM", "Le catalogue recense toutes les données disponibles. Le MDM (gestion des données de référence) garantit qu'une même donnée de référence (un client, un code activité) a une seule version officielle."),
    ("Registre des anomalies", "Le carnet de bord des problèmes détectés : qui doit corriger, pour quand, et où on en est."),
    ("Piste d'audit", "La trace de tout ce qui a été lancé, pour pouvoir prouver comment un chiffre a été obtenu."),
    ("SAS / PROC SQL", "Le logiciel de traitement de données utilisé en actuariat. PROC SQL permet d'y écrire des requêtes SQL."),
    ("ODBC", "Le « tuyau » standard qui permet à SAS ou à Qlik de lire directement les bases de données de l'entreprise."),
    ("Qlik Sense", "L'outil de tableaux de bord : il affiche les résultats de façon visuelle pour les responsables."),
    ("ISIN / CIC", "ISIN : le numéro d'identité d'un titre financier. CIC : le code qui dit de quel type d'actif il s'agit (action, obligation…)."),
]

POWERBI_QLIK = [
    ("Power Query (préparer les données)", "Le script de chargement (instructions LOAD … FROM …)",
     "Dans Qlik, la préparation s'écrit en script. Exemple dans le projet : app/chargement_qdd.qvs"),
    ("Modèle : relations tracées à la main", "Associations automatiques : deux tables sont liées si elles ont un champ de même nom",
     "D'où la règle du projet : seules les clés gardent leur nom, les autres champs sont préfixés (cp_, dd_…)"),
    ("Relation ambiguë", "Clé synthétique ou référence circulaire",
     "Deux tables qui partagent plusieurs champs créent une clé synthétique : à éviter"),
    ("Mesure DAX : SUM, CALCULATE", "Expression : Sum(…), et l'analyse d'ensembles Sum({<champ={valeur}>} …)",
     "L'analyse d'ensembles joue le rôle des filtres de CALCULATE"),
    ("Segment (slicer) et filtres", "Sélections : vert = sélectionné, blanc = possible, gris = exclu",
     "Cliquer n'importe où filtre toute l'application"),
    ("Page de rapport", "Feuille (sheet)", "Une application Qlik contient plusieurs feuilles"),
    ("Actualisation du jeu de données", "Rechargement (reload) de l'application", "Planifiable, comme une actualisation programmée"),
]

SAS_DATA = """/* 1. Une bibliothèque = un dossier (ou une base, via ODBC en entreprise).
      Celle-ci est déjà déclarée par sas/00_config.sas : */
libname SI "&RACINE./sas/lib_si";

/* 2. Étape DATA : lire, filtrer, créer des colonnes */
data contrats_rc;
  set SI.gestion_contrats;
  where segment = "RC_DECENNALE";
  taux_acquisition = prime_acquise / prime_emise;
run;"""

SAS_SQL = """/* 3. PROC SQL : le SQL que vous connaissez, dans SAS */
proc sql;
  create table doublons as
  select arrete, contrat_id, count(*) as nb
  from SI.gestion_contrats
  group by arrete, contrat_id
  having count(*) > 1;
quit;"""

SAS_MACRO = """/* 4. Macro : écrire un contrôle une fois, le rejouer partout */
%macro compter_doublons(table=, cle=);
  proc sql noprint;
    select count(*) into :nb_doublons trimmed
    from (select &cle from &table group by &cle having count(*) > 1);
  quit;
  %put NOTE: &nb_doublons valeur(s) de &cle en double dans &table..;
%mend;

%compter_doublons(table=SI.gestion_contrats, cle=%str(arrete, contrat_id));
%compter_doublons(table=SI.gestion_sinistres, cle=%str(arrete, sinistre_id));"""


def _p(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:.{d}f} %".replace(".", ",")


def _pt(x):
    return f"{x * 100:+.2f} point".replace(".", ",")


def _j(d: dt.date) -> str:
    return f"{d:%d/%m/%Y}"


def afficher_guide(c: dict, var: pd.DataFrame | None) -> None:
    """c : campagne affichée (choisie dans le menu) ; var : variation N-1 -> N (ou None)."""
    st.markdown(
        "Ce guide explique **sans jargon** ce que fait l'application, ce que disent les chiffres "
        f"de la campagne **{c['campagne']}** (arrêté du {pd.Timestamp(c['date']):%d/%m/%Y}), ce qu'attend le "
        "poste et comment s'y préparer. Il est écrit pour quelqu'un qui vient de la **data** plutôt que de "
        "l'actuariat. Les chiffres sont recalculés en direct : ils changent si vous modifiez les paramètres "
        "dans le menu (*Paramètres de la méthode*).")
    s = st.tabs(["L'essentiel", "🔎 D'où sortent les chiffres", "Les chiffres", "Le poste", "L'assurance en clair",
                 "Se former", "Calendrier", "Glossaire"])
    with s[0]:
        _essentiel(c)
    with s[1]:
        afficher_d_ou_sortent(c)
    with s[2]:
        _chiffres(c, var)
    with s[3]:
        _poste()
    with s[4]:
        _assurance(c)
    with s[5]:
        _se_former()
    with s[6]:
        _calendrier()
    with s[7]:
        _glossaire()


# ====================================================================== L'essentiel
def _essentiel(c: dict) -> None:
    st.header("Le problème, en 30 secondes")
    st.markdown(
        "- Un assureur doit prouver chaque trimestre et chaque année qu'il a **assez d'argent de côté** "
        "pour payer les sinistres, même après une très mauvaise année. Ce montant exigé s'appelle le **SCR**.\n"
        "- Le SCR est calculé à partir de **données** : primes, provisions pour sinistres, placements, réassurance…\n"
        "- **Si les données sont fausses, le SCR est faux.** L'assureur peut alors se croire solide sans l'être, "
        "ou immobiliser trop de capital. Le régulateur (l'ACPR) le sait et demande des preuves.\n"
        "- **Le métier QDD** consiste à vérifier ces données, à mesurer leur fiabilité par une note, "
        "à faire corriger les erreurs par les bons services, et à **automatiser** tout cela pour que ce soit "
        "rapide, répétable et traçable.")
    scr = f"{c['scr']:.1f}".replace(".", ",")
    st.info(f"Dans l'application, l'assureur est **fictif** (spécialisé BTP) et son SCR simplifié vaut "
            f"**{scr} M€**.", icon="🏗️")

    st.header("L'image à garder en tête : le contrôle technique")
    st.markdown(
        "| Contrôle technique d'une voiture | Qualité des données |\n"
        "|---|---|\n"
        "| Les pièces de la voiture (freins, pneus, phares) | Les **données** (provisions, primes, placements…) |\n"
        "| Les freins comptent plus que l'autoradio | Les données qui pèsent lourd dans le SCR comptent plus (**sensibilité**) |\n"
        "| Les tests du contrôleur | Les **contrôles** (doublons, rapprochements, cohérence…) |\n"
        "| Le résultat de chaque test | Le **résultat** du contrôle, de 0 à 100 % |\n"
        "| Un test fait il y a 2 ans ne prouve plus rien | Un contrôle ancien est **pénalisé** (dégradation) |\n"
        "| « Favorable » ou « contre-visite » | **Vert / orange / rouge** par donnée |\n"
        "| Le carnet d'entretien | Le **registre des anomalies** et le **journal** |")

    st.header("Une campagne, étape par étape")
    st.markdown(
        "Une **campagne**, c'est le contrôle complet à une date d'arrêté (fin de trimestre). "
        "Voici ce qui se passe, et le programme SAS qui le fait (*Documentation → Code SAS / SQL*) :\n\n"
        "| # | Ce qu'on fait | En clair | Programme |\n"
        "|---|---|---|---|\n"
        "| 1 | Paramétrer et se connecter | Date d'arrêté, seuils, accès aux bases (ODBC en production) | `00_config.sas` |\n"
        "| 2 | Récupérer les données | Ici, les fichiers fictifs ; en entreprise, les bases de gestion, comptabilité, actuariat | `01_import_demo.sas` |\n"
        "| 3 | Lancer les contrôles | Les 20 contrôles tournent tout seuls | `02_controles.sas` |\n"
        "| 4 | Calculer les notes | Note par donnée, note globale, comparaison aux minimums, explication de la variation | `03_campagne.sas`, `04_variation.sas` |\n"
        "| 5 | Ouvrir ou fermer les anomalies | Nouveau problème : on l'ouvre. Problème corrigé et recontrôlé : on le ferme | `06_gouvernance.sas` |\n"
        "| 6 | Publier | Rapport, tableau de bord Qlik, journal d'exécution | `05_rapport.sas`, `07_export_qlik.sas` |\n"
        "| 7 | Faire agir | Envoyer à chaque propriétaire ses anomalies, suivre les échéances, présenter en comité | *humain* |\n")
    st.caption("Les étapes 1 à 6 sont faites pour tourner sans intervention, à chaque arrêté : c'est là que se "
               "joue l'automatisation. L'étape 7 reste humaine : c'est là que se joue le rôle de pilote.")

    st.header("Lire la Synthèse en 1 minute")
    st.markdown(
        "1. **Bloc « le chargement et l'exploitation » d'abord** : si une table est en alerte de volume ou un contrôle "
        "en échec technique, les résultats sont à prendre avec prudence tant que ce n'est pas expliqué.\n"
        "2. **La note et l'objectif** : au-dessus de l'objectif, c'est bien, mais ce n'est pas suffisant.\n"
        "3. **« Données critiques hors tolérance »** : tout ce qui n'est pas 0 doit être expliqué ; ↗ ouvre la liste.\n"
        "4. **Sous chaque chiffre, l'évolution depuis N-1** : en rouge si ça se dégrade, en vert si ça s'améliore.\n"
        "5. **« Contrôles en rouge » et « en retard »** : ↗ ouvre la liste, ou le panneau Actions mène à la page "
        "Contrôles déjà filtrée.\n"
        "6. **Les anomalies** : chaque anomalie a-t-elle un propriétaire et une échéance ? Le Top 5 des messages dit "
        "par où commencer.\n"
        "7. **Exportez** le registre ou le rapport Excel pour le partager ou le présenter.")


# ====================================================================== Les chiffres
def _chiffres(c: dict, var: pd.DataFrame | None) -> None:
    I, g = c["ind"], c["gouv"]
    donnees = c["donnees"]
    critiques = donnees[donnees["critique"]].sort_values("sensibilite", ascending=False)
    ctrl = c["controles"]

    st.header("Ce que disent les chiffres de cette campagne")
    ok = I["note"] >= I["note_min"]
    st.markdown(
        f"**La note globale est de {_p(I['note'])} pour un objectif de {_p(I['note_min'])}** : "
        + ("l'objectif est **atteint**" if ok else "l'objectif **n'est pas atteint**")
        + f", avec un écart de {_pt(I['ecart_objectif'])}.")
    if ok and I["nb_donnees_hors_tolerance"]:
        st.warning(
            f"Attention : la note globale passe, mais **{I['nb_donnees_hors_tolerance']} donnée(s) critique(s) "
            f"sur {I['nb_donnees_critiques']}** n'atteignent pas leur propre minimum. Une moyenne correcte "
            "peut cacher un vrai problème : il faut toujours regarder le détail.", icon="⚠️")

    st.subheader("Les données qui posent problème")
    a_traiter = critiques[critiques["statut"] != "vert"]
    if a_traiter.empty:
        st.success("Toutes les données critiques atteignent leur note minimum.")
    for _, d in a_traiter.iterrows():
        pire = ctrl[(ctrl["donnee_id"] == d["donnee_id"]) & ctrl["statut"].isin(["rouge", "orange"]) & ctrl["inclus_note"]]
        causes = " ; ".join(
            f"« {r.libelle} » ({_p(r.resultat)} pour un seuil de {_p(r.seuil)}"
            + (", contrôle en retard" if r.anteriorite > 0 else "") + ")"
            for r in pire.itertuples())
        icone = "🔴" if d["statut"] == "rouge" else "🟠"
        st.markdown(
            f"{icone} **{d['libelle']}** — propriétaire : {d['proprietaire']}\n"
            f"- Elle pèse **{_p(d['sensibilite'], 1)}** dans le SCR, donc on exige au moins "
            f"**{_p(d['note_min'])}**. Elle obtient **{_p(d['note'])}**.\n"
            + (f"- Contrôles en cause : {causes}.\n" if causes else ""))
    leger = critiques.sort_values("sensibilite").iloc[0]
    lourd = critiques.iloc[0]
    tol = (1 - lourd["note_min"]) * lourd["sensibilite"]  # erreur tolérée sur le SCR pour une donnée
    st.caption(
        f"Pourquoi exiger plus de certaines données ? « {lourd['libelle']} » pèse {_p(lourd['sensibilite'], 1)} "
        f"du SCR : on lui demande {_p(lourd['note_min'])}. « {leger['libelle']} » ne pèse que "
        f"{_p(leger['sensibilite'], 1)} : {_p(leger['note_min'])} suffit. Règle : note minimum = "
        f"100 % − (erreur tolérée sur le SCR pour une donnée, soit {_p(tol)}, ÷ sensibilité).")

    st.subheader("Les tableaux envoyés au régulateur (QRT)")
    qrt = ctrl[~ctrl["inclus_note"]]
    ko = qrt[qrt["statut"] != "vert"]
    st.markdown(
        f"**{len(qrt) - len(ko)} vérification(s) conforme(s) sur {len(qrt)}.** Ces vérifications comparent "
        "les chiffres des états officiels aux outils internes. Elles sont jugées en oui / non et ne comptent "
        "pas dans la note, pour qu'un bon résultat ici ne masque pas un problème sur une donnée.")
    for r in ko.itertuples():
        st.markdown(f"- ❌ « {r.libelle} » ({r.maille}) : {_p(r.resultat)} de concordance pour {_p(r.seuil)} exigé.")

    st.subheader("Les problèmes en cours (anomalies)")
    reg = c["registre"]
    ouv = reg[reg["statut"] != "Clôturée"]
    st.markdown(
        f"**{g['nb_anomalies_ouvertes']} anomalie(s) ouverte(s)**, dont **{g['nb_anomalies_haute']} grave(s)** "
        f"et **{g['nb_anomalies_en_retard']} dont l'échéance est dépassée**. "
        f"Anomalies réglées depuis la campagne précédente : {g['nb_anomalies_cloturees']}.")
    hautes = ouv[ouv["gravite"] == "Haute"]
    if not hautes.empty:
        st.markdown("Les plus graves, et qui doit agir :")
        for r in hautes.itertuples():
            st.markdown(f"- **{r.libelle}** → {r.proprietaire}, échéance {pd.Timestamp(r.echeance):%d/%m/%Y} "
                        f"({r.statut.lower()}).")

    st.subheader("Les trous dans la raquette (étapes à risque sans contrôle)")
    cv = c["couverture"]
    trous = cv[cv["zone_risque"] & cv["critique"] & ~cv["couvert"]].drop_duplicates("flux_id")
    st.markdown(
        f"**{_p(g['taux_couverture_zones_risque'], 0)} des étapes à risque sont contrôlées.** "
        "Les étapes suivantes ne sont vérifiées par aucun contrôle : une erreur pourrait y passer inaperçue.")
    for r in trous.itertuples():
        st.markdown(f"- **{r.flux_id}** : {r.traitement} ({r.systeme_source} → {r.systeme_cible})")

    if var is not None and c["campagne"] == var["etape"].iloc[-1].split()[-1]:
        st.subheader("Pourquoi la note a bougé depuis la campagne précédente")
        debut, fin = var["note"].iloc[0], var["note"].iloc[-1]
        st.markdown(f"La note passe de **{_p(debut)}** à **{_p(fin)}** ({_pt(fin - debut)}). Ce qui a joué :")
        for r in var[var["impact"].notna() & (var["impact"].abs() > 1e-6)].itertuples():
            st.markdown(f"- {ETAPES_EN_CLAIR.get(r.etape, r.etape)} : **{_pt(r.impact)}**")

    st.header("Les trois familles de contrôles, avec des exemples de la vraie vie")
    k1, k2, k3 = st.columns(3)
    with k1, st.container(border=True):
        st.markdown(
            "**Cohérence (C01 à C10)**  \nOn regarde **une seule base** et on cherche l'impossible.\n\n"
            "- Le même contrat saisi deux fois : ses primes sont comptées deux fois.\n"
            "- Un sinistre survenu **avant** le début du contrat : erreur de date, ou dossier à examiner.\n"
            "- Un placement sans code ISIN : on ne sait plus ce qu'on détient.")
    with k2, st.container(border=True):
        st.markdown(
            "**Rapprochement (R01 à R06)**  \nOn compare **le même chiffre dans deux outils**.\n\n"
            "- La gestion dit 10 M€ de primes, la comptabilité 9,8 M€ : qui a raison ?\n"
            "- Les provisions de l'outil de gestion, de l'entrepôt et de l'actuariat doivent être égales.\n"
            "- Les placements du dépositaire doivent correspondre à la comptabilité.")
    with k3, st.container(border=True):
        st.markdown(
            "**Restitution QRT (Q01 à Q04)**  \nOn vérifie **ce qui part chez le régulateur**.\n\n"
            "- Le total du bilan S.02.01 doit être égal à la somme de la liste des actifs S.06.02.\n"
            "- Les provisions déclarées en S.17.01 doivent être celles de l'outil de provisionnement.\n"
            "- Statut oui / non : le moindre écart est un problème.")


# ====================================================================== Le poste
def _poste() -> None:
    st.header("Les missions du poste, une par une")
    st.markdown("Pour chaque mission de l'offre : ce que cela veut dire concrètement, où la voir dans "
                "l'application, et un premier geste possible en arrivant.")
    st.dataframe(pd.DataFrame(MISSIONS, columns=["Bloc", "Mission", "En clair", "Dans l'application",
                                                 "Premier geste"]),
                 hide_index=True, width="stretch")

    st.header("Le rôle en trois verbes")
    r1, r2, r3 = st.columns(3)
    with r1, st.container(border=True):
        st.markdown("**Fiabiliser**\n\n- Savoir quelles données sont critiques, et pourquoi.\n"
                    "- Avoir un contrôle sur chaque étape à risque.\n"
                    "- Faire corriger les erreurs par leurs propriétaires, dans les délais.")
    with r2, st.container(border=True):
        st.markdown("**Automatiser**\n\n- Remplacer les copier-coller Excel par des programmes SAS rejoués à chaque arrêté.\n"
                    "- Écrire chaque contrôle une seule fois, en macro SAS ou en SQL.\n"
                    "- Produire automatiquement le registre, le journal et le tableau de bord.")
    with r3, st.container(border=True):
        st.markdown("**Optimiser**\n\n- Réduire le temps entre l'arrêté et les résultats.\n"
                    "- Réduire les ressaisies manuelles, principale source d'erreurs.\n"
                    "- Mesurer le temps gagné et le nombre d'anomalies évitées.")

    st.header("Les questions à poser dès l'arrivée")
    st.markdown(
        "- Existe-t-il une **politique de qualité des données** écrite ? Qui l'a validée, et quand a-t-elle été revue ?\n"
        "- Quelles données sont considérées comme **critiques** aujourd'hui, et comment ce choix a-t-il été fait ?\n"
        "- Quels **contrôles** existent déjà ? Lesquels sont automatiques, lesquels sont faits à la main ?\n"
        "- Où sont le **dictionnaire des données** et la **cartographie des flux** actuels, et de quand datent-ils ?\n"
        "- Qui est **propriétaire** de chaque grande famille de données ?\n"
        "- D'où viennent les données des **contrats apportés par les courtiers**, et qui les contrôle ?\n"
        "- Quel est le **calendrier** des remises trimestrielles et annuelles, et où sont les goulots d'étranglement ?\n"
        "- Qu'ont dit le dernier **rapport de la fonction actuarielle**, l'**audit interne**, les **commissaires "
        "aux comptes** et l'**ACPR** sur les données ?\n"
        "- Quels **projets informatiques** en cours touchent des données critiques ?\n"
        "- Quels outils sont disponibles : version de **SAS** (Enterprise Guide ?), accès **ODBC**, **Qlik Sense**, "
        "planificateur de tâches, outil de gestion de versions ?\n"
        "- Quelles sont les **attentes prioritaires** de mon responsable pour les 3 et 6 premiers mois ?")


# ====================================================================== L'assurance en clair
def _assurance(c: dict) -> None:
    st.header("L'assurance dommages, pour quelqu'un qui vient de la data")
    st.markdown(
        "**Le cycle d'un contrat, en 5 mots**\n\n"
        "1. **Prime émise** : ce que le client doit payer pour la période couverte par le contrat.\n"
        "2. **Prime acquise** : la part de cette prime qui correspond à la période déjà écoulée. Un contrat "
        "annuel signé le 1er juillet n'a « gagné » que la moitié de sa prime au 31 décembre.\n"
        "3. **Sinistre** : un dommage couvert. On retient trois dates : la **survenance** (le jour du dommage), "
        "la **déclaration** (le jour où l'assureur l'apprend), puis les **règlements** (les paiements).\n"
        "4. **Provision** : l'argent mis de côté pour ce qu'il reste à payer. Le gestionnaire estime chaque "
        "dossier (provision dossier) ; l'actuaire ajoute ce qui n'est pas encore connu, par exemple les sinistres "
        "déjà survenus mais pas encore déclarés.\n"
        "5. **Réassurance** : l'assureur s'assure lui-même auprès d'un réassureur et lui cède une part de ses "
        "risques (le **taux de cession**).")
    st.markdown(
        "**Le triangle, l'outil de base de l'actuaire**\n\n"
        "Un tableau où chaque ligne est une année de survenance et chaque colonne une année de développement. "
        "On y voit comment les paiements d'une année de sinistres s'étalent dans le temps, et on prolonge la "
        "tendance pour estimer ce qu'il reste à payer. C'est ce que contient l'état **S.19.01**. "
        "Une erreur de date de survenance range un sinistre dans la mauvaise ligne : c'est pour cela que la "
        "date de survenance est une donnée critique.")
    st.markdown(
        "**Pourquoi le BTP est particulier**\n\n"
        "- La **responsabilité décennale** couvre les constructeurs pendant **10 ans** après la réception des "
        "travaux. Des sinistres peuvent donc apparaître des années après la prime : les provisions sont "
        "importantes et longues à se dénouer.\n"
        "- La **dommages-ouvrage** permet au propriétaire d'être remboursé vite, avant de savoir qui est responsable.\n"
        "- Conséquence dans l'application : les provisions RC décennale pèsent "
        f"**{_p(c['donnees'].set_index('donnee_id')['sensibilite'].get('provisions_sinistres_RC_DECENNALE'), 1)}** "
        "du SCR fictif : c'est la donnée la plus surveillée.")
    st.markdown(
        "**Le courtage**\n\n"
        "Une partie des contrats peut être apportée par des **courtiers** (des intermédiaires). Leurs données "
        "arrivent alors de l'extérieur, dans leurs propres formats : ce sont des **données externes**, à "
        "contrôler à l'entrée comme les autres.")
    st.markdown(
        "**Solvabilité 2 en trois piliers**\n\n"
        "| Pilier | En clair | Exemples |\n|---|---|---|\n"
        "| 1. Chiffres | Combien de capital faut-il ? | Provisions (Best Estimate), SCR, MCR |\n"
        "| 2. Gouvernance | Comment l'assureur est-il piloté ? | ORSA, fonctions clés (actuarielle, risques, conformité, audit interne), **qualité des données** |\n"
        "| 3. Reporting | Que dit-on au régulateur et au public ? | QRT trimestriels et annuels, SFCR (public), RSR (régulateur) |\n")
    st.markdown(
        "**Les travaux actuariels cités dans l'offre, en une ligne chacun**\n\n"
        "- **Provisions techniques** : estimer ce qu'il reste à payer sur les sinistres.\n"
        "- **ORSA** : projeter la solvabilité sur plusieurs années, avec des scénarios défavorables.\n"
        "- **Tarification** : fixer le prix des contrats à partir de la sinistralité passée.\n"
        "- **Sinistralité grave** : suivre à part les très gros sinistres, qui faussent les moyennes.\n"
        "- **Réassurance** : choisir et vérifier ce qu'on cède au réassureur.\n"
        "- **Analyses de sensibilité** : mesurer de combien un résultat bouge quand une hypothèse bouge "
        "(c'est ce que fait l'application pour classer les données critiques).")
    st.caption("Dans tous ces travaux, l'équipe QDD fournit la même chose : des données dont on sait prouver "
               "qu'elles sont justes.")


# ====================================================================== Se former
def _se_former() -> None:
    st.header("SAS : de la base aux macros")
    st.markdown(
        "Ces exemples utilisent les vraies tables fictives du projet. Pour les essayer : créer un compte "
        "**SAS OnDemand for Academics** (gratuit pour apprendre), y déposer le projet et lancer "
        "`sas/99_executer.sas`, qui déclare la bibliothèque `SI` et y charge les tables.")
    st.code(SAS_DATA, language="sql")
    st.code(SAS_SQL, language="sql")
    st.code(SAS_MACRO, language="sql")
    st.markdown(
        "**Les réflexes à prendre**\n\n"
        "- **Lire le journal (log) après chaque exécution.** `ERROR` = arrêt, `WARNING` = à comprendre, "
        "`NOTE` = à lire : par exemple, une NOTE de conversion de type signale souvent un problème de données.\n"
        "- **Une macro par contrôle**, avec des paramètres : c'est ce qui permet d'automatiser. Modèle dans "
        "`sas/02_controles.sas`.\n"
        "- **Les dates sont des nombres** (jours depuis le 1er janvier 1960) : on les compare et on les "
        "soustrait directement. `INTCK('qtr', debut, fin)` compte les fins de trimestre entre deux dates.\n"
        "- **Ne jamais écrire un mot de passe dans un programme** : en entreprise, on passe par un DSN ODBC "
        "ou un `authdomain` (voir `sas/00_config.sas`).")

    st.header("De Power BI à Qlik Sense")
    st.markdown("Les deux outils font la même chose. Voici les équivalences pour transposer ce que vous savez déjà.")
    st.dataframe(pd.DataFrame(POWERBI_QLIK, columns=["Dans Power BI", "Dans Qlik Sense", "À savoir"]),
                 hide_index=True, width="stretch")
    st.caption("Pour pratiquer : le site de formation de Qlik propose des parcours en ligne ; vérifiez l'offre "
               "gratuite du moment.")

    st.header("SQL : ce que vous savez déjà sert directement")
    st.markdown(
        "Les 20 contrôles du projet sont écrits en SQL standard, sans fonctions exotiques "
        "(dossier `sql/controles/`, *Documentation → Code SAS / SQL*). Ils tournent tels quels dans PROC SQL. "
        "Un bon exercice : les lire dans l'ordre C01 → R06 → Q04 et, pour chacun, dire en une phrase "
        "quelle erreur il attrape.")


# ====================================================================== Calendrier
def _calendrier() -> None:
    st.header("Calendrier de préparation et de prise de poste")
    debut = st.date_input("Date de prise de poste", DATE_PRISE_DE_POSTE, format="DD/MM/YYYY")
    j = lambda n: debut + dt.timedelta(days=n)  # noqa: E731
    cloture = dt.date(debut.year, 12, 31)
    remise_trim, remise_ann = cloture + dt.timedelta(weeks=5), cloture + dt.timedelta(weeks=14)
    st.info(
        f"Le prochain arrêté annuel est le **{_j(cloture)}**. Les délais réglementaires de remise sont de "
        f"5 semaines pour les QRT trimestriels (vers le **{_j(remise_trim)}**) et de 14 semaines pour les QRT "
        f"annuels (vers le **{_j(remise_ann)}**). Le calendrier interne fixe des jalons plus tôt : à demander "
        "dès l'arrivée. Votre première clôture annuelle tombera donc pendant vos premiers mois : c'est le "
        "meilleur moment pour observer tout le circuit.", icon="📅")

    etapes = [
        (f"Avant le premier jour (du {_j(j(-19))} au {_j(j(-1))})", True, [
            "Semaine 1 — **Comprendre le métier** : les sous-onglets « L'essentiel » et « L'assurance en clair », "
            "le parcours « Comprendre la méthode pas à pas » de l'*Atelier (révision)*, puis les QCM.",
            "Semaine 2 — **SAS** : créer le compte SAS OnDemand, lancer `sas/99_executer.sas`, lire le journal, "
            "refaire les exemples du sous-onglet « Se former », puis écrire une macro de contrôle à soi.",
            "Semaine 3 — **Qlik Sense** à partir de Power BI (tableau d'équivalences), et relecture du glossaire "
            "jusqu'à pouvoir expliquer la note QDD à voix haute en 2 minutes.",
        ]),
        (f"Semaines 1 et 2 : écouter et cartographier (du {_j(debut)} au {_j(j(13))})", False, [
            "Rencontrer : actuariat, fonction actuarielle, gestion des risques, comptabilité, gestion des contrats "
            "et des sinistres, informatique, contrôle interne.",
            "Récupérer l'existant : politique QDD, données critiques, contrôles en place, dictionnaire, cartographie "
            "des flux, calendrier des remises, dernier rapport de la fonction actuarielle, remarques d'audit.",
            "Obtenir les accès : SAS, bases de données (ODBC), Qlik, dossiers partagés.",
            "Ne rien changer encore : comprendre comment les choses se font et pourquoi.",
        ]),
        (f"Semaines 3 à 6 : faire l'état des lieux (du {_j(j(14))} au {_j(j(41))})", False, [
            "Recenser les contrôles existants au format du référentiel du projet "
            "(`referentiels/referentiel_controles.csv`) : qui, quoi, quand, quel seuil.",
            "Dessiner le lignage des données critiques et repérer les étapes à risque sans contrôle.",
            "Repérer **un** contrôle manuel, long et répétitif, et l'automatiser en SAS : premier gain visible.",
        ]),
        (f"Semaines 7 à 12 : première campagne réelle (du {_j(j(42))} au {_j(j(83))})", False, [
            f"Observer la clôture du {_j(cloture)} et la préparation des remises : noter chaque étape manuelle "
            "et le temps qu'elle prend.",
            "Lancer une campagne sur un périmètre restreint (par exemple une seule ligne d'activité).",
            "Ouvrir le registre des anomalies, avec un propriétaire et une échéance pour chacune.",
            "Publier un premier tableau de bord Qlik.",
            "Présenter les résultats en comité, avec la justification de chaque paramètre (seuil, tolérance, "
            "pénalité de retard).",
        ]),
    ]
    for titre, ouvert, points in etapes:
        with st.expander(titre, expanded=ouvert):
            st.markdown("\n".join(f"- {p}" for p in points))
    st.markdown(
        f"**Vers le {_j(j(90))} (3 mois), on devrait pouvoir montrer :** une liste validée des données critiques, "
        "un inventaire des contrôles, un premier contrôle automatisé, une première note QDD sur un périmètre réel, "
        "et un registre des anomalies suivi.")
    st.caption("Proposition à adapter avec votre responsable : ses priorités passent avant ce plan.")


# ====================================================================== Glossaire
def _glossaire() -> None:
    st.header("Les mots du métier, en clair")
    st.dataframe(pd.DataFrame(GLOSSAIRE, columns=["Mot", "En clair"]), hide_index=True, width="stretch")

    st.header("Ce que cette application n'est pas")
    st.markdown(
        "- **Les données sont fictives.** Elles servent à apprendre et à montrer la méthode. "
        "Les vraies données de l'entreprise ne doivent **jamais** être mises dans ce dépôt public.\n"
        "- **Le SCR est simplifié** et ne remplace pas le calcul réglementaire.\n"
        "- **Le code SAS n'a pas encore été exécuté** : il a été écrit et relu, et il faut le faire tourner une "
        "première fois (`sas/99_executer.sas`) pour le valider.\n"
        "- **Les paramètres** (seuil, tolérance, pénalité de retard) sont des valeurs d'exemple : en entreprise, "
        "chacun devra être justifié et validé.")
