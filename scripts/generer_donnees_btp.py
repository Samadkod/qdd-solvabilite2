"""Génère un système d'information FICTIF d'assureur dommages BTP (DuckDB).

Aucune donnée réelle : montants, volumes et anomalies sont simulés (graine fixe)
pour illustrer la chaîne gestion -> entrepôt -> comptabilité -> actuariat.

Deux arrêtés : 30/06/2026 (campagne N-1) et 30/09/2026 (campagne N).
Anomalies injectées différemment selon l'arrêté pour rendre l'analyse de
variation parlante (ex. incident de migration entrepôt sur les DO en N).

Usage : python scripts/generer_donnees_btp.py [chemin.duckdb]
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

SEGMENTS = {  # nb contrats, prime moyenne (€), nb sinistres, provision moyenne (€)
    "RC_DECENNALE": (3200, 19_000, 2600, 100_000),
    "DOMMAGES_OUVRAGE": (1400, 18_000, 900, 78_000),
    "AUTO_FLOTTE": (1500, 10_000, 1400, 8_500),
}
ACTIVITES = ["4120A", "4120B", "4211Z", "4221Z", "4299Z", "4311Z", "4312A", "4321A",
             "4322A", "4322B", "4329A", "4331Z", "4332A", "4333Z", "4334Z", "4339Z",
             "4391A", "4391B", "4399A", "4399C"]  # codes NAF du BTP (nomenclature de référence)

# Taux d'anomalies par arrêté : (N-1, N)
INJ = {
    "dwh_contrat_manquant": {"RC_DECENNALE": (.002, .002), "DOMMAGES_OUVRAGE": (.004, .035), "AUTO_FLOTTE": (.001, .001)},
    "dwh_prime_alteree": (.010, .012),
    "prime_negative": (.003, .002),
    "doublon_contrat": (.001, .001),
    "activite_hors_nomenclature": (.020, .015),
    "sinistre_orphelin": (.004, .003),
    "provision_negative": (.002, .001),
    "survenance_apres_declaration": (.006, .004),
    "survenance_avant_effet": (.010, .009),
    "dwh_provision_alteree": {"RC_DECENNALE": (.010, .060), "DOMMAGES_OUVRAGE": (.008, .008), "AUTO_FLOTTE": (.005, .004)},
    "isin_manquant": (.010, .030),
    "cic_incoherent": (.010, .010),
}
ARRETES = {"2026-06-30": 0, "2026-09-30": 1}


def _taux(cle, seg, i):
    v = INJ[cle]
    return v[seg][i] if isinstance(v, dict) else v[i]


def generer(chemin: str | Path = "data/btp_fictif.duckdb", graine: int = 2026) -> Path:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists():
        chemin.unlink()
    tables = {k: [] for k in ["gestion_contrats", "dwh_contrats", "compta_primes", "gestion_sinistres",
                              "dwh_sinistres", "actuariat_inputs", "compta_reglements", "reassurance_traites",
                              "modele_parametres", "placements_depositaire", "placements_compta"]}
    for arrete, i in ARRETES.items():
        rng = np.random.default_rng(graine + i)
        croissance = 1 + 0.012 * i
        for seg, (nc, pm, ns, provm) in SEGMENTS.items():
            n = int(nc * croissance)
            cid = [f"{seg[:2]}{k:06d}" for k in range(n)]
            emise = rng.lognormal(np.log(pm), 0.6, n).round(2)
            acquise = (emise * rng.uniform(0.7, 1.0, n)).round(2)
            neg = rng.random(n) < _taux("prime_negative", seg, i)
            acquise[neg] = -acquise[neg]
            act = rng.choice(ACTIVITES, n)
            hors = rng.random(n) < _taux("activite_hors_nomenclature", seg, i)
            act = np.where(hors, rng.choice(["9999Z", "", "BTP"], n), act)
            effet = pd.Timestamp("2016-01-01") + pd.to_timedelta(rng.integers(0, 3700, n), "D")
            gc = pd.DataFrame({"arrete": arrete, "contrat_id": cid, "segment": seg, "code_activite": act,
                               "date_effet": effet, "prime_emise": emise, "prime_acquise": acquise})
            dup = gc.sample(frac=_taux("doublon_contrat", seg, i), random_state=graine + i)
            gc = pd.concat([gc, dup], ignore_index=True)
            tables["gestion_contrats"].append(gc)

            dw = gc.drop_duplicates("contrat_id")[["arrete", "contrat_id", "segment", "prime_acquise"]].copy()
            dw = dw[rng.random(len(dw)) >= _taux("dwh_contrat_manquant", seg, i)]
            alt = rng.random(len(dw)) < _taux("dwh_prime_alteree", seg, i)
            dw.loc[alt, "prime_acquise"] = (dw.loc[alt, "prime_acquise"] * rng.uniform(0.5, 1.5, alt.sum())).round(2)
            tables["dwh_contrats"].append(dw)

            tot = gc.drop_duplicates("contrat_id")["prime_acquise"].sum()
            tables["compta_primes"].append(pd.DataFrame({
                "arrete": [arrete], "segment": [seg], "prime_acquise": [round(tot * rng.normal(1, 0.004), 2)]}))

            m = int(ns * croissance)
            sid = [f"S{seg[:2]}{k:06d}" for k in range(m)]
            contrat = rng.choice(cid, m)
            orph = rng.random(m) < _taux("sinistre_orphelin", seg, i)
            contrat = np.where(orph, "INCONNU", contrat)
            surv = pd.Timestamp("2016-06-01") + pd.to_timedelta(rng.integers(0, 3700, m), "D")
            decl = surv + pd.to_timedelta(rng.integers(5, 400, m), "D")
            inv = rng.random(m) < _taux("survenance_apres_declaration", seg, i)
            surv = np.where(inv, decl + pd.to_timedelta(30, "D"), surv)
            eff = gc.drop_duplicates("contrat_id").set_index("contrat_id")["date_effet"]
            eff_s = pd.Series(contrat).map(eff)
            avant = (rng.random(m) < _taux("survenance_avant_effet", seg, i)) & eff_s.notna().values
            surv = np.where(avant, (eff_s - pd.to_timedelta(60, "D")).values, surv)
            prov = rng.lognormal(np.log(provm), 1.0, m).round(2)
            pneg = rng.random(m) < _taux("provision_negative", seg, i)
            prov[pneg] = -prov[pneg]
            regl = (rng.lognormal(np.log(provm * 0.6), 1.0, m)).round(2)
            gs = pd.DataFrame({"arrete": arrete, "sinistre_id": sid, "contrat_id": contrat, "segment": seg,
                               "date_survenance": pd.to_datetime(surv), "date_declaration": decl,
                               "reglements_cumules": regl, "provision_dossier": prov})
            tables["gestion_sinistres"].append(gs)

            ds = gs[["arrete", "sinistre_id", "segment", "provision_dossier", "reglements_cumules"]].copy()
            a2 = rng.random(m) < _taux("dwh_provision_alteree", seg, i)
            ds.loc[a2, "provision_dossier"] = (ds.loc[a2, "provision_dossier"] * rng.uniform(0.2, 0.6, a2.sum())).round(2)
            tables["dwh_sinistres"].append(ds)
            tables["actuariat_inputs"].append(pd.DataFrame({
                "arrete": [arrete], "segment": [seg],
                "provision_dossier_total": [round(ds["provision_dossier"].sum() * rng.normal(1, 0.003), 2)],
                "reglements_total": [round(ds["reglements_cumules"].sum(), 2)]}))
            tables["compta_reglements"].append(pd.DataFrame({
                "arrete": [arrete], "segment": [seg],
                "reglements": [round(gs["reglements_cumules"].sum() * rng.normal(1, 0.006), 2)]}))
            tx = {"RC_DECENNALE": .25, "DOMMAGES_OUVRAGE": .15, "AUTO_FLOTTE": .10}[seg]
            tables["reassurance_traites"].append(pd.DataFrame({"arrete": [arrete], "segment": [seg], "taux_cession": [tx]}))
            tables["modele_parametres"].append(pd.DataFrame({"arrete": [arrete], "segment": [seg],
                                                             "taux_cession": [tx if seg != "DOMMAGES_OUVRAGE" else tx * 1.04]}))

        # Placements (look-through simplifié) : actions et obligations
        k = 420
        classe = np.where(np.arange(k) < 60, "ACTIONS", "OBLIGATIONS")
        isin = [f"FR{rng.integers(10**9, 10**10)}{rng.integers(0, 10)}" for _ in range(k)]
        miss = rng.random(k) < _taux("isin_manquant", "", i)
        isin = np.where(miss, rng.choice(["", "N/A", "FR12"], k), isin)
        cic = np.where(classe == "ACTIONS", "FR31", "FR12")
        bad = rng.random(k) < _taux("cic_incoherent", "", i)
        cic = np.where(bad, np.where(classe == "ACTIONS", "FR12", "FR31"), cic)
        vm = np.where(classe == "ACTIONS", rng.lognormal(np.log(6.5e5), .5, k), rng.lognormal(np.log(9.0e5), .4, k)).round(2)
        vm = vm * (1 + 0.01 * i)
        aid = [f"A{j:05d}" for j in range(k)]
        tables["placements_depositaire"].append(pd.DataFrame({"arrete": arrete, "actif_id": aid, "classe": classe,
                                                               "isin": isin, "cic": cic, "valeur_marche": vm}))
        vc = vm * np.where(rng.random(k) < 0.02, rng.uniform(0.9, 1.1, k), 1.0)
        tables["placements_compta"].append(pd.DataFrame({"arrete": arrete, "actif_id": aid, "valeur_marche": vc.round(2)}))

    tables.update(_generer_qrt(tables, graine))

    con = duckdb.connect(str(chemin))
    for nom, morceaux in tables.items():
        df = pd.concat(morceaux, ignore_index=True)
        con.register("tmp", df)
        con.execute(f"CREATE TABLE {nom} AS SELECT * FROM tmp")
        con.unregister("tmp")
    con.execute("CREATE TABLE ref_activites_btp AS SELECT unnest($a) AS code_activite", {"a": ACTIVITES})
    con.close()
    return chemin


FACTEUR_BE = {"RC_DECENNALE": 1.18, "DOMMAGES_OUVRAGE": 1.09, "AUTO_FLOTTE": 1.03}  # dossier/dossier -> BE (IBNR, frais)


def _generer_qrt(tables: dict, graine: int) -> dict:
    """États QRT SIMPLIFIÉS (contenu inspiré de S.02.01, S.05.01, S.06.02, S.17.01, S.19.01 ;
    pas la taxonomie EIOPA). Générés après le SI, avec un RNG distinct : les tables
    existantes et leurs résultats ne changent pas.

    Les états sont exacts par construction, sauf UNE anomalie injectée en N : le BE
    dommages-ouvrage de S.17.01 provient d'une version antérieure du calcul (écart d'environ
    -3 % avec l'outil de provisionnement).
    """
    cat = {k: pd.concat(v, ignore_index=True) for k, v in tables.items()}
    out = {k: [] for k in ["actuariat_be", "qrt_s0501", "qrt_s1701", "qrt_s1901_diagonale",
                           "qrt_s0602", "qrt_s0201"]}
    for arrete, i in ARRETES.items():
        act = cat["actuariat_inputs"].query("arrete == @arrete").set_index("segment")
        cp = cat["compta_primes"].query("arrete == @arrete").set_index("segment")["prime_acquise"]
        ds = cat["dwh_sinistres"].query("arrete == @arrete")
        gs = cat["gestion_sinistres"].query("arrete == @arrete")
        for seg in SEGMENTS:
            be = round(act.loc[seg, "provision_dossier_total"] * FACTEUR_BE[seg], 2)
            out["actuariat_be"].append({"arrete": arrete, "segment": seg, "be_sinistres_brut": be})
            be_qrt = be * (0.97 if (i == 1 and seg == "DOMMAGES_OUVRAGE") else 1.0)
            out["qrt_s1701"].append({"arrete": arrete, "segment": seg, "be_sinistres_brut": round(be_qrt, 2)})
            out["qrt_s0501"].append({"arrete": arrete, "segment": seg,
                                     "primes_acquises_brutes": round(cp[seg], 2)})
            # dernière diagonale du triangle de paiements cumulés, construite depuis l'entrepôt
            g = gs[gs.segment == seg].assign(annee_survenance=lambda x: pd.to_datetime(x.date_survenance).dt.year)
            g = g.merge(ds[["sinistre_id", "reglements_cumules"]].rename(columns={"reglements_cumules": "r_dwh"}),
                        on="sinistre_id")
            diag = g.groupby("annee_survenance")["r_dwh"].sum().round(2)
            for a, v in diag.items():
                out["qrt_s1901_diagonale"].append({"arrete": arrete, "segment": seg, "annee_survenance": int(a),
                                                   "paiements_cumules": float(v)})
        pc = cat["placements_compta"].query("arrete == @arrete")
        pdp = cat["placements_depositaire"].query("arrete == @arrete")[["actif_id", "classe", "isin", "cic"]]
        s0602 = pc.merge(pdp, on="actif_id")[["arrete", "actif_id", "classe", "isin", "cic", "valeur_marche"]]
        out["qrt_s0602"].append(s0602)
        tot = s0602.groupby("classe")["valeur_marche"].sum()
        for cl, v in tot.items():
            out["qrt_s0201"].append({"arrete": arrete, "poste": f"PLACEMENTS_{cl}",
                                     "montant": round(v, 2)})
    res = {}
    for k, v in out.items():
        res[k] = [pd.concat(v, ignore_index=True)] if isinstance(v[0], pd.DataFrame) else [pd.DataFrame(v)]
    return res


if __name__ == "__main__":
    print(generer(sys.argv[1] if len(sys.argv) > 1 else "data/btp_fictif.duckdb"))
