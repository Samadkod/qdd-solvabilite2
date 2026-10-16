-- C09 | Cohérence | Code CIC incohérent avec la classe d'actif (catégorie CIC 3 = actions, 1 = obligations d'État)
-- Critères : pertinence | Fréquence : trimestrielle
SELECT classe AS maille,
       SUM(CASE WHEN (classe = 'ACTIONS' AND SUBSTR(cic, 3, 1) <> '3')
                  OR (classe = 'OBLIGATIONS' AND SUBSTR(cic, 3, 1) NOT IN ('1', '2')) THEN 1 ELSE 0 END) AS n_anomalies,
       COUNT(*) AS n_elements,
       SUM(CASE WHEN (classe = 'ACTIONS' AND SUBSTR(cic, 3, 1) <> '3')
                  OR (classe = 'OBLIGATIONS' AND SUBSTR(cic, 3, 1) NOT IN ('1', '2')) THEN valeur_marche ELSE 0 END) AS montant_anomalies,
       SUM(valeur_marche) AS montant_total
FROM placements_depositaire WHERE arrete = $arrete
GROUP BY classe
