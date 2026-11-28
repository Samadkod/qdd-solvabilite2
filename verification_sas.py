"""Page « Vérification SAS » : la même campagne calculée par la chaîne SAS, comparée valeur par valeur au moteur Python.

Source : le fichier verification_sas.csv écrit par sas/98_verifier.sas (dans &SORTIE) après lancer_qdd.sas.
Le dernier fichier reçu est versionné dans resultats_sas/ ; un fichier plus récent peut être chargé dans la page
(le temps de la session). Données 100 % fictives : aucune donnée d'entreprise ne doit transiter par ici.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent
FICHIER = RACINE / "resultats_sas" / "verification_sas.csv"
ATTENDUES = RACINE / "sas" / "donnees_demo" / "valeurs_attendues.csv"
COLONNES = ["campagne", "indicateur", "valeur_attendue", "valeur_sas", "ecart", "verdict"]
TOLERANCE = 1e-6  # celle de 98_verifier.sas


def charger(source) -> pd.DataFrame:
    """source : chemin ou fichier téléversé. Contrôle le format avant tout affichage."""
    df = pd.read_csv(source, sep=";", encoding="utf-8")
    df.columns = [c.strip().lower() for c in df.columns]
    manquantes = [c for c in COLONNES if c not in df.columns]
    if manquantes:
        raise ValueError(f"Colonnes absentes : {', '.join(manquantes)}. Ce fichier ne vient pas de 98_verifier.sas.")
    for c in ("valeur_attendue", "valeur_sas", "ecart"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def recalculer(df: pd.DataFrame, attendues: Path = ATTENDUES) -> pd.DataFrame:
    """Recalcule l'écart et le verdict côté Python, à partir de la valeur SAS et de la référence actuelle du moteur :
    le verdict écrit par SAS n'est pas cru sur parole. Une ligne par valeur de référence."""
    ref = pd.read_csv(attendues, sep=";")
    cle = ["campagne", "indicateur"]
    sas = df.assign(campagne=df["campagne"].astype(str).str.upper(), indicateur=df["indicateur"].astype(str).str.upper())
    m = ref.assign(_c=ref["campagne"].str.upper(), _i=ref["indicateur"].str.upper()).merge(
        sas[cle + ["valeur_sas", "verdict"]].rename(columns={"campagne": "_c", "indicateur": "_i", "verdict": "verdict_sas"}),
        on=["_c", "_i"], how="left").drop(columns=["_c", "_i"])
    m["ecart_recalcule"] = (m["valeur_attendue"] - m["valeur_sas"]).abs()
    m["verdict_recalcule"] = "ÉCART"
    m.loc[m["ecart_recalcule"] < TOLERANCE, "verdict_recalcule"] = "OK"
    m.loc[m["valeur_sas"].isna(), "verdict_recalcule"] = "MANQUANT"
    m["accord"] = m["verdict_sas"].fillna("MANQUANT").str.upper().eq("OK") == m["verdict_recalcule"].eq("OK")
    return m


def resume(df: pd.DataFrame, attendues: Path = ATTENDUES) -> dict:
    """Bilan recalculé côté Python, contrôle que le fichier suit les valeurs attendues actuelles, et désaccords avec
    le verdict écrit par SAS."""
    ref = pd.read_csv(attendues, sep=";")
    cle = ["campagne", "indicateur"]
    m = ref.merge(df[cle + ["valeur_attendue"]], on=cle, how="left", suffixes=("", "_fichier"))
    a_jour = bool(len(df) == len(ref) and m["valeur_attendue_fichier"].notna().all()
                  and ((m["valeur_attendue"] - m["valeur_attendue_fichier"]).abs() < 1e-9).all())
    rc = recalculer(df, attendues)
    ok = int((rc["verdict_recalcule"] == "OK").sum())
    return {"n": len(rc), "ok": ok, "ecarts": len(rc) - ok,
            "ecart_max": float(rc["ecart_recalcule"].max(skipna=True)) if len(rc) else float("nan"),
            "desaccords": int((~rc["accord"]).sum()), "detail": rc, "a_jour": a_jour,
            "execution": str(df["execution"].iloc[0]) if "execution" in df and len(df) else None,
            "version_sas": str(df["version_sas"].iloc[0]) if "version_sas" in df and len(df) else None}


