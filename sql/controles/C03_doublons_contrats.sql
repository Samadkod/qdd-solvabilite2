-- C03 | Cohérence | Doublons de contrats dans l'outil de gestion
-- Critères : exactitude, pertinence | Fréquence : semestrielle
SELECT segment AS maille,
       COUNT(*) - COUNT(DISTINCT contrat_id) AS n_anomalies,
       COUNT(*)                              AS n_elements,
       NULL AS montant_anomalies, NULL AS montant_total
FROM gestion_contrats WHERE arrete = $arrete
GROUP BY segment
