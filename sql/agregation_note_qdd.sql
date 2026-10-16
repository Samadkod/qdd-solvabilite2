-- =====================================================================
-- Note QDD agrégée en SQL pur (mémoire Motard, éq. 6, 22, 36, 10, 13)
-- Sans CTE ni fonction fenêtre : transposable tel quel en SAS PROC SQL
-- (remplacer $coef / $dscr par des macro-variables &coef. / &dscr.).
--
-- Entrées :
--   points(controle_id, donnee_id, poids, resultat_brut, anteriorite, inclus_note)
--   inclus_note = 0 : contrôle de restitution (QRT vs source), suivi à part, exclu de la note
--   donnees(donnee_id, sensibilite, critique)   -- critique : 1 / 0
-- Paramètres : $coef (coefficient de dégradation), $dscr (ΔSCR max)
-- =====================================================================
SELECT
    SUM(d.sensibilite * n.note)                         / SUM(d.sensibilite) AS note_qdd_agregee,
    SUM(d.sensibilite * (1 - $dscr / d.sensibilite))    / SUM(d.sensibilite) AS note_qdd_agregee_min,
    SUM(d.sensibilite * n.note_brute)                   / SUM(d.sensibilite) AS note_avant_degradation,
    COUNT(*)                                                                 AS nb_donnees_critiques
FROM donnees d
JOIN (SELECT donnee_id,
             SUM(poids * resultat_brut * CASE WHEN 1 - $coef * anteriorite > 0
                                              THEN 1 - $coef * anteriorite ELSE 0 END) / SUM(poids) AS note,
             SUM(poids * resultat_brut) / SUM(poids)                                         AS note_brute
      FROM points
      WHERE inclus_note = 1
      GROUP BY donnee_id) n
  ON n.donnee_id = d.donnee_id
WHERE d.critique = 1
