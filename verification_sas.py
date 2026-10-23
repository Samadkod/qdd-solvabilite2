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


def resume(df: pd.DataFrame, attendues: Path = ATTENDUES) -> dict:
    """Bilan, et contrôle que le fichier correspond à la version actuelle des valeurs attendues."""
    ref = pd.read_csv(attendues, sep=";")
    cle = ["campagne", "indicateur"]
    m = ref.merge(df[cle + ["valeur_attendue"]], on=cle, how="left", suffixes=("", "_fichier"))
    a_jour = bool(len(df) == len(ref) and m["valeur_attendue_fichier"].notna().all()
                  and ((m["valeur_attendue"] - m["valeur_attendue_fichier"]).abs() < 1e-9).all())
    ok = int((df["verdict"].str.upper() == "OK").sum())
    return {"n": len(df), "ok": ok, "ecarts": len(df) - ok,
            "ecart_max": float(df["ecart"].max(skipna=True)) if len(df) else float("nan"),
            "a_jour": a_jour,
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
    if r["ecarts"] == 0 and r["a_jour"]:
        st.success("Parité SAS / Python : toutes les valeurs sont identiques, à la tolérance près.",
                   icon=":material/verified:")
    elif not r["a_jour"]:
        st.warning("Ce résultat a été produit avec d'anciennes valeurs attendues : relancez lancer_qdd.sas avec la "
                   "version actuelle du projet.", icon=":material/history:")
    else:
        st.error(f"{r['ecarts']} valeur(s) en écart : voir les lignes ÉCART ou MANQUANT ci-dessous.",
                 icon=":material/error:")
    st.caption(f"Source : {'fichier chargé' if televerse is not None else 'resultats_sas/verification_sas.csv'}"
               + (f" · {r['version_sas']}" if r["version_sas"] else ""))
    vue = df[COLONNES].sort_values(["verdict", "campagne", "indicateur"], ascending=[False, True, True])
    st.dataframe(vue, hide_index=True, width="stretch",
                 column_config={"valeur_attendue": st.column_config.NumberColumn("Python (attendu)", format="%.10f"),
                                "valeur_sas": st.column_config.NumberColumn("SAS", format="%.10f"),
                                "ecart": st.column_config.NumberColumn("Écart", format="%.2e")})
