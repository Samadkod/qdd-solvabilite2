-- C05 | Cohérence | Provisions dossier/dossier négatives
-- Critères : exactitude | Fréquence : trimestrielle
SELECT segment AS maille,
       SUM(CASE WHEN provision_dossier < 0 THEN 1 ELSE 0 END) AS n_anomalies,
       COUNT(*) AS n_elements,
       SUM(CASE WHEN provision_dossier < 0 THEN ABS(provision_dossier) ELSE 0 END) AS montant_anomalies,
       SUM(ABS(provision_dossier)) AS montant_total
FROM gestion_sinistres WHERE arrete = $arrete
GROUP BY segment
