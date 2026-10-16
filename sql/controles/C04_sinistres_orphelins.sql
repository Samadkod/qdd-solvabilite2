-- C04 | Cohérence | Sinistres sans contrat rattaché (orphelins)
-- Critères : exhaustivité, pertinence | Fréquence : trimestrielle
SELECT s.segment AS maille,
       SUM(CASE WHEN c.contrat_id IS NULL THEN 1 ELSE 0 END) AS n_anomalies,
       COUNT(*) AS n_elements,
       SUM(CASE WHEN c.contrat_id IS NULL THEN ABS(s.provision_dossier) ELSE 0 END) AS montant_anomalies,
       SUM(ABS(s.provision_dossier)) AS montant_total
FROM gestion_sinistres s
LEFT JOIN (SELECT DISTINCT contrat_id FROM gestion_contrats WHERE arrete = $arrete) c ON c.contrat_id = s.contrat_id
WHERE s.arrete = $arrete
GROUP BY s.segment
