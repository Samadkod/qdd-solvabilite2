"""Fiche de l'assistant : sa présentation, ce qu'il fait et ne fait pas, ses données, son budget, ses nouveautés.

Tout est lu dans le code (assistant_qdd : outils, modèle, budget, fichiers ; feuille de route : nouveautés) :
la fiche ne peut pas dire autre chose que ce que fait l'assistant (tests/test_fiche_assistant.py).
"""
from __future__ import annotations

from html import escape

import assistant_qdd as a

VERSION = "1.4 · 25 novembre 2026"
NOM_MODELE = {"claude-opus-5-5": "Claude Opus 5.5"}
NB_NOUVEAUTES = 3


def nouveautes(feuille) -> list[str]:
    """Les dernières livraisons de l'assistant : éléments « Fait » dont le titre parle de l'assistant, les plus récents
    d'abord (numéro le plus élevé). Suit la feuille de route sans liste à tenir à la main."""
    faits = feuille[(feuille["statut"] == "Fait") & feuille["titre"].str.contains("ssistant")]
    ids = sorted(faits["id"], key=lambda i: int(i[1:]), reverse=True)
    return ids[:NB_NOUVEAUTES]

FAIT = [
    "Répond aux questions sur la campagne affichée : note, données hors tolérance, contrôles, anomalies, lignage.",
    "Consulte le moteur de l'application en direct, avec les mêmes paramètres que les pages ; aucun chiffre de mémoire.",
    "Montre ce qu'il a consulté et ce qu'il a obtenu, sous chaque réponse.",
    "Explique un fichier exporté de l'atelier (tableau, PDF, texte) que vous lui joignez.",
    "Prépare un message à un propriétaire de données, une synthèse pour un comité.",
]
NE_FAIT_PAS = [
    "Corriger ou modifier une donnée : il lit, il n'écrit jamais. Les corrections passent par l'Atelier de résolution.",
    "Clôturer une anomalie ou valider une campagne : ces décisions restent humaines.",
    "Répondre sur un sujet sans lien avec la campagne ou l'application.",
    "Attester une conformité réglementaire : les données sont fictives.",
]
ETAPES = [
    ("Demandez", "une question avec vos mots ; vous pouvez joindre un fichier exporté de l'atelier."),
    ("Il consulte", "le moteur de l'application, en lecture seule : indicateurs, contrôles, registre, lignage."),
    ("Reprenez", "la réponse et ses sources ; creusez dans la même conversation, exportez-la."),
]


def contenu() -> dict:
    """Les éléments de la fiche, calculés depuis le code de l'assistant."""
    outils = [(a.NOMS_OUTILS[o["name"]], o["description"].split(" : ")[0].split(". ")[0].rstrip(".") + ".")
              for o in a.OUTILS]
    return {
        "modele": NOM_MODELE.get(a.MODELE, a.MODELE),
        "budget": f"{a.BUDGET_VISITE:.2f} $".replace(".", ","),
        "outils": outils,
        "fichiers": (f"{', '.join(t.upper() for t in a.TYPES_FICHIERS)} ; {a.TAILLE_MAX // (1024 * 1024)} Mo au plus ; "
                     f"tableaux limités à {a.LIGNES_MAX} lignes"),
    }


