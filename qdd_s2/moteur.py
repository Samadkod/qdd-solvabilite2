"""Moteur d'évaluation quantitative de la QDD (mémoire Motard, parties 2 et 3).

Chaîne de calcul :
    contrôles (résultat brut, antériorité) --dégradation--> résultat C_i,d
    C_i,d --moyenne pondérée par p_i,d--> Note_d (donnée critique)
    Note_d --moyenne pondérée par s_d (données critiques)--> Note agrégée
    s_d + tolérance --> Note_d^min, seuils d'acceptation des contrôles, Note^min

Améliorations par rapport au mémoire (désactivables) :
    * contrôle de cohérence tolérance / criticité levé en erreur explicite ;
    * données critiques non contrôlées signalées (le mémoire les suppose absentes) ;
    * règle du maillon faible : nb de données critiques sous leur note minimum ;
    * statut tricolore par donnée et par contrôle ;
    * résultats bornés dans [0 ; 1].
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

import numpy as np
import pandas as pd

from .anteriorite import anteriorite as _anteriorite, degrader


@dataclass(frozen=True)
class Parametres:
    seuil_significativite: float = 0.01      # éq. 5
    mode_tolerance: str = "donnee"           # "donnee" (ΔSCR max, éq. 10) | "globale" (éq. 21)
    delta_scr_max: float = 0.005             # niveau de variation acceptable du SCR par donnée
    tolerance_globale: float = 0.05          # niveau de tolérance globale de non-QDD
    coef_degradation: float = 0.05
    base_anteriorite: str = "frequence"      # "frequence" | "annuelle"
    methode_degradation: str = "simple"      # "simple" | "composee"
    ponderation_donnees: str = "sensibilite" # "sensibilite" | "uniforme"
    repartition_seuil: str = "uniforme"      # "uniforme" (éq. 38) | "ponderee" (éq. 39)
    marge_alerte: float = 0.02               # zone orange sous la note minimum
    donnee_sans_controle: str = "exclure"    # "exclure" (mémoire) | "zero" (prudent)

    def verifier_coherence(self, sensibilite_moyenne: float) -> None:
        """Éq. 12 et 19 : la tolérance doit être cohérente avec la criticité."""
        if self.mode_tolerance == "donnee" and not self.delta_scr_max < self.seuil_significativite:
            raise ValueError(
                f"Incohérence : ΔSCR max ({self.delta_scr_max:.2%}) doit être < seuil de "
                f"significativité ({self.seuil_significativite:.2%}) (éq. 12).")
        if self.mode_tolerance == "globale" and sensibilite_moyenne > 0:
            borne = self.seuil_significativite / sensibilite_moyenne
            if not self.tolerance_globale < borne:
                raise ValueError(
                    f"Incohérence : tolérance globale ({self.tolerance_globale:.2%}) doit être < "
                    f"seuil / sensibilité moyenne = {borne:.2%} (éq. 19).")


def _moy_pond(valeurs: pd.Series, poids: pd.Series) -> float:
    w = poids.astype(float)
    return float((valeurs * w).sum() / w.sum()) if w.sum() > 0 else float("nan")


@dataclass
class Evaluation:
    params: Parametres
    donnees: pd.DataFrame
    controles: pd.DataFrame
    sensibilite_moyenne: float
    indicateurs: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    def _agreger(self, ctrl: pd.DataFrame, col_resultat: str = "resultat", global_: bool = False) -> dict:
        """Note agrégée sur un sous-ensemble de contrôles (éq. 40-42)."""
        crit = self.donnees[self.donnees["critique"]]
        c = ctrl[ctrl["donnee_id"].isin(crit.index) & ctrl["inclus_note"]]
        if c.empty:
            return {"note": np.nan, "note_min": np.nan, "nb_donnees": 0}
        notes = c.groupby("donnee_id").apply(lambda g: _moy_pond(g[col_resultat], g["poids"]),
                                             include_groups=False)
        if global_ and self.params.donnee_sans_controle == "zero":
            manquantes = crit.index.difference(notes.index)
            notes = pd.concat([notes, pd.Series(0.0, index=manquantes)])
        d = crit.loc[notes.index]
        w = d["poids_donnee"]
        return {
            "note": _moy_pond(notes, w),
            "note_min": _moy_pond(d["note_min"], w),
            "nb_donnees": int(len(notes)),
        }

    def par_axe(self, axe: str) -> pd.DataFrame:
        """Indicateurs déclinés selon un axe d'analyse (colonne des contrôles).

        Un axe à valeurs multiples séparées par des virgules (ex. critères
        « E,X ») est éclaté : un contrôle compte dans chaque modalité.
        """
        c = self.controles.copy()
        c[axe] = c[axe].astype(str).str.split(",")
        c = c.explode(axe)
        c[axe] = c[axe].str.strip()
        lignes = []
        for modalite, g in c.groupby(axe):
            r = self._agreger(g)
            rb = self._agreger(g, "resultat_brut")
            if r["nb_donnees"] == 0:
                continue
            gc = g[g["critique"] & g["inclus_note"]]
            lignes.append({
                axe: modalite, "note": r["note"], "note_avant_degradation": rb["note"],
                "note_min": r["note_min"], "ecart_objectif": r["note"] - r["note_min"],
                "nb_donnees_critiques": r["nb_donnees"], "nb_controles": int(len(gc)),
                "taux_validation": float((gc["anteriorite"] == 0).mean()) if len(gc) else np.nan,
                "taux_conformite": float(gc["conforme"].mean()) if len(gc) else np.nan,
            })
        return pd.DataFrame(lignes).set_index(axe)


def evaluer(
    donnees: pd.DataFrame,
    controles: pd.DataFrame,
    params: Parametres = Parametres(),
    date_campagne=None,
    critiques: Iterable[str] | None = None,
) -> Evaluation:
    """Évalue une campagne.

    donnees   : index = donnee_id ; colonnes : sensibilite, [libelle], [critique_expert]
    controles : colonnes : controle_id, donnee_id, resultat_brut, [poids],
                [anteriorite] ou ([date_derniere_real] + [frequence]), + axes libres.
    critiques : force l'ensemble des données critiques (utilisé par l'analyse de variation).
    """
    p = params
    d = donnees.copy()
    if "sensibilite" not in d:
        raise ValueError("donnees doit contenir la colonne 'sensibilite'")
    if critiques is not None:
        crit_set = set(critiques)
        d["critique"] = d.index.isin(crit_set)
    else:
        d["critique"] = d["sensibilite"] >= p.seuil_significativite
        if "critique_expert" in d:  # dire d'expert prioritaire quand renseigné
            exp = d["critique_expert"]
            d.loc[exp.notna(), "critique"] = exp[exp.notna()].astype(bool)

    crit = d[d["critique"]]
    S = float(crit["sensibilite"].mean()) if len(crit) else 0.0
    p.verifier_coherence(S)

    # Pondération des données (éq. 6) et tolérance (éq. 10 ou 21)
    d["poids_donnee"] = np.where(d["critique"],
                                 d["sensibilite"] if p.ponderation_donnees == "sensibilite" else 1.0, 0.0)
    s = d["sensibilite"].where(d["critique"])
    if p.mode_tolerance == "donnee":
        d["tolerance"] = p.delta_scr_max / s
    else:
        d["tolerance"] = p.tolerance_globale * S / s
    d["note_min"] = 1 - d["tolerance"]

    # Contrôles : antériorité + dégradation
    c = controles.copy()
    if "poids" not in c:
        c["poids"] = 1.0
    c["poids"] = c["poids"].fillna(1.0).astype(float)
    if "anteriorite" not in c or c["anteriorite"].isna().any():
        if date_campagne is None:
            raise ValueError("Fournir 'anteriorite' ou date_campagne + date_derniere_real + frequence")
        c["anteriorite"] = [
            _anteriorite(r.date_derniere_real, date_campagne, r.frequence, p.base_anteriorite)
            if pd.notna(r.date_derniere_real) else np.nan
            for r in c.itertuples()
        ]
    jamais = c["anteriorite"].isna() | c["resultat_brut"].isna()
    c["jamais_realise"] = jamais
    c["resultat"] = [
        0.0 if j else degrader(rb, a, p.coef_degradation, p.methode_degradation)
        for j, rb, a in zip(jamais, c["resultat_brut"], c["anteriorite"])
    ]
    c["resultat_brut"] = c["resultat_brut"].fillna(0.0)
    c["critique"] = c["donnee_id"].map(d["critique"]).fillna(False).astype(bool)
    # AMÉLIORATION : les contrôles de restitution (état QRT vs sa source) vérifient la production de
    # l'état, pas la donnée. Ils sont suivis (seuil, statut, registre) mais exclus de la note QDD,
    # sinon des contrôles parfaits en aval diluent un défaut amont (moyennes compensatoires).
    if "inclus_note" not in c:
        c["inclus_note"] = True
    c["inclus_note"] = c["inclus_note"].map(lambda v: True if pd.isna(v) else bool(int(v))).astype(bool)
    cn = c[c["inclus_note"]]

    # Notes par donnée (éq. 22) avant / après dégradation
    def _note(col):
        return cn.groupby("donnee_id").apply(lambda g: _moy_pond(g[col], g["poids"]), include_groups=False)
    d["note"] = _note("resultat")
    d["note_avant_degradation"] = _note("resultat_brut")
    d["nb_controles"] = cn.groupby("donnee_id").size()
    d["nb_controles"] = d["nb_controles"].fillna(0).astype(int)
    if p.donnee_sans_controle == "zero":
        mask = d["critique"] & (d["nb_controles"] == 0)
        d.loc[mask, ["note", "note_avant_degradation"]] = 0.0
    # Couverture des critères S2 (E = exhaustivité, X = exactitude, P = pertinence)
    if "criteres" in c:
        cov = cn.groupby("donnee_id")["criteres"].apply(
            lambda x: "".join(sorted({k.strip() for v in x for k in str(v).split(",")})))
        d["criteres_couverts"] = cov

    # Poids des contrôles (éq. 23-24) et seuils d'acceptation (éq. 38-39)
    somme_p = c["donnee_id"].map(cn.groupby("donnee_id")["poids"].sum())
    moy_p = c["donnee_id"].map(cn.groupby("donnee_id")["poids"].mean())
    c["poids_dans_donnee"] = (c["poids"] / somme_p).where(c["inclus_note"], 0.0)
    inclus = d["critique"] & ((d["nb_controles"] > 0) | (p.donnee_sans_controle == "zero"))
    wd = d["poids_donnee"] / d.loc[inclus, "poids_donnee"].sum()
    d["poids_dans_note"] = wd.where(inclus, 0.0)
    c["poids_dans_note"] = c["poids_dans_donnee"] * c["donnee_id"].map(d["poids_dans_note"]).fillna(0)
    tol = c["donnee_id"].map(d["tolerance"])
    if p.repartition_seuil == "uniforme":
        c["seuil"] = 1 - tol
    else:
        c["seuil"] = 1 - tol * moy_p / c["poids"]
    # AMÉLIORATION : seuil fixe pour les contrôles de restitution (QRT vs source). Un écart entre un état
    # réglementaire et sa source est une erreur, pas une incertitude : il ne doit pas hériter de la
    # tolérance dérivée de la sensibilité. Ces contrôles sont évalués même si la donnée n'est pas critique.
    if "seuil_fixe" not in c:
        c["seuil_fixe"] = np.nan
    fixe = pd.to_numeric(c["seuil_fixe"], errors="coerce")
    c["seuil"] = fixe.where(fixe.notna(), c["seuil"])
    c["evalue"] = c["critique"] | fixe.notna()
    c["conforme"] = (c["resultat"] >= c["seuil"]).where(c["evalue"])

    def _statut(note, mini):
        if pd.isna(note) or pd.isna(mini):
            return None
        return "vert" if note >= mini else ("orange" if note >= mini - p.marge_alerte else "rouge")
    d["statut"] = [_statut(n, m) if cr else None for n, m, cr in zip(d["note"], d["note_min"], d["critique"])]
    # seuil fixe (restitution) : binaire, tout dépassement est rouge (pas de zone orange)
    c["statut"] = [(("vert" if r >= s_ else "rouge") if pd.notna(fx) else _statut(r, s_)) if ev_ else None
                   for r, s_, ev_, fx in zip(c["resultat"], c["seuil"], c["evalue"], fixe)]

    ev = Evaluation(p, d, c, S)
    g = ev._agreger(c, global_=True)
    gb = ev._agreger(c, "resultat_brut", global_=True)
    cc = c[c["critique"] & c["inclus_note"]]
    cres = c[~c["inclus_note"] & c["evalue"]]
    critd = d[d["critique"]]
    ev.indicateurs = {
        "nb_donnees_critiques": int(len(critd)),
        "sensibilite_moyenne": S,
        "note_avant_degradation": gb["note"],
        "note": g["note"],
        "note_min": g["note_min"],
        "ecart_objectif": g["note"] - g["note_min"],
        "degradation_moyenne": 1 - g["note"] / gb["note"] if gb["note"] else np.nan,
        "taux_validation": float((cc["anteriorite"] == 0).mean()) if len(cc) else np.nan,
        "anteriorite_moyenne": float(cc["anteriorite"].mean()) if len(cc) else np.nan,
        # --- améliorations ---
        "taux_conformite_controles": float(cc["conforme"].mean()) if len(cc) else np.nan,
        "nb_donnees_hors_tolerance": int((critd["note"] < critd["note_min"]).sum()),
        "note_plancher": float(critd["note"].min()) if len(critd) else np.nan,
        "donnees_critiques_non_controlees": critd.index[critd["nb_controles"] == 0].tolist(),
        "tolerance_globale_effective": 1 - g["note_min"],
        "nb_controles_restitution": int(len(cres)),
        "taux_conformite_restitutions": float(cres["conforme"].mean()) if len(cres) else np.nan,
    }
    return ev


# ----------------------------------------------------------------------
# Analyse de la variation entre deux campagnes (mémoire §3.1.3, tableau 20)
# ----------------------------------------------------------------------
ORDRE_DEFAUT = [
    ("suppression_controles", "Suppression de contrôles"),
    ("suppression_critiques", "Sortie de données critiques"),
    ("resultats", "QDD mesurée par les contrôles (antériorité intacte)"),
    ("anteriorite", "Antériorité des contrôles"),
    ("coef_degradation", "Coefficient de dégradation"),
    ("poids_controles", "Pondération des contrôles"),
    ("ajout_controles", "Ajout de contrôles"),
    ("sensibilites", "Sensibilités des données critiques"),
    ("ajout_critiques", "Entrée de données critiques"),
]


@dataclass
class Etat:
    """Photographie d'une campagne pour l'analyse de variation."""
    donnees: pd.DataFrame      # index donnee_id, sensibilite
    controles: pd.DataFrame    # controle_id, donnee_id, resultat_brut, anteriorite, poids
    params: Parametres

    def critiques(self) -> set:
        ev = evaluer(self.donnees, self.controles, self.params)
        return set(ev.donnees.index[ev.donnees["critique"]])


def _hybride(prec: Etat, cour: Etat, actifs: set) -> tuple:
    cp = prec.controles.set_index("controle_id")
    cc = cour.controles.set_index("controle_id")
    ids = list(cp.index)
    if "suppression_controles" in actifs:
        ids = [i for i in ids if i in cc.index]
    if "ajout_controles" in actifs:
        ids += [i for i in cc.index if i not in cp.index]
    lignes = []
    for i in ids:
        src_p = cp.loc[i] if i in cp.index else cc.loc[i]
        r = src_p.copy()
        if i in cc.index:
            for comp, col in (("resultats", "resultat_brut"), ("anteriorite", "anteriorite"),
                              ("poids_controles", "poids")):
                if comp in actifs or i not in cp.index:
                    r[col] = cc.loc[i, col]
        r["controle_id"] = i
        lignes.append(r)
    ctrl = pd.DataFrame(lignes).reset_index(drop=True)

    sens = prec.donnees["sensibilite"].copy()
    for k, v in cour.donnees["sensibilite"].items():
        if k not in sens.index or "sensibilites" in actifs:
            sens.loc[k] = v
    don = pd.DataFrame({"sensibilite": sens})

    crit = prec.critiques()
    crit_c = cour.critiques()
    if "suppression_critiques" in actifs:
        crit &= crit_c
    if "ajout_critiques" in actifs:
        crit |= crit_c
    params = replace(prec.params, coef_degradation=(cour.params.coef_degradation
                     if "coef_degradation" in actifs else prec.params.coef_degradation))
    # le contrôle de cohérence est neutralisé pendant les états intermédiaires
    params = replace(params, mode_tolerance="donnee", delta_scr_max=0.0)
    return don, ctrl, params, crit


def analyse_variation(prec: Etat, cour: Etat, ordre=ORDRE_DEFAUT) -> pd.DataFrame:
    """Décompose Note(N) - Note(N-1) facteur par facteur (substitutions successives)."""
    actifs: set = set()
    don, ctrl, par, crit = _hybride(prec, cour, actifs)
    note = evaluer(don, ctrl, par, critiques=crit).indicateurs["note"]
    lignes = [{"etape": "Note QDD agrégée N-1", "note": note, "impact": np.nan}]
    for cle, libelle in ordre:
        actifs.add(cle)
        don, ctrl, par, crit = _hybride(prec, cour, actifs)
        n2 = evaluer(don, ctrl, par, critiques=crit).indicateurs["note"]
        lignes.append({"etape": libelle, "note": n2, "impact": n2 - note})
        note = n2
    lignes.append({"etape": "Note QDD agrégée N", "note": note, "impact": np.nan})
    return pd.DataFrame(lignes)
