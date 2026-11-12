"""Contrôle de niveau 2 : adéquation et efficacité des contrôles de niveau 1.

La notice ACPR QDD (points 67 à 70, et point 19 pour le rôle du contrôle interne) attend des contrôles de
2nd niveau qui vérifient l'adéquation et l'efficacité des contrôles de 1er niveau. Ce module ne crée aucun
score d'« efficacité » : il calcule des constats objectifs, chacun avec une règle écrite, à partir de ce que
le dispositif produit déjà (référentiel des contrôles, résultats des campagnes, lignage, dictionnaire).

Statut de chaque indicateur :
  - vert   : aucun écart ;
  - orange : au moins un écart (à corriger, non bloquant) ;
  - « À revoir » : signal à examiner, pas une défaillance (contrôle jamais en anomalie).
Aucun indicateur n'est classé rouge : la notice ne fixe pas de seuil de gravité pour le niveau 2, et le
dispositif n'en invente pas.
"""
from __future__ import annotations

import pandas as pd

A_REVOIR = "À revoir"
CRITERES_S2 = ("E", "X", "P")
NOMS_CRITERES = {"E": "exhaustivité", "X": "exactitude", "P": "pertinence"}
# référentiel des contrôles : contenu attendu pour chaque contrôle (notice, points 67-70)
CHAMPS_REFERENTIEL = {
    "risque_couvert": "risque sous-jacent", "frequence": "périodicité", "criteres": "critères",
    "donnee_id": "donnée vérifiée", "mode_realisation": "réalisation manuelle ou automatique",
    "mode_operatoire": "mode opératoire", "responsable": "responsable",
}
COLONNES = ["id", "indicateur", "regle", "valeur", "nb_ecarts", "statut", "detail"]


