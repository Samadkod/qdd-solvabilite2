-- C02 | Cohérence | Prime acquise négative ou supérieure à la prime émise
-- Critères : exactitude | Fréquence : trimestrielle
SELECT segment AS maille,
       SUM(CASE WHEN prime_acquise < 0 OR prime_acquise > prime_emise THEN 1 ELSE 0 END) AS n_anomalies,
       COUNT(*) AS n_elements,
       SUM(CASE WHEN prime_acquise < 0 OR prime_acquise > prime_emise THEN ABS(prime_acquise) ELSE 0 END) AS montant_anomalies,
       SUM(ABS(prime_acquise)) AS montant_total
FROM gestion_contrats WHERE arrete = $arrete
GROUP BY segment
