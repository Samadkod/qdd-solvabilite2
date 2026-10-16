-- C01 | Cohérence | Contrats de gestion absents de l'entrepôt (exhaustivité du transfert)
-- Mesure pondérée en montant de prime acquise | Fréquence : trimestrielle
SELECT g.segment AS maille,
       SUM(CASE WHEN d.contrat_id IS NULL THEN 1 ELSE 0 END)                  AS n_anomalies,
       COUNT(*)                                                               AS n_elements,
       SUM(CASE WHEN d.contrat_id IS NULL THEN ABS(g.prime_acquise) ELSE 0 END) AS montant_anomalies,
       SUM(ABS(g.prime_acquise))                                              AS montant_total
FROM (SELECT DISTINCT contrat_id, segment, prime_acquise FROM gestion_contrats WHERE arrete = $arrete) g
LEFT JOIN dwh_contrats d ON d.contrat_id = g.contrat_id AND d.arrete = $arrete
GROUP BY g.segment
