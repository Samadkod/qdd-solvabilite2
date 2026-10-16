-- C10 | Cohérence | Code activité BTP hors nomenclature de référence
-- Critères : pertinence | Fréquence : semestrielle
SELECT 'TOUS' AS maille,
       SUM(CASE WHEN r.code_activite IS NULL THEN 1 ELSE 0 END) AS n_anomalies,
       COUNT(*) AS n_elements,
       NULL AS montant_anomalies, NULL AS montant_total
FROM gestion_contrats g
LEFT JOIN ref_activites_btp r ON r.code_activite = g.code_activite
WHERE g.arrete = $arrete
