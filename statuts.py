"""Libellés et pastilles de statut, communs à toute l'application.

Le moteur garde ses valeurs internes (vert / orange / rouge, identiques en Python, SAS, SQL, Excel) ;
l'application affiche un libellé qui dit quoi faire, et la couleur porte la gravité :
  - vert   : Conforme       — rien à faire ;
  - orange : À corriger     — non bloquant, correction à prévoir ;
  - rouge  : Bloquant       — correction obligatoire ;
  - gris   : Non noté / Non réalisé — pas encore traité, ou hors note.
"""
from __future__ import annotations

import pandas as pd

VERT, ORANGE, ROUGE, GRIS, BLEU = "#22744A", "#C98A10", "#AD3030", "#8A96A3", "#0E5A69"

LIBELLES = {"vert": "Conforme", "orange": "À corriger", "rouge": "Bloquant"}
NON_NOTE = "Non noté"
DEFINITIONS = {
    "Conforme": "Au-dessus du minimum exigé : rien à faire.",
    "À corriger": "Sous le minimum de moins de 2 points : non bloquant, correction à prévoir.",
    "Bloquant": "Sous le minimum de plus de 2 points : correction obligatoire.",
    NON_NOTE: "Donnée non critique ou contrôle sans seuil : suivi, mais hors note.",
}

# couleur de chaque libellé affiché, quelle que soit la page
COULEURS = {
    "Conforme": VERT, "À corriger": ORANGE, "Bloquant": ROUGE, NON_NOTE: GRIS,
    "Exécuté": VERT, "Saisi hors outil": BLEU, "Non réalisé": GRIS, "Échec technique": ROUGE,
    "Ouverte": ORANGE, "Récurrente": ROUGE, "Clôturée": VERT,
    "Haute": ROUGE, "Moyenne": ORANGE,
    "Normal": VERT, "À expliquer": ORANGE, "Sans référence": GRIS,
    "En retard": ROUGE, "À jour": VERT,
}
AIDE_COLONNES = {
    "Statut": "Conforme (vert) : rien à faire. À corriger (orange) : non bloquant, correction à prévoir. "
              "Bloquant (rouge) : correction obligatoire. Non noté (gris) : hors note.",
    "Exécution": "Exécuté : refait pour cet arrêté. Non réalisé : pas encore fait, l'ancien résultat est repris "
                 "avec une pénalité. Saisi hors outil : résultat repris de l'historique. Échec technique : la "
                 "requête ne tourne pas.",
    "Gravité": "Haute : correction obligatoire, échéance 30 jours. Moyenne : à corriger, échéance 60 jours.",
}


def libelle(statut) -> str:
    """vert / orange / rouge -> libellé ; vide -> Non noté ; un libellé déjà lisible est rendu tel quel."""
    if statut is None or (isinstance(statut, float) and pd.isna(statut)) or statut in ("", "—") \
            or str(statut).lower().startswith(("non noté", "non évalué")):
        return NON_NOTE
    return LIBELLES.get(statut, statut)


def _est_colonne_statut(s: pd.Series) -> bool:
    v = {libelle(x) for x in s.dropna().astype(str)} - {""}
    return bool(v) and v <= set(COULEURS)


def colonne_statut(serie: pd.Series) -> bool:
    """Colonne à afficher en pastilles : nommée « statut » (valeurs du moteur) ou ne contenant que des statuts connus."""
    if str(serie.name).lower().endswith("statut"):
        return True
    return _est_colonne_statut(serie)


def tableau(df: pd.DataFrame, formats: dict | None = None, column_config: dict | None = None, **kw):
    """st.dataframe avec des pastilles de couleur pour chaque colonne de statut.

    formats : {colonne: fonction} pour l'affichage des autres colonnes (pourcentages à la française, etc.).
    """
    import streamlit as st

    out = df.copy()
    config = dict(column_config or {})
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]) or pd.api.types.is_bool_dtype(out[col]):
            continue
        if not colonne_statut(out[col]):
            continue
        traduire = str(col).lower().endswith("statut") or bool(set(out[col].dropna().astype(str)) & set(LIBELLES))
        vals = out[col].map(libelle) if traduire else out[col]
        options = [o for o in COULEURS if o in set(vals.dropna())]
        out[col] = vals.map(lambda x: [x] if isinstance(x, str) and x else [])
        nom = config[col] if isinstance(config.get(col), str) else ("Statut" if str(col) == "statut" else
                                                                    "Gravité" if str(col) == "gravite" else str(col))
        config[col] = st.column_config.MultiselectColumn(
            nom, options=options, color=[COULEURS[o] for o in options], help=AIDE_COLONNES.get(nom))
    formats = dict(formats or {})
    for col, f in list(formats.items()):  # une case vide s'afficherait « None » : la colonne passe en texte
        if col in out and out[col].isna().any():
            out[col] = out[col].map(lambda v, f=f: "—" if v is None or pd.isna(v) else f(v))
            del formats[col]
    donnees = out.style.format(formats, na_rep="—") if formats else out
    return st.dataframe(donnees, column_config=config, **kw)


def pastille(texte: str) -> str:
    """Pastille HTML (contour et texte de la couleur du statut, fond très clair)."""
    return f'<span class="qdd-pastille" style="--c:{COULEURS.get(texte, GRIS)}">{texte}</span>'


def compteurs(lignes: list[tuple[str, int]], titre: str = "") -> str:
    """Bloc HTML « pastille … nombre », une ligne par statut (panneaux de synthèse)."""
    tete = f'<div class="qdd-compteurs-titre">{titre}</div>' if titre else ""
    corps = "".join(f'<div class="qdd-compteur">{pastille(t)}<b>{n}</b></div>' for t, n in lignes)
    return f'<div class="qdd-compteurs">{tete}{corps}</div>'


def legende() -> None:
    """Légende courte des quatre statuts, en pastilles."""
    import streamlit as st

    st.markdown('<div class="qdd-legende">' + "".join(
        f'<span>{pastille(k)} {v}</span>' for k, v in DEFINITIONS.items()) + "</div>", unsafe_allow_html=True)