def _vide(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""


def _ligne(i, indicateur, regle, ok, total, ecarts, statut_ecart="orange"):
    return {"id": i, "indicateur": indicateur, "regle": regle, "valeur": f"{ok} sur {total}",
            "nb_ecarts": len(ecarts), "statut": "vert" if not ecarts else statut_ecart,
            "detail": " ; ".join(ecarts)}


def referentiel_complet(ref: pd.DataFrame) -> dict:
    """N2-01 : chaque contrôle renseigne les champs attendus ; le seuil vient du moteur ou de seuil_fixe."""
    ecarts = []
    for r in ref.itertuples():
        manque = [nom for col, nom in CHAMPS_REFERENTIEL.items() if _vide(getattr(r, col, None))]
        if manque:
            ecarts.append(f"{r.controle_id} : {', '.join(manque)}")
    return _ligne("N2-01", "Référentiel des contrôles complet",
                  "Chaque contrôle renseigne risque, périodicité, critères, donnée, réalisation, mode opératoire "
                  "et responsable.", len(ref) - len(ecarts), len(ref), ecarts)


def controles_a_jour(controles: pd.DataFrame) -> dict:
    """N2-02 : contrôle à jour = antériorité nulle sur tous ses points (refait dans sa périodicité)."""
    ant = controles.groupby("controle")["anteriorite"].max()
    retard = ant[ant > 0]
    ecarts = [f"{c} ({int(n)} période{'s' if n > 1 else ''} de retard)" for c, n in retard.sort_index().items()]
    return _ligne("N2-02", "Contrôles réalisés dans leur périodicité",
                  "Un contrôle est à jour si aucun de ses points n'a d'antériorité (refait depuis sa dernière "
                  "échéance).", len(ant) - len(retard), len(ant), ecarts)


def jamais_en_anomalie(historique: list[pd.DataFrame]) -> dict:
    """N2-03 : contrôle noté au moins une fois et jamais orange ni rouge sur toutes les campagnes.

    Signal « À revoir » : le seuil est peut-être trop large, ou le défaut visé n'existe plus. Ce n'est pas une
    défaillance : un contrôle qui ne trouve rien peut être parfaitement utile.
    """
    tout = pd.concat(historique, ignore_index=True)
    notes = tout[tout["statut"].isin(["vert", "orange", "rouge"])]
    par = notes.groupby("controle")["statut"].agg(lambda s: set(s))
    jamais = sorted(c for c, st in par.items() if st == {"vert"})
    mini = notes.groupby("controle")["resultat"].min()
    ecarts = [f"{c} (résultat minimum {mini[c] * 100:.2f} %)".replace(".", ",") for c in jamais]
    return _ligne("N2-03", "Contrôles jamais en anomalie sur les campagnes",
                  f"Contrôle noté sur les {len(historique)} campagnes sans jamais passer sous son seuil : seuil "
                  "à revoir ou défaut disparu (signal, pas une défaillance).",
                  len(par) - len(jamais), len(par), ecarts, statut_ecart=A_REVOIR)


def critiques_sans_controle(controles: pd.DataFrame, donnees: pd.DataFrame) -> dict:
    """N2-04 : donnée critique sans aucun point de contrôle compté dans la note."""
    crit = donnees.index[donnees["critique"].astype(bool)]
    notes = set(controles.loc[controles["inclus_note"].astype(bool), "donnee_id"])
    ecarts = sorted(d for d in crit if d not in notes)
    return _ligne("N2-04", "Données critiques contrôlées",
                  "Chaque donnée critique a au moins un contrôle qui compte dans la note.",
                  len(crit) - len(ecarts), len(crit), ecarts)


def criteres_non_couverts(donnees: pd.DataFrame) -> dict:
    """N2-05 : pour chaque donnée critique, critères S2 (E, X, P) vérifiés par aucun contrôle compté dans la note
    (colonne criteres_couverts du moteur : les contrôles de restitution QRT n'y entrent pas, règle de méthode 1)."""
    crit = donnees[donnees["critique"].astype(bool)].sort_index()
    ecarts = [f"{d} : {NOMS_CRITERES[k]}" for d, cov in crit["criteres_couverts"].fillna("").items()
              for k in CRITERES_S2 if k not in cov]
    total = len(crit) * len(CRITERES_S2)
    return _ligne("N2-05", "Critères S2 couverts par donnée critique",
                  "Pour chaque donnée critique, l'exhaustivité, l'exactitude et la pertinence sont vérifiées par "
                  "au moins un contrôle compté dans la note.", total - len(ecarts), total, ecarts)


def zones_non_couvertes(couverture: pd.DataFrame) -> dict:
    """N2-06 : passage d'une donnée critique par une zone de risque du lignage sans contrôle (même règle que la
    couverture du lignage, gouvernance.indicateurs_couverture)."""
    z = couverture[couverture["zone_risque"] & couverture["critique"]]
    non = z[~z["couvert"]].sort_values(["flux_id", "donnee_id"])
    ecarts = [f"{r.flux_id} · {r.donnee_id}" for r in non.itertuples()]
    return _ligne("N2-06", "Zones de risque des données critiques couvertes",
                  "Chaque passage d'une donnée critique par une zone de risque du lignage est sécurisé par un "
                  "contrôle.", len(z) - len(non), len(z), ecarts)


def donnees_externes(dictionnaire: pd.DataFrame, couverture: pd.DataFrame, flux: pd.DataFrame) -> dict:
    """N2-07 : donnée externe = traitement documenté, et chaque flux externe de son lignage contrôlé."""
    ext_flux = set(flux.loc[flux["origine"] == "Externe", "flux_id"])
    ext = dictionnaire[dictionnaire["origine"] == "Externe"]
    ecarts, total = [], 0
    for d, r in ext.sort_index().iterrows():
        total += 1
        pb = []
        if _vide(r.get("fournisseur")) or _vide(r.get("traitement_externe")):
            pb.append("fournisseur ou traitement non documenté")
        passages = couverture[(couverture["donnee_id"] == d) & couverture["flux_id"].isin(ext_flux)]
        if passages.empty:
            pb.append("aucun flux externe dans le lignage")
        pb += [f"flux externe {f} sans contrôle" for f in sorted(passages.loc[~passages["couvert"], "flux_id"])]
        if pb:
            ecarts.append(f"{d} : {', '.join(pb)}")
    return _ligne("N2-07", "Données externes documentées et contrôlées",
                  "Une donnée externe a un fournisseur et un traitement documentés, et chaque flux externe de son "
                  "lignage est contrôlé.", total - len(ecarts), total, ecarts)


def niveau2(campagnes: list, referentiel: pd.DataFrame, dictionnaire: pd.DataFrame,
            flux: pd.DataFrame) -> pd.DataFrame:
    """Indicateurs de niveau 2 de la dernière campagne (N2-03 utilise toutes les campagnes fournies).

    campagnes : sorties de lancer_campagnes (ResultatCampagne), dans l'ordre du plan.
    dictionnaire : repertoire_donnees indexé par donnee_id.
    """
    n = campagnes[-1]
    ctrl, don = n.evaluation.controles, n.evaluation.donnees
    lignes = [
        referentiel_complet(referentiel),
        controles_a_jour(ctrl),
        jamais_en_anomalie([c.evaluation.controles for c in campagnes]),
        critiques_sans_controle(ctrl, don),
        criteres_non_couverts(don),
        zones_non_couvertes(n.couverture),
        donnees_externes(dictionnaire, n.couverture, flux),
    ]
    return pd.DataFrame(lignes, columns=COLONNES)


def charger_referentiels(dossier) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(référentiel des contrôles, dictionnaire indexé par donnee_id, catalogue des flux), en texte."""
    from pathlib import Path
    lire = lambda nom: pd.read_csv(Path(dossier) / nom, dtype=str, keep_default_na=False)
    return (lire("referentiel_controles.csv"), lire("repertoire_donnees.csv").set_index("donnee_id"),
            lire("lignage_flux.csv"))


def niveau2_par_campagne(campagnes: list, dossier_referentiels) -> list[pd.DataFrame]:
    """Indicateurs de niveau 2 de chaque campagne, calculés avec les campagnes connues à sa date."""
    refs = charger_referentiels(dossier_referentiels)
    return [niveau2(campagnes[:i + 1], *refs) for i in range(len(campagnes))]