def afficher() -> None:
    import streamlit as st

    st.markdown("La chaîne SAS (`sas/lancer_qdd.sas`) refait les trois campagnes sur les mêmes données fictives. "
                "Chaque valeur est comparée à celle du moteur Python : c'est la preuve que les deux versions calculent "
                "la même chose.")
    televerse = st.file_uploader("Charger un résultat plus récent (verification_sas.csv)", type="csv",
                                 help="Après lancer_qdd.sas, le fichier est dans qdd-s2/sas/sorties/ : clic droit, "
                                      "Télécharger. Il n'est gardé que le temps de la session.")
    source = televerse if televerse is not None else (FICHIER if FICHIER.exists() else None)
    if source is None:
        st.info("Aucun résultat SAS enregistré. Lancez `lancer_qdd.sas` sur SAS OnDemand puis chargez "
                "`sas/sorties/verification_sas.csv` ci-dessus.")
        return
    try:
        df = charger(source)
    except Exception as e:  # noqa: BLE001 — message clair plutôt qu'une trace Python
        st.error(f"Fichier illisible : {e}")
        return
    r = resume(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Valeurs identiques", f"{r['ok']} sur {r['n']}")
    c2.metric("Écarts", r["ecarts"])
    c3.metric("Plus grand écart", f"{r['ecart_max']:.1e}".replace(".", ","), help=f"Tolérance : {TOLERANCE:.0e}")
    c4.metric("Exécution SAS", (r["execution"] or "—").replace("T", " ")[:16])
    if r["desaccords"]:
        st.error(f"{r['desaccords']} valeur(s) où le verdict écrit par SAS ne correspond pas à l'écart recalculé ici : "
                 "le fichier n'est pas fiable, relancez lancer_qdd.sas.", icon=":material/gpp_bad:")
    if r["ecarts"] == 0 and r["a_jour"] and not r["desaccords"]:
        st.success("Parité SAS / Python : toutes les valeurs sont identiques, à la tolérance près.",
                   icon=":material/verified:")
    elif not r["a_jour"]:
        st.warning("Ce résultat a été produit avec d'anciennes valeurs attendues : relancez lancer_qdd.sas avec la "
                   "version actuelle du projet.", icon=":material/history:")
    else:
        st.error(f"{r['ecarts']} valeur(s) en écart : voir les lignes ÉCART ou MANQUANT ci-dessous.",
                 icon=":material/error:")
    st.caption("Écarts et verdicts recalculés ici, à partir des valeurs SAS et de la référence actuelle du moteur "
               f"(tolérance {TOLERANCE:.0e}) ; le verdict écrit par SAS sert seulement de contrôle croisé.")
    st.caption(f"Source : {'fichier chargé' if televerse is not None else 'resultats_sas/verification_sas.csv'}"
               + (f" · {r['version_sas']}" if r["version_sas"] else ""))
    vue = r["detail"].sort_values(["verdict_recalcule", "campagne", "indicateur"], ascending=[False, True, True])
    st.dataframe(vue[["campagne", "indicateur", "valeur_attendue", "valeur_sas", "ecart_recalcule",
                      "verdict_recalcule", "verdict_sas"]], hide_index=True, width="stretch",
                 column_config={"campagne": "Campagne", "indicateur": "Indicateur",
                                "valeur_attendue": st.column_config.NumberColumn("Python (attendu)", format="%.10f"),
                                "valeur_sas": st.column_config.NumberColumn("SAS", format="%.10f"),
                                "ecart_recalcule": st.column_config.NumberColumn("Écart recalculé", format="%.2e"),
                                "verdict_recalcule": "Verdict recalculé", "verdict_sas": "Verdict écrit par SAS"})
