"""Page « Vérification SAS » : lecture du fichier écrit par sas/98_verifier.sas et bilan."""
import pandas as pd
import pytest

from verification_sas import ATTENDUES, charger, resume


def _fichier(tmp_path, decale=0.0, retirer=0):
    ref = pd.read_csv(ATTENDUES, sep=";")
    df = ref.assign(valeur_sas=ref["valeur_attendue"] + decale, ecart=abs(decale),
                    verdict="OK" if abs(decale) < 1e-6 else "ÉCART",
                    execution="2026-10-23T13:10:50", version_sas="9.04.01M9P060525")
    df = df.iloc[retirer:]
    p = tmp_path / "verification_sas.csv"
    df.to_csv(p, sep=";", index=False)
    return p


def test_bilan_parite(tmp_path):
    r = resume(charger(_fichier(tmp_path, 3e-7)))
    assert (r["n"], r["ok"], r["ecarts"], r["a_jour"]) == (59, 59, 0, True)


def test_ecarts_detectes(tmp_path):
    r = resume(charger(_fichier(tmp_path, 1e-3)))
    assert r["ecarts"] == 59


def test_fichier_ancien_signale(tmp_path):
    """Un fichier produit avec une autre version des valeurs attendues (ici 43 lignes) n'est pas « à jour »."""
    assert resume(charger(_fichier(tmp_path, retirer=16)))["a_jour"] is False


def test_format_refuse(tmp_path):
    p = tmp_path / "autre.csv"
    p.write_text("a;b\n1;2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="98_verifier"):
        charger(p)
