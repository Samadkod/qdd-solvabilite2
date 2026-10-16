"""Orchestration d'une campagne QDD de bout en bout.

    référentiels (répertoire de données, référentiel des contrôles, plan)
      + base de données (SI fictif DuckDB ou vraie base)
      -> exécution des contrôles SQL -> points de contrôle (1 donnée chacun)
      -> historique des résultats -> antériorité / dégradation
      -> sensibilités SCR -> criticité, tolérance
      -> Evaluation (moteur) + analyse de variation
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .mesures import mesure_rapprochement, ratio_anomalie, resultat_controle
from .moteur import Etat, Evaluation, Parametres, analyse_variation, evaluer
from .gouvernance import (couverture_lignage, entree_journal, indicateurs_anomalies, indicateurs_couverture,
                          maj_registre)
from .sensibilite import SIGMA, scr_formule_standard_simplifiee, sensibilites

RACINE = Path(__file__).resolve().parents[1]


@dataclass
class Config:
    base: Path = RACINE / "data" / "btp_fictif.duckdb"
    referentiels: Path = RACINE / "referentiels"
    sql: Path = RACINE / "sql" / "controles"
    methode_ecart: str = "memoire"        # "memoire" | "symetrique"
    ponderation_montant: bool = True      # ratio d'anomalie pondéré en montant si dispo
    choc_sensibilite: float = 0.15
    params: Parametres = Parametres()


def charger_referentiels(cfg: Config):
    rep = pd.read_csv(cfg.referentiels / "repertoire_donnees.csv").set_index("donnee_id")
    rep["critique_expert"] = rep["critique_expert"].map({True: True, False: False, "True": True, "False": False})
    ref = pd.read_csv(cfg.referentiels / "referentiel_controles.csv")
    plan = pd.read_csv(cfg.referentiels / "plan_campagnes.csv")
    hist = pd.read_csv(cfg.referentiels / "historique_resultats.csv")
    return rep, ref, plan, hist


def charger_lignage(cfg: Config):
    flux = pd.read_csv(cfg.referentiels / "lignage_flux.csv")
    lig = pd.read_csv(cfg.referentiels / "lignage_donnees.csv")
    return lig, flux


def volumetries(con, arrete: str) -> dict:
    """Nombre de lignes par table source pour l'arrêté (piste d'audit)."""
    out = {}
    for (t,) in con.execute("SHOW TABLES").fetchall():
        cols = [c[0] for c in con.execute(f"DESCRIBE {t}").fetchall()]
        if "arrete" in cols:
            out[t] = con.execute(f"SELECT COUNT(*) FROM {t} WHERE arrete = $a", {"a": arrete}).fetchone()[0]
    return out


def executer_controle(con, ligne: pd.Series, arrete: str, cfg: Config) -> pd.DataFrame:
    """Exécute le SQL d'un contrôle et renvoie un point de contrôle par maille."""
    sql = (cfg.sql / ligne.fichier_sql).read_text(encoding="utf-8")
    res = con.execute(sql, {"arrete": arrete}).df()
    pts = []
    for _, r in res.iterrows():
        if ligne.famille == "rapprochement":
            vals = [float(r[c]) for c in ("v1", "v2", "v3") if c in r and pd.notna(r[c])]
            mesure = mesure_rapprochement(vals, methode=cfg.methode_ecart)
            detail = " | ".join(f"{v:,.2f}" for v in vals)
        else:
            n, tot = int(r.n_anomalies), int(r.n_elements)
            use_m = cfg.ponderation_montant and pd.notna(r.get("montant_total")) and r.montant_total
            mesure = (float(r.montant_anomalies) / float(r.montant_total)) if use_m else (n / tot if tot else 0.0)
            detail = f"{n} anomalies / {tot}" + (f" ; {r.montant_anomalies:,.0f} € / {r.montant_total:,.0f} €" if use_m else "")
        pts.append({"point_id": f"{ligne.controle_id}|{r.maille}", "maille": r.maille,
                    "mesure_non_qdd": mesure, "resultat_brut": resultat_controle(mesure), "detail": detail})
    return pd.DataFrame(pts)


def entrees_scr(con, arrete: str) -> dict:
    """Agrège les données critiques candidates (M€) pour la formule standard simplifiée."""
    q = lambda s: con.execute(s, {"arrete": arrete}).df()
    pa = q("SELECT segment, SUM(prime_acquise)/1e6 v FROM (SELECT DISTINCT contrat_id, segment, prime_acquise "
           "FROM gestion_contrats WHERE arrete=$arrete) GROUP BY segment").set_index("segment")["v"]
    pr = q("SELECT segment, SUM(provision_dossier)/1e6 v FROM gestion_sinistres WHERE arrete=$arrete "
           "GROUP BY segment").set_index("segment")["v"]
    tx = q("SELECT t.segment, t.taux_cession FROM reassurance_traites t WHERE arrete=$arrete").set_index("segment")["taux_cession"]
    pl = q("SELECT classe, SUM(valeur_marche)/1e6 v FROM placements_depositaire WHERE arrete=$arrete "
           "GROUP BY classe").set_index("classe")["v"]
    x = {f"primes_acquises_{s}": float(pa[s]) for s in SIGMA}
    x |= {f"provisions_sinistres_{s}": float(pr[s]) for s in SIGMA}
    x["taux_cession"] = float((tx * pa).sum() / pa.sum())
    x["placements_actions"] = float(pl["ACTIONS"])
    x["placements_obligations"] = float(pl["OBLIGATIONS"])
    return x


