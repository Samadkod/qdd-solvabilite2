-- C09 | Lignes en anomalie : code CIC incohérent avec la classe d'actif
SELECT classe AS maille, actif_id AS objet, valeur_marche AS montant, 1 AS poids,
       'CIC ' || cic AS valeurs
FROM placements_depositaire
WHERE arrete = $arrete
  AND ((classe = 'ACTIONS' AND SUBSTR(cic, 3, 1) <> '3')
    OR (classe = 'OBLIGATIONS' AND SUBSTR(cic, 3, 1) NOT IN ('1', '2')))
