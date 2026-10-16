"""Assemble l'application HTML autonome : template + moteur JS + contenu + résultats JSON.

Usage : python scripts/construire_appli.py  ->  output/atelier_qdd_s2.html
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
GARDER_D = ["donnee_id", "libelle", "proprietaire", "sensibilite", "critique_expert", "valeur", "criteres_couverts",
            "note", "note_min", "statut"]
GARDER_C = ["controle_id", "libelle", "donnee_id", "maille", "famille", "criteres", "frequence", "etape", "responsable",
            "poids", "resultat_brut", "anteriorite", "resultat", "date_derniere_real", "inclus_note", "seuil_fixe"]


def main():
    data = json.loads((R / "output" / "resultats_campagnes.json").read_text(encoding="utf-8"))
    for c in data["campagnes"]:
        c["donnees"] = [{k: d.get(k) for k in GARDER_D} for d in c["donnees"]]
        c["controles"] = [{k: x.get(k) for k in GARDER_C} for x in c["controles"]]
        c.pop("axes", None)
        c.pop("couverture", None)
        c["registre"] = [{k: r.get(k) for k in ("anomalie_id", "type", "objet", "libelle", "gravite", "proprietaire",
                                                "echeance", "statut", "constat")} for r in c["registre"]]
    data["variation"] = [{"etape": v["etape"], "note": v["note"], "impact": v["impact"]} for v in data["variation"]]
    html = (R / "app" / "template.html").read_text(encoding="utf-8")
    html = html.replace("/*__MOTEUR__*/", (R / "app" / "moteur.js").read_text(encoding="utf-8"))
    html = html.replace("/*__CONTENU__*/", (R / "app" / "contenu.js").read_text(encoding="utf-8"))
    html = html.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = R / "output" / "atelier_qdd_s2.html"
    out.write_text(html, encoding="utf-8")
    (R / "app" / "atelier_qdd_s2.html").write_text(html, encoding="utf-8")  # version embarquée par Streamlit
    print(out, f"{len(html) // 1024} Ko")


if __name__ == "__main__":
    main()
