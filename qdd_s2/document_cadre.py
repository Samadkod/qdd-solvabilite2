"""Document cadre du dispositif QDD, généré depuis les référentiels et les paramètres du moteur.

La notice ACPR QDD (points 16 et 17) attend un document cadre validé par la direction générale et revu au moins
une fois par an, qui contient au minimum : périmètre, rôles et responsabilités, comitologie, critères (S2,
criticité, tolérance) et instruments de suivi. Ce module écrit tout ce qui se calcule ou se lit dans le dépôt ;
ce qui relève d'une décision de l'organisme (rôles nominatifs, comités, validation) reste « À compléter par
l'organisme ». Chaque chiffre du document vient de valeurs(), que tests/test_document_cadre.py compare au moteur.
"""
from __future__ import annotations

import pandas as pd

A_COMPLETER = "**À compléter par l'organisme.**"
NOMS_CRITERES = {"E": "Exhaustivité", "X": "Exactitude", "P": "Pertinence"}
FAMILLES = {"coherence": "cohérence", "rapprochement": "rapprochement"}


def _pct(x: float, d: int = 2) -> str:
    return f"{x * 100:.{d}f} %".replace(".", ",")


def valeurs(campagne, referentiel: pd.DataFrame, dictionnaire: pd.DataFrame, flux: pd.DataFrame,
            choc: float) -> dict:
    """Tous les chiffres du document, lus dans les sorties du moteur et les référentiels."""
    ev = campagne.evaluation
    p, don, ind = ev.params, ev.donnees, ev.indicateurs
    crit = don[don["critique"].astype(bool)]
    expert = don["critique_expert"].astype(str).str.lower().eq("true") if "critique_expert" in don else None
    inclus = referentiel["inclus_note"].astype(str).eq("1")
    lettres = referentiel.loc[inclus, "criteres"].str.split(",").explode().str.strip()
    return {
        "campagne": campagne.campagne, "arrete": campagne.date_arrete,
        "nb_donnees": len(don), "nb_critiques": len(crit),
        "critiques": list(crit.index), "non_critiques": list(don.index[~don["critique"].astype(bool)]),
        "critiques_expert": sorted(don.index[expert & don["critique"].astype(bool)]) if expert is not None else [],
        "nb_externes": int(dictionnaire["origine"].eq("Externe").sum()),
        "choc": choc, "seuil_significativite": p.seuil_significativite, "mode_tolerance": p.mode_tolerance,
        "delta_scr_max": p.delta_scr_max, "marge_alerte": p.marge_alerte, "coef_degradation": p.coef_degradation,
        "sensibilites": crit["sensibilite"].to_dict(), "notes_min": crit["note_min"].to_dict(),
        "sensibilite_moyenne": ind["sensibilite_moyenne"], "tolerance_globale_effective": ind["tolerance_globale_effective"],
        "note_min_globale": ind["note_min"],
        "nb_controles": len(referentiel), "nb_controles_note": int(inclus.sum()),
        "nb_restitution": int((~inclus).sum()),
        "par_famille": referentiel.loc[inclus, "famille"].value_counts().to_dict(),
        "par_critere": lettres.value_counts().to_dict(),
        "seuil_restitution": float(referentiel.loc[~inclus, "seuil_fixe"].astype(float).iloc[0]),
        "nb_flux": len(flux), "nb_flux_zone_risque": int(flux["zone_risque"].astype(str).eq("True").sum()),
        "nb_flux_externes": int(flux["origine"].eq("Externe").sum()),
        "nb_zones_critiques": campagne.gouvernance["nb_zones_risque_critiques"],
        "nb_zones_non_couvertes": campagne.gouvernance["nb_zones_non_couvertes"],
        "proprietaires": sorted(dictionnaire["proprietaire"].unique()),
        "responsables": sorted(referentiel["responsable"].unique()),
    }


