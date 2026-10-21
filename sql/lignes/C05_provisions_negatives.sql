-- C05 | Lignes en anomalie : provisions de dossier négatives
SELECT segment AS maille, sinistre_id AS objet, ABS(provision_dossier) AS montant, 1 AS poids,
       'provision ' || CAST(ROUND(provision_dossier, 2) AS VARCHAR) || ' €' AS valeurs
FROM gestion_sinistres
WHERE arrete = $arrete AND provision_dossier < 0
