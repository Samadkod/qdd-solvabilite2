-- C07 | Cohérence | Sinistre survenu avant la date d'effet du contrat
-- Critères : pertinence | Fréquence : semestrielle
SELECT 'TOUS' AS maille,
       SUM(CASE WHEN s.date_survenance < c.date_effet THEN 1 ELSE 0 END) AS n_anomalies,
       COUNT(*) AS n_elements,
       SUM(CASE WHEN s.date_survenance < c.date_effet THEN ABS(s.provision_dossier) ELSE 0 END) AS montant_anomalies,
       SUM(ABS(s.provision_dossier)) AS montant_total
FROM gestion_sinistres s
JOIN (SELECT contrat_id, MIN(date_effet) AS date_effet FROM gestion_contrats WHERE arrete = $arrete GROUP BY contrat_id) c
  ON c.contrat_id = s.contrat_id
WHERE s.arrete = $arrete
