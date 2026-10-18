"""Exercices SAS : chaque énoncé a son corrigé dans le fichier SAS, et les résultats attendus sont stables."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import exercices_sas as ex  # noqa: E402


def test_un_corrige_par_exercice():
    code = ex.corriges()
    assert list(code) == ["E00"] + [e["id"] for e in ex.EXERCICES]
    for e in ex.EXERCICES:
        assert code[e["id"]][0] == e["titre"], e["id"]  # même titre dans l'application et dans le SAS
        assert code[e["id"]][1].strip()


def test_resultats_attendus():
    r = ex.resultats_attendus()
    assert r["E01"]["nb_lignes"].tolist() == [6106, 6178]
    assert r["E02"]["nb_contrats"].iloc[0] == 3241
    assert r["E03"]["nb_sinistres"].tolist() == [42, 4471, 444]
    assert r["E06"]["contrat_id"].tolist() == ["AU000277", "AU001019", "DO000609", "RC001015", "RC001317",
                                               "RC002279"]
    assert r["E07"]["nb_orphelins"].iloc[0] == 12
    assert r["E08"]["nb_absents"].iloc[0] == 54
    # un code activité vide est hors nomenclature (comportement SAS)
    assert dict(zip(r["E09"]["code_activite"], r["E09"]["nb_contrats"])) == {"BTP": 33, "9999Z": 32, "(vide)": 24}
    assert dict(zip(r["E10"]["longueur"], r["E10"]["nb_placements"])) == {0: 8, 3: 3, 4: 3, 12: 406}
    assert r["E11"]["nb_doublons"].tolist() == [6, 0, 0]
    # la macro de E12 retrouve exactement les écarts de E05
    e5 = r["E05"].set_index("segment")["ecart_relatif"]
    e12 = r["E12"].set_index("segment")["ecart_relatif"]
    assert (e5.sort_index() - e12.sort_index()).abs().max() < 1e-12
    assert r["E13"]["nb_anomalies"].tolist() == [6, 13, 16, 6, 12, 54]


def test_formatage_francais():
    import pandas as pd
    f = ex._formater(pd.DataFrame({"montant": [1234567.891], "ecart_relatif": [-0.0038369]}))
    assert f.iloc[0].tolist() == ["1 234 567,89", "-0,38 %"]


def test_isin_fictifs_valides():
    """ISIN fictifs : 12 caractères et clé de contrôle ISO 6166 juste (sauf valeurs manquantes voulues)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generer_donnees_btp import _cle_isin
    for reel in ["US0378331005", "FR0000120271", "FR0000131104", "DE0007164600", "GB0002634946"]:
        assert _cle_isin(reel[:11]) == reel[11]
    import pandas as pd
    p = pd.read_csv(ex.DEMO / "placements_depositaire.csv", sep=";", dtype=str, keep_default_na=False)
    bons = p[p["isin"].str.len() == 12]["isin"]
    assert len(bons) == 821 and all(_cle_isin(i[:11]) == i[11] for i in bons)
    assert set(p.loc[p["isin"].str.len() != 12, "isin"]) == {"", "N/A", "FR12"}
