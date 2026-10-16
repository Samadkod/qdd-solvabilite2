/* Moteur QDD en JavaScript — miroir de qdd_s2/moteur.py (parité testée). */
(function (root) {
  const FREQ_MOIS = { M: 1, T: 3, S: 6, A: 12 };

  function degrader(r, ant, coef, methode) {
    return methode === "composee" ? r * Math.pow(1 - coef, ant) : r * Math.max(0, 1 - coef * ant);
  }

  function ecartMemoire(ref, comp) {
    if (ref !== 0) return Math.abs(comp / ref - 1);
    return comp === ref ? 0 : 1;
  }
  function ecartSymetrique(a, b) {
    const m = Math.max(Math.abs(a), Math.abs(b));
    return m === 0 ? 0 : Math.min(1, Math.abs(a - b) / m);
  }
  function mesureRapprochement(vals, methode) {
    const f = methode === "symetrique" ? ecartSymetrique : ecartMemoire;
    let m = 0;
    for (let k = 0; k < vals.length; k++)
      for (let j = 0; j < vals.length; j++) if (k !== j) m = Math.max(m, f(vals[k], vals[j]));
    return m;
  }

  function moyPond(items, val, poids) {
    let s = 0, w = 0;
    for (const it of items) { s += val(it) * poids(it); w += poids(it); }
    return w > 0 ? s / w : NaN;
  }

  /* donnees : [{donnee_id, sensibilite, critique_expert(true/false/null)}]
     controles : [{controle_id, donnee_id, poids, resultat_brut, anteriorite, criteres, ...}]
     p : {seuil, mode:"donnee"|"globale", dscr, tol, coef, degradation:"simple"|"composee", marge} */
  function evaluer(donnees, controles, p) {
    const D = donnees.map((d) => {
      let crit = d.sensibilite >= p.seuil;
      if (d.critique_expert === true || d.critique_expert === false) crit = d.critique_expert;
      return Object.assign({}, d, { critique: crit });
    });
    const crit = D.filter((d) => d.critique);
    const S = crit.length ? crit.reduce((a, d) => a + d.sensibilite, 0) / crit.length : 0;
    const coherent = p.mode === "donnee" ? p.dscr < p.seuil : p.tol < p.seuil / S;
    for (const d of D) {
      d.tolerance = d.critique ? (p.mode === "donnee" ? p.dscr / d.sensibilite : (p.tol * S) / d.sensibilite) : NaN;
      d.note_min = 1 - d.tolerance;
    }
    const byId = Object.fromEntries(D.map((d) => [d.donnee_id, d]));
    const C = controles.map((c) => {
      const r = degrader(c.resultat_brut, c.anteriorite, p.coef, p.degradation);
      const d = byId[c.donnee_id];
      const critique = !!(d && d.critique);
      const inclus = c.inclus_note === undefined || c.inclus_note === null ? true : !!Number(c.inclus_note);
      const fixe = c.seuil_fixe === undefined || c.seuil_fixe === null ? null : Number(c.seuil_fixe);
      const evalue = critique || fixe !== null;
      const seuil = fixe !== null ? fixe : (critique ? d.note_min : NaN);
      /* seuil fixe (contrôle de restitution QRT) : binaire, pas de zone orange */
      const st = !evalue ? null : (fixe !== null ? (r >= seuil ? "vert" : "rouge") : statut(r, seuil, p.marge));
      return Object.assign({}, c, { resultat: r, critique, inclus_note: inclus, seuil,
        conforme: evalue ? r >= seuil : null, statut: st });
    });
    const CN = C.filter((c) => c.inclus_note);
    for (const d of D) {
      const cs = CN.filter((c) => c.donnee_id === d.donnee_id);
      d.nb_controles = cs.length;
      d.note = moyPond(cs, (c) => c.resultat, (c) => c.poids);
      d.note_avant_degradation = moyPond(cs, (c) => c.resultat_brut, (c) => c.poids);
      d.statut = d.critique ? statut(d.note, d.note_min, p.marge) : null;
    }
    const agg = agreger(D, CN);
    const cc = CN.filter((c) => c.critique);
    const cres = C.filter((c) => !c.inclus_note && c.conforme !== null);
    const critd = D.filter((d) => d.critique);
    return {
      donnees: D, controles: C, S, coherent,
      indicateurs: {
        note: agg.note, note_min: agg.note_min, ecart_objectif: agg.note - agg.note_min,
        note_avant_degradation: agg.note_brute, degradation_moyenne: 1 - agg.note / agg.note_brute,
        nb_donnees_critiques: critd.length, sensibilite_moyenne: S,
        taux_validation: cc.filter((c) => c.anteriorite === 0).length / cc.length,
        anteriorite_moyenne: cc.reduce((a, c) => a + c.anteriorite, 0) / cc.length,
        taux_conformite_controles: cc.filter((c) => c.conforme).length / cc.length,
        nb_donnees_hors_tolerance: critd.filter((d) => d.note < d.note_min).length,
        taux_conformite_restitutions: cres.length ? cres.filter((c) => c.conforme).length / cres.length : NaN,
      },
    };
  }

  function agreger(D, C) {
    const crit = new Set(D.filter((d) => d.critique).map((d) => d.donnee_id));
    const groupes = {};
    for (const c of C) if (crit.has(c.donnee_id) && c.inclus_note !== false) (groupes[c.donnee_id] = groupes[c.donnee_id] || []).push(c);
    const ids = Object.keys(groupes);
    const byId = Object.fromEntries(D.map((d) => [d.donnee_id, d]));
    const notes = ids.map((id) => ({ d: byId[id],
      n: moyPond(groupes[id], (c) => c.resultat, (c) => c.poids),
      nb: moyPond(groupes[id], (c) => c.resultat_brut, (c) => c.poids) }));
    return {
      note: moyPond(notes, (x) => x.n, (x) => x.d.sensibilite),
      note_brute: moyPond(notes, (x) => x.nb, (x) => x.d.sensibilite),
      note_min: moyPond(notes, (x) => x.d.note_min, (x) => x.d.sensibilite),
      nb: ids.length,
    };
  }

  function parAxe(ev, axe) {
    const mod = {};
    for (const c of ev.controles) {
      for (const m of String(c[axe]).split(",").map((s) => s.trim()))
        (mod[m] = mod[m] || []).push(c);
    }
    return Object.entries(mod).map(([m, cs]) => {
      const a = agreger(ev.donnees, cs);
      const cc = cs.filter((c) => c.critique && c.inclus_note !== false);
      return { modalite: m, note: a.note, note_min: a.note_min, nb_donnees: a.nb, nb_controles: cc.length,
        taux_conformite: cc.length ? cc.filter((c) => c.conforme).length / cc.length : NaN };
    }).filter((r) => r.nb_donnees > 0);
  }

  function statut(note, mini, marge) {
    if (!(isFinite(note) && isFinite(mini))) return null;
    return note >= mini ? "vert" : note >= mini - marge ? "orange" : "rouge";
  }

  root.QDD = { evaluer, parAxe, degrader, mesureRapprochement, ecartMemoire, ecartSymetrique, statut, FREQ_MOIS };
  if (typeof module !== "undefined") module.exports = root.QDD;
})(typeof window !== "undefined" ? window : globalThis);
