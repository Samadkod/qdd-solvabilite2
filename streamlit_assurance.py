"""Entrée de la copie assurance. Déployer ce fichier depuis la branche design-assurance.

Les modules métier et l'entrée historique restent inchangés. Seuls l'habillage,
la synthèse et la position du sélecteur de campagne sont remplacés ici ;
les extensions d'atelier utilisent des copies isolées, sans modifier la référence.
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
        ('from feuille_de_route import afficher_feuille_de_route',
         'from assurance_feuille import afficher_feuille_de_route\n'
         'from operations_qdd.ui import afficher_diagnostic, afficher_impact, afficher_resolution, afficher_dossier'),
        ('    "atelier": ("Se former", "Atelier (révision)", ":material/quiz:", "Fiches, QCM, vrai ou faux, simulateur, plan à 90 jours."),',
         '    "atelier": ("Se former", "Atelier QDD", ":material/quiz:", "Résolution fictive et atelier de révision conservé."),'),
        ('    "verif_sas": ("Exploitation", "Vérification SAS",',
         '    "resolution": ("Exploitation", "Atelier de résolution", ":material/build:", '
         '"Correction sur copie, recontrôle réel et validation déclarative sur données fictives."),\n'
         '    "dossier": ("Exploitation", "Dossier de campagne", ":material/folder:", '
         '"Preuves, résultats, règles et pièces manquantes de la campagne."),\n'
         '    "verif_sas": ("Exploitation", "Vérification SAS",'),
        ('    afficher_synthese(c, prev, xlsx, aller, lig, vol, exe, precedentes)',
         '    afficher_synthese(c, prev, xlsx, aller, lig, vol, exe, precedentes, base=base_fictive(), methode='
         '{"methode_ecart": ecart, "ponderation_montant": montant})'),
        ('def page_lignage() -> None:\n    st.subheader',
         'def page_lignage() -> None:\n    afficher_impact(c)\n    st.subheader'),
        ('def page_atelier() -> None:\n    html =',
         'def page_atelier() -> None:\n'
         '    mode = st.radio("Espace de travail", ["Résolution QDD", "Révision historique"], horizontal=True)\n'
         '    if mode == "Résolution QDD":\n'
         '        afficher_resolution(c, base_fictive(), {"methode_ecart": ecart, "ponderation_montant": montant})\n'
         '        return\n    html ='),
        ('    "synthese": page_synthese,',
         '    "resolution": lambda: afficher_resolution(c, base_fictive(), '
         '{"methode_ecart": ecart, "ponderation_montant": montant}),\n'
         '    "dossier": lambda: afficher_dossier(c, prev, *_contexte(c, prev), xlsx, base_fictive(), '
         '{"methode_ecart": ecart, "ponderation_montant": montant}),\n'
         '    "synthese": page_synthese,'),
    ]
    for avant, apres in substitutions:
        if source.count(avant) != 1:
            raise RuntimeError("L'entrée originale a évolué : adaptation du point d'entrée assurance nécessaire.")
        source = source.replace(avant, apres, 1)
    contexte = {"__name__": "__main__", "__file__": str(original)}
    exec(compile(source, str(original), "exec"), contexte)


lancer()
