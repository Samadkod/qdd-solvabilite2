"""Fiche de l'Atelier de résolution : à quoi il sert, comment s'en servir pas à pas, pourquoi un scénario est bloqué.

Affichée en haut de la page Atelier de résolution. L'exemple pas à pas lit les vraies lignes en anomalie de la campagne
affichée (operations_qdd.correction.candidats) ; les motifs de blocage reprennent ceux du code (correction.rejouer).
"""
from __future__ import annotations

from operations_qdd.correction import ESSAIS_VALIDABLES, candidats

ETAPES = [
    ("Proposer", "Choisir la règle (C05 ou C02) et le segment ; dans le tableau, une nouvelle valeur et une pièce "
                 "justificative par ligne (ou un fichier CSV importé), votre nom, puis « Déclarer la correction »."),
    ("Recontrôler", "« Relancer les 20 contrôles sur la copie » : les 20 règles SQL tournent réellement sur une copie de "
                    "la base corrigée ; l'atelier compare chaque point avant et après."),
    ("Valider", "Une autre personne saisit son nom et valide. Le même nom que le correcteur est refusé (séparation des "
                "rôles, déclarative dans cette version)."),
    ("Exporter", "Télécharger la fiche d'ajustement (CSV) et le scénario avec ses preuves (JSON) : rien n'est conservé "
                 "après la visite."),
]
FAIT = [
    "Corrige sur une copie : la base de référence et le registre ne sont jamais modifiés.",
    "Rejoue réellement les 20 contrôles et montre l'effet sur chaque point et sur la note.",
    "Exige une validation par une autre personne et garde le journal de chaque action.",
    "Produit la fiche d'ajustement (données en défaut conservées, méthode, responsables) et la preuve.",
]
NE_FAIT_PAS = [
    "Corriger toutes les règles : seules C02 (prime acquise hors bornes) et C05 (provision négative) sont modifiables.",
    "Propager la correction vers les systèmes en aval ni clôturer une anomalie du registre.",
    "Vérifier l'identité : les noms sont déclaratifs, sans connexion des utilisateurs.",
    "Conserver le travail : la session se perd en quittant la page ; exportez avant.",
]
BLOCAGES = [
    ("La donnée n'est pas critique", "Elle n'a pas de seuil QDD : le scénario peut être recontrôlé, jamais validé."),
    ("Des lignes fautives restent sur la cible", "Toutes les lignes en anomalie du segment doivent être corrigées "
                                                 "dans la même déclaration (chacune avec sa propre valeur) : une "
                                                 "déclaration par ligne ne suffit pas, chaque scénario part de la "
                                                 "base d'origine."),
    ("Un autre contrôle de la même donnée reste sous son seuil", "La validation exige que la donnée corrigée soit "
                                                                 "conforme sur tous ses contrôles, pas seulement sur "
                                                                 "la règle corrigée : l'autre défaut est à traiter à part."),
    ("La correction crée ou aggrave une non-conformité", "Un point qui passe sous son seuil, ou qui était déjà sous son "
                                                          "seuil et se dégrade, bloque la validation."),
]


def _euros(x: float) -> str:
    return f"{x:,.2f} €".replace(",", " ").replace(".", ",")


def afficher(c: dict, base) -> None:
    import streamlit as st

    with st.container(border=True, key="fiche_atelier"):
        st.markdown("**Fiche de l'atelier** · tester une correction de donnée **sans toucher la base** : correction "
                    "sur une copie, recontrôle réel des 20 contrôles, validation par une autre personne, preuve "
                    "exportée. Les quatre étapes ci-dessous suivent la barre de progression.")
        for col, (i, (titre, texte)) in zip(st.columns(4, gap="small"), enumerate(ETAPES, 1)):
            col.markdown(f'<div class="qdd-fiche-etape"><b>{i} · {titre}</b><span>{texte}</span></div>',
                         unsafe_allow_html=True)
        with st.expander("Exemple pas à pas : remettre à zéro les provisions négatives (C05 · Flottes auto)",
                         icon=":material/school:"):
            essais = ESSAIS_VALIDABLES.get(c["campagne"])
            if essais == []:
                st.warning(f"Sur la campagne {c['campagne']}, aucun scénario ne peut aller jusqu'à la validation. "
                           "Choisissez la campagne **N** en haut du menu pour cet exemple.")
            try:
                df = candidats(base, c["date"], "C05", "AUTO_FLOTTE")
            except Exception:  # noqa: BLE001 — l'exemple reste lisible même sans la base
                df = None
            if df is not None and len(df):
                lignes = " ; ".join(f"{r.objet} ({_euros(r.ancienne)})" for r in df.itertuples())
                st.markdown(f"Sur la campagne {c['campagne']}, le contrôle C05 trouve **{len(df)} sinistre"
                            f"{'s' if len(df) > 1 else ''} à provision négative** en flottes auto : {lignes}.")
            st.markdown(
                "1. **Étape 1** : règle **C05 · Provision négative**, segment **Flottes auto**.\n"
                "2. **Étape 2** : dans le tableau, pour chaque sinistre, une **nouvelle valeur** (par exemple 500 € pour "
                "l'un, 0 € pour l'autre) et sa **pièce justificative** (par exemple « Rapport d'expert n° 2026-114 "
                "du 12/10/2026 », fictif ici) ; votre nom, une justification d'ensemble, cocher la confirmation, puis "
                "**Déclarer la correction**. Toutes les lignes sont corrigées dans la même déclaration. Beaucoup de "
                "lignes : téléchargez le modèle CSV, remplissez-le, importez-le.\n"
                "3. **Étape 3** : **Relancer les 20 contrôles sur la copie**. Attendu : C05 · Flottes auto passe à "
                "100 % (0 anomalie) et aucun blocage ; l'état devient « Recontrôle réussi · à valider ».\n"
                "4. **Étape 4** : saisir **un autre nom** que le correcteur, un commentaire, puis **Valider dans le bac "
                "à sable**. Enfin, exporter la fiche d'ajustement et le scénario.")
            st.caption("La « note avant » affichée est celle d'un recontrôle neuf des 20 règles, pas la note de la "
                       "campagne. Elle peut bouger très peu, dans un sens ou dans l'autre : remettre une provision "
                       "négative à zéro change aussi les totaux comparés par les rapprochements (R03).")
        g, d = st.columns(2)
        with g.expander("Ce qu'il fait / ne fait pas", icon=":material/checklist:"):
            st.markdown("**Il fait**\n" + "\n".join(f"- {x}" for x in FAIT))
            st.markdown("**Il ne fait pas**\n" + "\n".join(f"- {x}" for x in NE_FAIT_PAS))
        with d.expander("Pourquoi un scénario est bloqué", icon=":material/block:"):
            for titre, texte in BLOCAGES:
                st.markdown(f"**{titre}.** {texte}")
            st.caption("Un scénario bloqué ne se valide jamais : faire une nouvelle déclaration à l'étape 1.")
