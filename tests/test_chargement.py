"""Contrôles de chargement : règle de volumétrie (seuil 10 %, petites tables, tables vides) et exécution des requêtes."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chargement as ch  # noqa: E402
from lignes_anomalie import referentiel  # noqa: E402

BASE = Path(__file__).resolve().parents[1] / "data" / "btp_fictif.duckdb"


@pytest.mark.parametrize("prec,cour,attendu", [
    (6106, 6178, "Normal"),          # +1,2 % : variation normale du SI fictif
    (6000, 6600, "Normal"),          # +10,0 % : pile au seuil, pas d'alerte
    (6000, 6601, "À expliquer"),     # au-delà de 10 %
    (6000, 5399, "À expliquer"),     # baisse de plus de 10 % (chargement partiel)
    (3, 3, "Normal"),                # petite table inchangée
    (3, 2, "À expliquer"),           # petite table : un segment a disparu
    (6000, 0, "Bloquant"),           # table vide
    (6000, None, "Bloquant"),        # table absente
    (None, 500, "Sans référence"),   # premier trimestre
    (0, 500, "Sans référence"),      # vide au trimestre précédent (comme en SAS)
])
def test_regle_de_volumetrie(prec, cour, attendu):
    assert ch.statut_volume(prec, cour)[0] == attendu


def test_explication_en_francais():
    assert ch.statut_volume(6106, 6178)[1] == "Variation de +1,2 %, sous le seuil de 10 %."
    assert ch.statut_volume(6000, 5000)[1] == "Variation de -16,7 % : au-delà du seuil de 10 %."


def test_aucune_fausse_alerte_sur_le_si_fictif():
    if not BASE.exists():
        pytest.skip("base fictive absente")
    from qdd_s2.campagne import Config, lancer_campagnes
    camps, _ = lancer_campagnes(Config(base=BASE))
    v = ch.volumetrie({"journal": camps[1].journal}, {"journal": camps[0].journal})
    assert len(v) == 17 and (v["Statut"] == "Normal").all()
    exe = ch.execution(BASE, "2026-09-30", referentiel())
    assert len(exe) == 20 and (exe["Statut"] == "Exécuté").all()


def test_echec_technique_consigne_sans_arreter(tmp_path):
    import duckdb
    vide = tmp_path / "vide.duckdb"
    duckdb.connect(str(vide)).close()  # base sans aucune table
    exe = ch.execution(vide, "2026-09-30", referentiel())
    assert len(exe) == 20 and (exe["Statut"] == "Échec technique").all()
    assert exe["Message"].str.contains("CatalogException").all()
