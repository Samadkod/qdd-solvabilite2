-- C03 | Lignes en anomalie : numéros de contrat présents plusieurs fois (poids = lignes en trop)
SELECT segment AS maille, contrat_id AS objet, CAST(NULL AS DOUBLE) AS montant, COUNT(*) - 1 AS poids,
       CAST(COUNT(*) AS VARCHAR) || ' lignes pour ce contrat' AS valeurs
FROM gestion_contrats
WHERE arrete = $arrete
GROUP BY segment, contrat_id
HAVING COUNT(*) > 1
