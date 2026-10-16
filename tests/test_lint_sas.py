"""Le code SAS passe la vérification statique, et le vérificateur détecte bien les fautes."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lint_sas import verifier  # noqa: E402

SAS = Path(__file__).resolve().parents[1] / "sas"


def test_code_sas_propre():
    assert verifier(SAS) == []


@pytest.mark.parametrize("avant,apres,attendu", [
    ('date_realisation = "&arrete"d; format date_realisation date9.; run;',
     'date_realisation = "&arrete"d; format date_realisation date9.;', "sans RUN/QUIT"),
    ("    %end;\n    %else %put", "    %else %put", "%do non fermé"),
    ("%mesure_rapprochement(&id);", "%mesure_rapprochemen(&id);", "non défini"),
    ("max(0, 1 - &COEF * anteriorite);", "max(0, 1 - &COEF * anteriorite;", "parenthèses"),
])
def test_detection_des_fautes(tmp_path, avant, apres, attendu):
    d = tmp_path / "sas"
    shutil.copytree(SAS, d)
    f = d / "03_campagne.sas"
    t = f.read_text("utf-8")
    assert avant in t, avant
    f.write_text(t.replace(avant, apres, 1), "utf-8")
    assert any(attendu in e for e in verifier(d)), verifier(d)


def test_if_en_code_ouvert(tmp_path):
    d = tmp_path / "sas"
    shutil.copytree(SAS, d)
    (d / "zz.sas").write_text("%if 1 = 1 %then %put x;\n", "utf-8")
    assert any("code ouvert" in e for e in verifier(d))
