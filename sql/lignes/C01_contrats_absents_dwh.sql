-- C01 | Lignes en anomalie : contrats de l'outil de gestion absents de l'entrepôt
SELECT g.segment AS maille, g.contrat_id AS objet, ABS(g.prime_acquise) AS montant, 1 AS poids,
       'prime acquise ' || CAST(ROUND(g.prime_acquise, 2) AS VARCHAR) || ' €' AS valeurs
FROM (SELECT DISTINCT contrat_id, segment, prime_acquise FROM gestion_contrats WHERE arrete = $arrete) g
LEFT JOIN dwh_contrats d ON d.contrat_id = g.contrat_id AND d.arrete = $arrete
WHERE d.contrat_id IS NULL
