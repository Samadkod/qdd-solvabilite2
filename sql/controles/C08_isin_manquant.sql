-- C08 | Cohérence | ISIN absent ou mal formé (12 caractères, 2 lettres pays) — cf. indicateur EIOPA
-- Critères : exhaustivité, exactitude | Fréquence : trimestrielle
SELECT classe AS maille,
       SUM(CASE WHEN isin IS NULL OR LENGTH(isin) <> 12 THEN 1 ELSE 0 END) AS n_anomalies,
       COUNT(*) AS n_elements,
       SUM(CASE WHEN isin IS NULL OR LENGTH(isin) <> 12 THEN valeur_marche ELSE 0 END) AS montant_anomalies,
       SUM(valeur_marche) AS montant_total
FROM placements_depositaire WHERE arrete = $arrete
GROUP BY classe
