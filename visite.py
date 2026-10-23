"""Page « Visite de l'application » : chaque page en une ligne, à quoi elle sert et quand l'ouvrir."""
from __future__ import annotations

# clé de page -> (à quoi elle sert, quand l'ouvrir)
USAGES = {
    "synthese": ("La note de la campagne, les contrôles, les anomalies, le chargement : tout en tuiles, avec "
                 "l'évolution depuis la campagne précédente.", "En premier, à chaque campagne ; c'est l'écran à montrer."),
    "donnees": ("Chaque donnée critique : sa note, son minimum exigé, son statut ; pourquoi la note globale a "
                "bougé (cascade) ; la note par segment, étape, critère, responsable.", "Pour expliquer un rouge ou "
                "une baisse de note."),
    "controles": ("La liste de suivi des points de contrôle : exécuté ou non, résultat, échéance, tendance, "
                  "durée ; clic sur une ligne pour voir ses lignes en anomalie.", "Pendant la campagne, pour "
                  "savoir ce qui reste à faire."),
    "anomalies": ("Le registre : chaque anomalie, sa gravité, son propriétaire, son échéance, son statut ; le "
                  "cycle de vie sur les campagnes.", "Pour relancer les propriétaires et suivre les corrections."),
    "lignes": ("Les lignes fautives elles-mêmes (contrat, sinistre, titre), avec un message en clair, et leurs "
               "regroupements.", "Pour transmettre à un propriétaire exactement quoi corriger."),
    "regles": ("Le catalogue des 20 contrôles : ce que chacun vérifie, sa famille, son responsable.",
               "Pour présenter le dispositif ou ajouter un contrôle."),
    "lignage": ("Le trajet de chaque donnée (gestion, entrepôt, actuariat, SCR), les passages sans contrôle, le "
                "dictionnaire des données, le journal d'exécution.", "Pour un audit (ACPR, commissaires aux "
                "comptes) ou pour trouver un trou de contrôle."),
    "chargement": ("Les tables sont-elles arrivées, avec un volume normal ; chaque requête de contrôle a-t-elle "
                   "tourné.", "Avant de lire les résultats : une table vide fausse tout le reste."),
    "verif_sas": ("Le résultat de la chaîne SAS comparé valeur par valeur au moteur Python.", "Pour prouver que "
                  "la version SAS calcule juste."),
    "feuille": ("Ce qui est prévu, ce qui reste à vérifier, ce qui a été fait.", "Pour suivre le projet."),
    "comprendre": ("Le calcul pas à pas sur une donnée au choix, avec les vrais chiffres.", "Quand un chiffre "
                   "n'est pas clair."),
    "guide": ("Le métier, les chiffres et le poste expliqués sans jargon ; les questions à poser en arrivant.",
              "Pour préparer la prise de poste."),
    "visite": ("Cette page.", "Pour s'y retrouver."),
    "sas": ("13 exercices SAS progressifs, avec indice, corrigé et résultat attendu.", "Pour s'entraîner sur "
            "SAS OnDemand."),
    "atelier": ("Fiches, QCM, vrai ou faux, simulateur des paramètres, plan à 90 jours.", "Pour réviser la "
                "méthode."),
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
