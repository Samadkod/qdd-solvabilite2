"""Archive des données en défaut : lignes en anomalie figées par campagne, avant tout ajustement.

La notice ACPR QDD (point 37) demande que les données en défaut soient enregistrées et stockées avant de
faire l'objet d'ajustements. Les lignes en anomalie étaient jusqu'ici recalculées à la volée depuis la base ;
ce module les fige une fois par campagne dans archives/donnees_en_defaut/, avec un manifeste (nombre de lignes,
empreinte SHA-256, date d'archivage).

Une archive est immuable : archiver() ne réécrit jamais un fichier existant. Si le contenu recalculé diffère
de l'archive, il s'arrête en erreur au lieu d'écraser la donnée d'origine. verifier() recalcule les empreintes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pandas as pd

from lignes_anomalie import lignes

RACINE = Path(__file__).resolve().parent
DOSSIER = RACINE / "archives" / "donnees_en_defaut"
MANIFESTE = "manifeste.json"


def nom_fichier(campagne: str, arrete: str) -> str:
    return f"lignes_en_defaut_{campagne}_{arrete}.csv"


def contenu(base: Path | str, arrete: str) -> bytes:
    """Lignes en anomalie de l'arrêté, triées, en CSV (« ; », UTF-8, fins de ligne Unix) : octets stables."""
    df = lignes(base, arrete)
    df = df.sort_values(["controle", "maille", "objet", "valeurs"], kind="stable").reset_index(drop=True)
    buf = StringIO()
    df.to_csv(buf, sep=";", index=False, lineterminator="\n")
    return buf.getvalue().encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lire_manifeste(dossier: Path = DOSSIER) -> dict:
    p = dossier / MANIFESTE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"archives": []}


def archiver(base: Path | str, plan: pd.DataFrame, dossier: Path = DOSSIER) -> list[dict]:
    """Archive chaque campagne du plan qui ne l'est pas encore. Retourne les entrées créées."""
    dossier.mkdir(parents=True, exist_ok=True)
    man = lire_manifeste(dossier)
    connues = {a["fichier"]: a for a in man["archives"]}
    nouvelles = []
    for camp in plan.itertuples():
        nom = nom_fichier(camp.campagne, camp.date_arrete)
        data = contenu(base, camp.date_arrete)
        chemin = dossier / nom
        if chemin.exists() or nom in connues:
            if not chemin.exists() or sha256(chemin.read_bytes()) != sha256(data):
                raise RuntimeError(f"{nom} : la donnée recalculée diffère de l'archive ; archive conservée, "
                                   "rien n'est écrasé.")
            continue
        chemin.write_bytes(data)
        entree = {"campagne": camp.campagne, "arrete": camp.date_arrete, "fichier": nom,
                  "nb_lignes": data.count(b"\n") - 1, "sha256": sha256(data),
                  "archive_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        man["archives"].append(entree)
        nouvelles.append(entree)
    if nouvelles:
        (dossier / MANIFESTE).write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return nouvelles


def verifier(dossier: Path = DOSSIER) -> pd.DataFrame:
    """Une ligne par archive : empreinte recalculée égale (ou non) à celle du manifeste."""
    out = []
    for a in lire_manifeste(dossier)["archives"]:
        p = dossier / a["fichier"]
        recalc = sha256(p.read_bytes()) if p.exists() else None
        out.append(a | {"intacte": recalc == a["sha256"]})
    return pd.DataFrame(out, columns=["campagne", "arrete", "fichier", "nb_lignes", "sha256", "archive_le", "intacte"])


def archive(campagne: str, arrete: str, dossier: Path = DOSSIER) -> dict | None:
    """Entrée du manifeste pour une campagne, ou None si elle n'est pas archivée."""
    return next((a for a in lire_manifeste(dossier)["archives"]
                 if a["campagne"] == campagne and a["arrete"] == str(arrete)), None)
