"""Page « Visite de l'application » : chaque page en une ligne, à quoi elle sert et quand l'ouvrir."""
from __future__ import annotations

# clé de page -> (à quoi elle sert, quand l'ouvrir)
USAGES = {
    "synthese": ("La note de la campagne, les contrôles, les anomalies, le chargement : tout en tuiles, avec "
                 "l'évolution depuis la campagne précédente.", "En premier, à chaque campagne ; c'est l'écran à montrer."),
    "donnees": ("Chaque donnée critique : sa note, son minimum exigé, son statut ; pourquoi la note globale a "
                "bougé (cascade) ; la note par segment, étape, critère, responsable ; le gain de note de chaque correction avant de la faire.", "Pour expliquer un rouge ou "
                "une baisse de note."),
    "controles": ("La liste de suivi des points de contrôle : exécuté ou non, résultat, échéance, tendance, "
                  "durée ; clic sur une ligne pour voir ses lignes en anomalie.", "Pendant la campagne, pour "
                  "savoir ce qui reste à faire."),
    "anomalies": ("Le registre : chaque anomalie, sa gravité, son propriétaire, son échéance, son statut ; le "
                  "cycle de vie sur les campagnes.", "Pour relancer les propriétaires et suivre les corrections."),
    "relances": ("Pour chaque responsable : ses anomalies échues ou proches de l'échéance et ses contrôles à "
                 "refaire, avec le message prêt à copier ou télécharger.", "Chaque semaine de campagne, pour faire "
                 "agir les propriétaires."),
    "glossaire": ("Tous les mots du métier et de l'application, avec une recherche et un lien vers la page "
                  "où chaque mot sert.", "Dès qu'un mot n'est pas clair."),
    "acpr": ("Les faiblesses que l'ACPR relève le plus souvent (enquêtes 2022 et 2024, communiqué 2021), chaque "
             "constat sourcé et cité, face à ce que l'application couvre et à ce qui reste à faire.", "Avant un "
             "comité, un audit ou à la prise de poste, pour situer le dispositif."),
    "lignes": ("Les lignes fautives elles-mêmes (contrat, sinistre, titre), avec un message en clair, et leurs "
               "regroupements.", "Pour transmettre à un propriétaire exactement quoi corriger."),
    "regles": ("Le catalogue des 20 contrôles : ce que chacun vérifie, sa famille, son responsable.",
               "Pour présenter le dispositif ou ajouter un contrôle."),
    "lignage": ("Le trajet de chaque donnée (gestion, entrepôt, actuariat, SCR), les passages sans contrôle, le "
                "dictionnaire des données, le journal d'exécution.", "Pour un audit (ACPR, commissaires aux "
                "comptes) ou pour trouver un trou de contrôle."),
    "chargement": ("Les tables sont-elles arrivées, avec un volume normal ; chaque requête de contrôle a-t-elle "
                   "tourné.", "Avant de lire les résultats : une table vide fausse tout le reste."),
    "projet": ("Déclarer ce qu'un projet informatique touche (systèmes, flux) : données critiques, contrôles à "
               "rejouer, étapes sans contrôle, états QRT, niveau de risque par règles écrites, exigences de recette "
               "et fiche d'avis QDD en PDF.", "Quand un projet change un outil ou un flux (notice ACPR, point 18)."),
    "resolution": ("Proposer une correction sur une copie des données, relancer les 20 contrôles, faire valider "
                   "par une autre personne, exporter la preuve. La campagne de référence n'est jamais modifiée.",
                   "Pour montrer comment une anomalie se corrige et se prouve."),
    "dossier": ("Le dossier de comité en un clic (PDF : où en est-on, qui doit agir, points à arbitrer), puis le dossier de preuves de la campagne : résultats, règles, journal, pièces manquantes, à télécharger "
                "en un seul fichier.", "Pour préparer un audit ou une revue de clôture."),
    "verif_sas": ("Le résultat de la chaîne SAS comparé valeur par valeur au moteur Python.", "Pour prouver que "
                  "la version SAS calcule juste."),
    "assistant": ("Une question en langage courant sur la campagne ; l'assistant interroge le moteur en direct, "
                  "répond avec les vrais chiffres et cite la page où les vérifier.", "Pour aller vite, ou préparer "
                  "un message à un propriétaire de données."),
    "fiche_assistant": ("La présentation de l'assistant : ce qu'il fait et ne fait pas, ce qu'il lit, son modèle, son "
                        "budget, ses nouveautés.", "Avant de s'en servir, ou pour le présenter."),
    "feuille": ("Ce qui est prévu, ce qui reste à vérifier, ce qui a été fait.", "Pour suivre le projet."),
    "comprendre": ("Le calcul pas à pas sur une donnée au choix, avec les vrais chiffres.", "Quand un chiffre "
                   "n'est pas clair."),
    "guide": ("Le métier, les chiffres et le poste expliqués sans jargon ; les questions à poser en arrivant.",
              "Pour préparer la prise de poste."),
    "visite": ("Cette page.", "Pour s'y retrouver."),
    "sas": ("13 exercices SAS progressifs, avec indice, corrigé et résultat attendu.", "Pour s'entraîner sur "
            "SAS OnDemand."),
    "atelier": ("La résolution guidée et l'atelier de révision : fiches, QCM, vrai ou faux, simulateur, plan à "
                "90 jours.", "Pour s'entraîner et réviser la méthode."),
    "entreprise": ("Ce qu'il faut changer une fois, puis faire chaque trimestre, pour faire tourner la chaîne "
                   "SAS sur les vraies données.", "Au moment d'installer le dispositif en entreprise."),
    "code": ("Les programmes SAS de la version production et les 20 contrôles SQL.", "Pour lire ou réutiliser "
             "le code."),
}


def afficher(pages: dict, aller) -> None:
    """pages : le dictionnaire PAGES de l'application (rubrique, titre, icône, description)."""
    import streamlit as st

    st.markdown("Deux espaces : l'**atelier QDD** (piloter une campagne) et la **documentation** (comprendre, se "
                "former, installer). Les chiffres viennent tous du même moteur, sur des données 100 % fictives.")
    rubrique = None
    for cle, (rub, titre, icone, _) in pages.items():
        if rub != rubrique:
            st.markdown(f"#### {rub}")
            rubrique = rub
        sert, quand = USAGES.get(cle, ("", ""))
        with st.container(border=True):
            g, d = st.columns([5, 1])
            g.markdown(f"**{icone} {titre}** — {sert}  \n*Quand l'ouvrir* : {quand}")
            if cle != "visite" and d.button("Ouvrir", key=f"visite_{cle}", icon=":material/arrow_forward:"):
                aller(cle)
