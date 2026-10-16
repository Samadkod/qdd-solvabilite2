-- C06 | Cohérence | Date de survenance postérieure à la date de déclaration
-- Critères : exactitude | Fréquence : trimestrielle | Une seule maille (donnée transverse)
SELECT 'TOUS' AS maille,
       SUM(CASE WHEN date_survenance > date_declaration THEN 1 ELSE 0 END) AS n_anomalies,
       COUNT(*) AS n_elements,
       SUM(CASE WHEN date_survenance > date_declaration THEN ABS(provision_dossier) ELSE 0 END) AS montant_anomalies,
       SUM(ABS(provision_dossier)) AS montant_total
FROM gestion_sinistres WHERE arrete = $arrete