def markdown(v: dict) -> str:
    sens = "\n".join(f"| {d} | {_pct(s)}{' (moyenne, dire d’expert)' if d in v['critiques_expert'] else ''} | "
                     f"{_pct(v['notes_min'][d])} |" for d, s in v["sensibilites"].items())
    if v["mode_tolerance"] == "donnee":
        tol = (f"- Mode : tolérance par donnée ; variation acceptable du SCR par donnée : {_pct(v['delta_scr_max'])}.\n"
               f"- Note minimum d'une donnée = 1 − {_pct(v['delta_scr_max'])} ÷ sa sensibilité ; note minimum globale :")
    else:
        tol = "- Mode : tolérance globale déclinée par donnée ; note minimum globale :"
    fam = ", ".join(f"{n} de {FAMILLES.get(f, f)}" for f, n in sorted(v["par_famille"].items()))
    crit = ", ".join(f"{NOMS_CRITERES[k]} : {v['par_critere'].get(k, 0)}" for k in "EXP")
    expert = ", ".join(v["critiques_expert"]) or "aucune"
    return f"""# Document cadre du dispositif de maîtrise de la qualité des données

*Prototype sur données 100 % fictives, généré le {v['arrete']} (campagne {v['campagne']}) à partir des référentiels
et des paramètres du moteur. Il ne vaut pas document cadre validé : les parties marquées « À compléter par
l'organisme » relèvent de décisions humaines.*

## 1. Validation et revue
- Validation par la direction générale : {A_COMPLETER}
- Date de la dernière revue annuelle : {A_COMPLETER}

## 2. Périmètre des données couvertes
- {v['nb_donnees']} données au répertoire (`referentiels/repertoire_donnees.csv`), dont {v['nb_critiques']} critiques
  et {v['nb_externes']} d'origine externe.
- Données critiques : {", ".join(v['critiques'])}.
- Données suivies, non critiques : {", ".join(v['non_critiques'])}.
- Systèmes couverts : de la saisie dans les outils de gestion jusqu'aux états QRT et à l'outil SCR
  ({v['nb_flux']} flux au lignage, dont {v['nb_flux_externes']} externes).

## 3. Rôles et responsabilités
- Responsable QDD, personnes relais, comité de pilotage : {A_COMPLETER}
- Propriétaires de données déclarés au répertoire : {", ".join(v['proprietaires'])}.
- Responsables de contrôle déclarés au référentiel : {", ".join(v['responsables'])}.

## 4. Comitologie
- Comités, missions, participants et fréquence : {A_COMPLETER}

## 5. Critères
### 5.1 Critères Solvabilité 2
Exhaustivité (E), exactitude (X), pertinence (P). Contrôles comptés dans la note, par critère vérifié : {crit}.

### 5.2 Criticité
- Méthode : sensibilité du SCR = variation relative du SCR pour un choc de {_pct(v['choc'], 0)} sur la donnée,
  divisée par le choc.
- Seuil de criticité : une donnée est critique si sa sensibilité est au moins de {_pct(v['seuil_significativite'])}.
- Données critiques à dire d'expert (sans sensibilité calculable) : {expert}.
- Justification du seuil retenu : {A_COMPLETER}

| Donnée critique | Sensibilité | Note minimum exigée |
|---|---|---|
{sens}

### 5.3 Tolérance au risque de non-qualité
{tol}
  {_pct(v['note_min_globale'])} ; tolérance globale équivalente : {_pct(v['tolerance_globale_effective'])}
  (sensibilité moyenne des données critiques : {_pct(v['sensibilite_moyenne'])}).
- Grille : conforme à partir de la note minimum ; à corriger jusqu'à {v['marge_alerte'] * 100:g} points sous la
  note minimum ; bloquant au-delà.
- Restitutions QRT : seuil fixe de {_pct(v['seuil_restitution'])}, statut binaire, hors note.
- Contrôle non refait dans sa périodicité : résultat réduit de {_pct(v['coef_degradation'], 0)} par période de retard.

## 6. Instruments de suivi
- Référentiel des contrôles : {v['nb_controles']} contrôles ({v['nb_controles_note']} comptés dans la note : {fam} ;
  {v['nb_restitution']} de restitution QRT), avec risque couvert, périodicité, critères, seuil, réalisation, mode
  opératoire et responsable (`referentiels/referentiel_controles.csv`).
- Méthode d'agrégation : note de chaque donnée = moyenne pondérée de ses contrôles comptés dans la note ; note
  globale = moyenne des notes des données critiques pondérée par leur sensibilité.
- Répertoire des données : `referentiels/repertoire_donnees.csv`.
- Cartographie des flux et lignage des données critiques : `referentiels/lignage_flux.csv` et
  `referentiels/lignage_donnees.csv` ; {v['nb_flux_zone_risque']} flux en zone de risque ;
  {v['nb_zones_critiques']} passages de données critiques en zone de risque, dont {v['nb_zones_non_couvertes']} sans
  contrôle à cet arrêté.
- Contrôle de niveau 2 et archive des données en défaut : `qdd_s2/niveau2.py`, `archives/donnees_en_defaut/`.
"""


def document_cadre(campagne, dossier_referentiels, choc: float) -> str:
    from .niveau2 import charger_referentiels
    ref, dic, flux = charger_referentiels(dossier_referentiels)
    return markdown(valeurs(campagne, ref, dic, flux, choc))