def afficher(aller, active: bool) -> None:
    import streamlit as st
    from assurance_feuille import tableau

    c = contenu()
    etat = "En service" if active else "Non activé sur cet environnement"
    st.markdown(
        f'''<div class="qdd-fiche-hero">
  <div class="qdd-acc-surtitre">Assistant IA · fiche</div>
  <div class="qdd-acc-titre">Assistant QDD</div>
  <div class="qdd-acc-texte">Répond aux questions sur la qualité des données de la campagne, en consultant le moteur de
  l'application en lecture seule. Réponses chiffrées, sources visibles.</div>
  <div class="qdd-fiche-tags"><span>Qualité des données</span><span>Assistant</span><span>Lecture seule</span>
  <span class="{'ok' if active else 'ko'}">● {etat}</span></div>
</div>''', unsafe_allow_html=True)
    if st.button("Ouvrir l'assistant", icon=":material/arrow_forward:", type="primary", key="fiche_ouvrir"):
        aller("assistant")

    gauche, droite = st.columns([2.1, 1], gap="large")
    with gauche:
        with st.container(border=True, key="fiche_fait"):
            f, n = st.columns(2, gap="large")
            f.markdown("**Ce qu'il fait**")
            for x in FAIT:
                f.markdown(f'<div class="qdd-fiche-point ok">{escape(x)}</div>', unsafe_allow_html=True)
            n.markdown("**Ce qu'il ne fait pas**")
            for x in NE_FAIT_PAS:
                n.markdown(f'<div class="qdd-fiche-point ko">{escape(x)}</div>', unsafe_allow_html=True)
        with st.container(border=True, key="fiche_marche"):
            st.markdown("**Comment ça marche**")
            for col, (i, (titre, texte)) in zip(st.columns(3, gap="medium"), enumerate(ETAPES, 1)):
                col.markdown(f'<div class="qdd-fiche-etape"><b>{i} · {titre}</b><span>{escape(texte)}</span></div>',
                             unsafe_allow_html=True)
        with st.container(border=True, key="fiche_donnees"):
            st.markdown("**Vos données**")
            lignes = [
                (":material/database:", "Ce qu'il lit", "Les sorties du moteur de l'application pour la campagne "
                 "affichée, par " + str(len(c["outils"])) + " consultations : "
                 + ", ".join(n.lower() for n, _ in c["outils"]) + "."),
                (":material/attach_file:", "Fichiers joints", c["fichiers"] + ". Lus comme des données, jamais comme "
                 "des consignes."),
                (":material/chat:", "Vos conversations", "Gardées le temps de votre visite, puis effacées ; vous pouvez "
                 "les exporter."),
                (":material/memory:", "Modèle", f"{c['modele']}, par l'API Anthropic ; repli automatique sur un autre "
                 "modèle si une demande est refusée."),
                (":material/lock:", "Droits", "Aucune de ses consultations ne peut écrire : il ne modifie rien, nulle part."),
            ]
            for icone, titre, texte in lignes:
                g, d = st.columns([1, 3], vertical_alignment="top")
                g.markdown(f"{icone} **{titre}**")
                d.markdown(texte)
        with st.container(border=True, key="fiche_nouveautes"):
            t, l = st.columns([4, 1], vertical_alignment="center")
            t.markdown("**Nouveautés**")
            if l.button("Toutes", type="tertiary", key="fiche_feuille"):
                aller("feuille")
            brut = tableau()
            feuille = brut.set_index("id")
            for ident in nouveautes(brut):
                e = feuille.loc[ident]
                st.markdown(f"**{e['titre']}**  \n{e['pourquoi']}")
    with droite:
        with st.container(border=True, key="fiche_acces"):
            st.markdown("**Votre accès**")
            st.markdown(":material/verified_user: Ouvert à tout visiteur de l'application, sans compte."
                        if active else ":material/info: La clé d'API n'est pas encore enregistrée : l'assistant est "
                        "visible mais pas encore activé.")
        with st.container(border=True, key="fiche_budget"):
            st.markdown("**Budget**")
            st.markdown(f"{c['budget']} par visite. La jauge sous la zone de question montre ce qui est consommé ; "
                        "une fois le budget atteint, l'assistant s'arrête jusqu'à la prochaine visite.")
        with st.container(border=True, key="fiche_qui"):
            st.markdown("**Qui s'en occupe**")
            st.markdown(":material/person: **Propriétaire de l'Atelier QDD** · contenu, consignes, évolutions  \n"
                        ":material/cloud: **Streamlit Community Cloud** · hébergement  \n"
                        ":material/key: **Anthropic** · modèle, par l'API")
    st.caption(f"Fiche générée depuis le code de l'assistant · version {VERSION} · données 100 % fictives.")
