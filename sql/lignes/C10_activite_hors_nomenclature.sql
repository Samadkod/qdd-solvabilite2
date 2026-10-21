-- C10 | Lignes en anomalie : code activité absent de la nomenclature BTP
SELECT 'TOUS' AS maille, g.contrat_id AS objet, CAST(NULL AS DOUBLE) AS montant, 1 AS poids,
       'code activité « ' || COALESCE(g.code_activite, '') || ' »' AS valeurs
FROM gestion_contrats g
LEFT JOIN ref_activites_btp r ON r.code_activite = g.code_activite
WHERE g.arrete = $arrete AND r.code_activite IS NULL
