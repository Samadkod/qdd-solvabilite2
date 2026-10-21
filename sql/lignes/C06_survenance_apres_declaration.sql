-- C06 | Lignes en anomalie : sinistres survenus après leur déclaration
SELECT 'TOUS' AS maille, sinistre_id AS objet, ABS(provision_dossier) AS montant, 1 AS poids,
       'survenance ' || CAST(date_survenance AS VARCHAR) || ' ; déclaration ' || CAST(date_declaration AS VARCHAR) AS valeurs
FROM gestion_sinistres
WHERE arrete = $arrete AND date_survenance > date_declaration
