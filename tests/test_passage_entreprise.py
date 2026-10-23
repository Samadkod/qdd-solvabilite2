"""Pages « Mise en place en entreprise » et « Visite » : elles suivent le code."""
from passage_entreprise import OU_TROUVER, tables_attendues
from visite import USAGES


def test_tables_attendues_suivent_l_import_sas():
    t = tables_attendues()
    assert len(t) == 18 and set(t["Table attendue (SI.)"]) == set(OU_TROUVER)
    sin = t.set_index("Table attendue (SI.)").loc["gestion_sinistres", "Colonnes"]
    assert sin == ("arrete, sinistre_id, contrat_id, segment, date_survenance, date_declaration, "
                   "reglements_cumules, provision_dossier")


def test_visite_couvre_toutes_les_pages():
    import ast
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(encoding="utf-8")
    noeud = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assign)
                 and getattr(n.targets[0], "id", None) == "PAGES")
    assert {k.value for k in noeud.value.keys} == set(USAGES)