@dataclass
class ResultatCampagne:
    campagne: str
    date_arrete: str
    evaluation: Evaluation
    sensibilites: pd.DataFrame
    scr_ref: float
    points: pd.DataFrame
    etat: Etat
    couverture: pd.DataFrame = None
    registre: pd.DataFrame = None
    gouvernance: dict = None
    journal: dict = None


def lancer_campagnes(cfg: Config = Config()) -> tuple[list[ResultatCampagne], pd.DataFrame]:
    rep, ref, plan, hist = charger_referentiels(cfg)
    lig, flux = charger_lignage(cfg)
    registre = None
    con = duckdb.connect(str(cfg.base), read_only=True)
    historique = hist.rename(columns={"commentaire": "detail"}).assign(mesure_non_qdd=np.nan)
    sorties = []
    for camp in plan.itertuples():
        arrete = camp.date_arrete
        non_real = set(str(camp.controles_non_realises).split(";")) if pd.notna(camp.controles_non_realises) else set()
        # 1. exécution des contrôles réalisés
        nb_exec = 0
        for ligne in ref.itertuples():
            if ligne.controle_id in non_real:
                continue
            pts = executer_controle(con, pd.Series(ligne._asdict()), arrete, cfg)
            pts["date_realisation"] = arrete
            nb_exec += 1
            historique = pd.concat([historique, pts], ignore_index=True)
        # 2. dernier résultat connu de chaque point à la date de campagne
        h = historique[pd.to_datetime(historique["date_realisation"]) <= pd.Timestamp(arrete)]
        dernier = h.sort_values("date_realisation").groupby("point_id").tail(1).set_index("point_id")
        lignes = []
        for pid, r in dernier.iterrows():
            cid, maille = pid.split("|")
            rc = ref.set_index("controle_id").loc[cid]
            lignes.append({
                "controle_id": pid, "controle": cid, "libelle": rc.libelle, "famille": rc.famille,
                "donnee_id": rc.donnee_id.format(maille=maille), "maille": maille,
                "criteres": rc.criteres, "frequence": rc.frequence, "poids": rc.poids, "etape": rc.etape,
                "responsable": rc.responsable, "flux": rc.flux, "seuil_fixe": rc.get("seuil_fixe"), "inclus_note": rc.get("inclus_note", 1), "resultat_brut": r.resultat_brut,
                "mesure_non_qdd": r.get("mesure_non_qdd"),
                "date_derniere_real": r.date_realisation, "detail": r.get("detail"),
                "realise_campagne": r.date_realisation == arrete,
            })
        ctrl = pd.DataFrame(lignes)
        # 3. sensibilités SCR et criticité
        x = entrees_scr(con, arrete)
        sens = sensibilites(scr_formule_standard_simplifiee, x, choc=cfg.choc_sensibilite)
        sens = sens.rename(index={"placements_actions": "placements_ACTIONS",
                                  "placements_obligations": "placements_OBLIGATIONS"})
        don = rep.copy()
        don["sensibilite"] = sens["sensibilite"].reindex(don.index).fillna(0.0)
        # données critiques à dire d'expert sans sensibilité calculable : poids = sensibilité moyenne
        exp = don["critique_expert"].fillna(False).astype(bool) & (don["sensibilite"] == 0)
        don.loc[exp, "sensibilite"] = sens.loc[sens["sensibilite"] >= cfg.params.seuil_significativite, "sensibilite"].mean()
        don["valeur"] = sens["valeur"].reindex(don.index)
        don["non_linearite"] = sens["non_linearite"].reindex(don.index)
        ev = evaluer(don, ctrl, cfg.params, date_campagne=arrete)
        etat = Etat(don[["sensibilite", "critique_expert"]], ev.controles[["controle_id", "donnee_id",
                    "resultat_brut", "anteriorite", "poids", "inclus_note"]], cfg.params)
        # 4. gouvernance : couverture du lignage, registre des anomalies, journal
        couv = couverture_lignage(lig, flux, ev.controles, ev.donnees)
        registre = maj_registre(registre, camp.campagne, arrete, ev.controles, ev.donnees, couv)
        gouv = indicateurs_couverture(couv) | indicateurs_anomalies(registre, arrete)
        journal = entree_journal(camp.campagne, arrete, cfg.params, RACINE, cfg.referentiels,
                                 volumetries(con, arrete), nb_exec, len(ctrl), ev.indicateurs)
        sorties.append(ResultatCampagne(camp.campagne, arrete, ev, sens, sens.attrs["scr_ref"], ctrl, etat,
                                        couv, registre.copy(), gouv, journal))
    con.close()
    variation = analyse_variation(sorties[-2].etat, sorties[-1].etat) if len(sorties) >= 2 else pd.DataFrame()
    return sorties, variation
