// Parité JS / Python : node tests/parite_js.mjs output/resultats_campagnes.json
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const QDD = require("../app/moteur.js");

const data = JSON.parse(readFileSync(process.argv[2], "utf8"));
let ko = 0;
for (const camp of data.campagnes) {
  const pp = camp.parametres;
  const p = { seuil: pp.seuil_significativite, mode: pp.mode_tolerance, dscr: pp.delta_scr_max,
    tol: pp.tolerance_globale, coef: pp.coef_degradation, degradation: pp.methode_degradation, marge: pp.marge_alerte };
  const ev = QDD.evaluer(camp.donnees, camp.controles, p);
  for (const k of ["note", "note_min", "note_avant_degradation", "taux_validation", "taux_conformite_controles",
                   "nb_donnees_critiques", "nb_donnees_hors_tolerance", "anteriorite_moyenne", "taux_conformite_restitutions"]) {
    const a = ev.indicateurs[k], b = camp.indicateurs[k];
    const ok = Math.abs(a - b) < 1e-10;
    if (!ok) ko++;
    console.log(`${camp.campagne} ${k.padEnd(28)} js=${a.toFixed(8)} py=${Number(b).toFixed(8)} ${ok ? "OK" : "ÉCART"}`);
  }
  for (const c of camp.controles) {
    const j = ev.controles.find((x) => x.controle_id === c.controle_id);
    if ((c.statut ?? null) !== (j.statut ?? null)) { ko++; console.log("statut contrôle diff", c.controle_id, c.statut, j.statut); }
  }
  for (const d of camp.donnees) {
    const j = ev.donnees.find((x) => x.donnee_id === d.donnee_id);
    if (d.statut !== j.statut) { ko++; console.log("statut diff", d.donnee_id, d.statut, j.statut); }
  }
  for (const r of QDD.parAxe(ev, "maille")) {
    const py = camp.axes.maille.find((x) => x.maille === r.modalite);
    if (Math.abs(py.note - r.note) > 1e-10) { ko++; console.log("axe diff", r.modalite, r.note, py.note); }
  }
}
console.log(ko ? `${ko} écart(s)` : "PARITÉ OK");
process.exit(ko ? 1 : 0);
