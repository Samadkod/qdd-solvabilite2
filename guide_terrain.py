"""Onglet « Guide terre à terre » de l'application Streamlit.

Explique le dispositif sans jargon, pour une prise de poste. Tous les chiffres cités
viennent de la campagne sélectionnée (aucune valeur recopiée à la main) : si un calcul
ou une donnée change, le texte suit.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

# libellés des étapes de la variation (moteur) -> explication en clair
ETAPES_EN_CLAIR = {
    "Suppression de contrôles": "des contrôles ont été retirés du dispositif",
    "Sortie de données critiques": "des données ne sont plus jugées critiques",
    "QDD mesurée par les contrôles (antériorité intacte)": "les contrôles ont trouvé davantage d'erreurs dans les données",
    "Antériorité des contrôles": "des contrôles n'ont pas été refaits à temps (pénalité de retard)",
    "Coefficient de dégradation": "la pénalité de retard a été modifiée",
    "Pondération des contrôles": "le poids relatif des contrôles a changé",
    "Ajout de contrôles": "de nouveaux contrôles ont été ajoutés",
    "Sensibilités des données critiques": "le poids des données dans le SCR a changé",
    "Entrée de données critiques": "de nouvelles données sont devenues critiques",
}

GLOSSAIRE = [
    ("Solvabilité 2", "La réglementation européenne des assureurs (depuis 2016). Elle oblige à prouver qu'on a assez de capital, à bien gérer ses risques et à rendre des comptes au régulateur."),
    ("ACPR", "Le gendarme français de l'assurance et de la banque. C'est lui qui reçoit les états réglementaires et qui contrôle."),
    ("SCR", "Le capital minimum exigé. Il doit permettre de survivre à une très mauvaise année, du genre qui n'arrive qu'une fois tous les 200 ans."),
    ("Provisions techniques / Best Estimate (BE)", "L'argent mis de côté pour payer les sinistres déjà arrivés ou à venir. Le Best Estimate est la meilleure estimation de ce qu'on paiera réellement."),
    ("QRT", "Les tableaux officiels envoyés au régulateur, chaque trimestre et chaque année (S.02.01 = bilan, S.05.01 = primes et sinistres, S.06.02 = liste des placements, S.17.01 = provisions non-vie, S.19.01 = triangles de sinistres)."),
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
    ("Registre des anomalies", "Le carnet de bord des problèmes détectés : qui doit corriger, pour quand, et où on en est."),
    ("Piste d'audit", "La trace de tout ce qui a été lancé, pour pouvoir prouver comment un chiffre a été obtenu."),
    ("SAS / PROC SQL", "Le logiciel de traitement de données utilisé en actuariat. PROC SQL permet d'y écrire des requêtes SQL."),
    ("ODBC", "Le « tuyau » standard qui permet à SAS ou à Qlik de lire directement les bases de données de l'entreprise."),
    ("Qlik Sense", "L'outil de tableaux de bord : il affiche les résultats de façon visuelle pour les responsables."),
    ("ISIN / CIC", "ISIN : le numéro d'identité d'un titre financier. CIC : le code qui dit de quel type d'actif il s'agit (action, obligation…)."),
]


def _p(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:.{d}f} %".replace(".", ",")


def _pt(x):
    return f"{x * 100:+.2f} point".replace(".", ",")


def afficher_guide(c: dict, var: pd.DataFrame | None) -> None:
    """c : campagne sélectionnée dans « Campagne live » ; var : variation N-1 -> N (ou None)."""
    I, g = c["ind"], c["gouv"]
    date = pd.Timestamp(c["date"])
    donnees = c["donnees"]
    critiques = donnees[donnees["critique"]].sort_values("sensibilite", ascending=False)
    ctrl = c["controles"]

    st.markdown(
        "Cet onglet explique **sans jargon** ce que fait l'application, ce que disent les chiffres "
        f"de la campagne **{c['campagne']}** (arrêté du {date:%d/%m/%Y}) et comment s'en servir au quotidien. "
        "Les chiffres ci-dessous sont recalculés en direct : ils changent si vous modifiez les paramètres "
        "dans l'onglet *Campagne live*.")

    # ------------------------------------------------------------------ 1
    st.header("1. Le problème, en 30 secondes")
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

    # ------------------------------------------------------------------ 2
    st.header("2. L'image à garder en tête : le contrôle technique")
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

    # ------------------------------------------------------------------ 3
    st.header("3. Ce que disent les chiffres de cette campagne")
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

    # ------------------------------------------------------------------ 4
    st.header("4. Les trois familles de contrôles, avec des exemples de la vraie vie")
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

    # ------------------------------------------------------------------ 5
    st.header("5. Une campagne, étape par étape")
    st.markdown(
        "Une **campagne**, c'est le contrôle complet à une date d'arrêté (fin de trimestre). "
        "Voici ce qui se passe, et le programme SAS qui le fait (onglet *Code SAS / SQL*) :\n\n"
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
               "joue l'automatisation. L'étape 7 reste humaine : c'est là que se joue le rôle de cadre.")

    # ------------------------------------------------------------------ 6
    st.header("6. Comment lire l'onglet « Campagne live » en 1 minute")
    st.markdown(
        "1. **Regardez la note globale et l'objectif** (premier compteur). Au-dessus de l'objectif : bien, "
        "mais ce n'est pas suffisant.\n"
        "2. **Regardez « Données hors tolérance »**. Tout ce qui n'est pas 0 doit être expliqué.\n"
        "3. **Dans le tableau « Données »**, repérez les lignes rouges et orange, en commençant par celles "
        "qui ont la plus forte sensibilité.\n"
        "4. **Dans « Points de contrôle »**, filtrez sur « rouge » puis « en retard » pour voir les contrôles en cause.\n"
        "5. **Dans *Gouvernance***, vérifiez que chaque anomalie a un propriétaire et une échéance.\n"
        "6. **Téléchargez le rapport Excel** pour le partager ou le présenter.")

    # ------------------------------------------------------------------ 7
    st.header("7. Le rôle : fiabiliser, automatiser, optimiser")
    r1, r2, r3 = st.columns(3)
    with r1, st.container(border=True):
        st.markdown("**Fiabiliser**\n\n- Savoir quelles données sont critiques, et pourquoi.\n"
                    "- Avoir un contrôle sur chaque étape à risque.\n"
                    "- Faire corriger les erreurs par leurs propriétaires, dans les délais.")
    with r2, st.container(border=True):
        st.markdown("**Automatiser**\n\n- Remplacer les copier-coller Excel par des programmes SAS rejoués à chaque arrêté.\n"
                    "- Écrire chaque contrôle une seule fois, en SQL.\n"
                    "- Produire automatiquement le registre, le journal et le tableau de bord.")
    with r3, st.container(border=True):
        st.markdown("**Optimiser**\n\n- Réduire le temps entre l'arrêté et les résultats.\n"
                    "- Réduire les ressaisies manuelles, principale source d'erreurs.\n"
                    "- Mesurer le temps gagné et le nombre d'anomalies évitées.")

    # ------------------------------------------------------------------ 8
    st.header("8. Plan de prise de poste (proposition à adapter avec votre responsable)")
    with st.expander("Avant le premier jour", expanded=True):
        st.markdown(
            "- Relire cet onglet et le glossaire jusqu'à pouvoir expliquer la note QDD à voix haute en 2 minutes.\n"
            "- Faire le parcours « Comprendre la méthode pas à pas » et les QCM de l'onglet *Atelier*.\n"
            "- Se remettre à niveau en SAS / PROC SQL (SAS OnDemand for Academics est gratuit) et y faire tourner "
            "`sas/99_executer.sas` sur les données fictives.\n"
            "- Préparer la liste de questions de la section 9.")
    with st.expander("Semaines 1 et 2 : écouter et cartographier"):
        st.markdown(
            "- Rencontrer : actuariat, fonction actuarielle, gestion des risques, comptabilité, gestion des contrats "
            "et des sinistres, informatique (DSI), contrôle interne.\n"
            "- Récupérer l'existant : politique de qualité des données, liste des données critiques, contrôles déjà "
            "en place, calendrier des remises QRT, dernier rapport de la fonction actuarielle, remarques de l'ACPR "
            "ou de l'audit interne.\n"
            "- Obtenir les accès : SAS, bases de données (ODBC), Qlik, dossiers partagés.\n"
            "- Ne rien changer encore : comprendre comment les choses se font et pourquoi.")
    with st.expander("Semaines 3 à 6 : faire l'état des lieux"):
        st.markdown(
            "- Recenser les contrôles existants dans le format du référentiel de ce projet "
            "(`referentiels/referentiel_controles.csv`) : qui, quoi, quand, quel seuil.\n"
            "- Dessiner le lignage des données critiques et repérer les étapes à risque sans contrôle.\n"
            "- Repérer **un** contrôle manuel, long et répétitif, et l'automatiser en SAS : c'est le premier gain visible.")
    with st.expander("Semaines 7 à 12 : première campagne réelle"):
        st.markdown(
            "- Lancer une campagne sur un périmètre restreint (par exemple une seule ligne d'activité).\n"
            "- Ouvrir le registre des anomalies, avec un propriétaire et une échéance pour chacune.\n"
            "- Publier un premier tableau de bord Qlik.\n"
            "- Présenter les résultats en comité, avec la justification de chaque paramètre (seuil, tolérance, "
            "pénalité de retard).")
    st.markdown(
        "**À 3 mois, on devrait pouvoir montrer :** une liste validée des données critiques, un inventaire des "
        "contrôles, un premier contrôle automatisé, une première note QDD sur un périmètre réel, et un registre "
        "des anomalies suivi.")

    # ------------------------------------------------------------------ 9
    st.header("9. Les questions à poser dès l'arrivée")
    st.markdown(
        "- Existe-t-il une **politique de qualité des données** écrite ? Qui l'a validée, et quand a-t-elle été revue ?\n"
        "- Quelles données sont considérées comme **critiques** aujourd'hui, et comment ce choix a-t-il été fait ?\n"
        "- Quels **contrôles** existent déjà ? Lesquels sont automatiques, lesquels sont faits à la main ?\n"
        "- Qui est **propriétaire** de chaque grande famille de données ?\n"
        "- Quel est le **calendrier** des remises trimestrielles et annuelles, et où sont les goulots d'étranglement ?\n"
        "- Qu'ont dit le dernier **rapport de la fonction actuarielle**, l'**audit interne** et l'**ACPR** sur les données ?\n"
        "- Quels outils sont disponibles : version de **SAS**, accès **ODBC**, **Qlik Sense**, planificateur de tâches ?\n"
        "- Quelles sont les **attentes prioritaires** de mon responsable pour les 3 et 6 premiers mois ?")

    # ------------------------------------------------------------------ 10
    st.header("10. Les mots du métier, en clair")
    st.dataframe(pd.DataFrame(GLOSSAIRE, columns=["Mot", "En clair"]), hide_index=True, width="stretch")

    # ------------------------------------------------------------------ 11
    st.header("11. Ce que cette application n'est pas")
    st.markdown(
        "- **Les données sont fictives.** Elles servent à apprendre et à montrer la méthode. "
        "Les vraies données de l'entreprise ne doivent **jamais** être mises dans ce dépôt public.\n"
        "- **Le SCR est simplifié** et ne remplace pas le calcul réglementaire.\n"
        "- **Le code SAS n'a pas encore été exécuté** : il a été écrit et relu, et il faut le faire tourner une "
        "première fois (`sas/99_executer.sas`) pour le valider.\n"
        "- **Les paramètres** (seuil, tolérance, pénalité de retard) sont des valeurs d'exemple : en entreprise, "
        "chacun devra être justifié et validé.")
