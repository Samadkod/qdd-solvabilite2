-- C08 | Lignes en anomalie : code ISIN absent ou mal formé
SELECT classe AS maille, actif_id AS objet, valeur_marche AS montant, 1 AS poids,
       'ISIN « ' || COALESCE(isin, '') || ' »' AS valeurs
FROM placements_depositaire
WHERE arrete = $arrete AND (isin IS NULL OR LENGTH(isin) <> 12)
