"""Entrée de la copie assurance. Déployer ce fichier depuis la branche design-assurance.

Les modules métier et l'entrée historique restent inchangés. Seuls l'habillage,
la synthèse et la position du sélecteur de campagne sont remplacés ici.
"""
from pathlib import Path


def lancer() -> None:
    original = Path(__file__).parent / "streamlit_app.py"
    source = original.read_text(encoding="utf-8")
    substitutions = [
        ("from style_app import appliquer_style, bandeau, entete_page",
         "from assurance_style import appliquer_style, bandeau, entete_page"),
        ("from synthese import afficher_synthese, tuiles",
         "from synthese import tuiles\nfrom assurance_synthese import afficher_synthese"),
        ('    en_doc = PAGES[st.session_state["page"]][0] in DOC',
         '    campagne_slot = st.container()\n    en_doc = PAGES[st.session_state["page"]][0] in DOC'),
        ('with st.sidebar:\n    choix = st.segmented_control("Campagne affichée", noms, default=noms[-1], key="campagne") or noms[-1]',
         'with campagne_slot:\n    choix = st.selectbox("Campagne affichée", noms, index=len(noms) - 1, key="campagne")'),
    ]
    for avant, apres in substitutions:
        if source.count(avant) != 1:
            raise RuntimeError("L'entrée originale a évolué : adaptation du point d'entrée assurance nécessaire.")
        source = source.replace(avant, apres, 1)
    contexte = {"__name__": "__main__", "__file__": str(original)}
    exec(compile(source, str(original), "exec"), contexte)


lancer()
