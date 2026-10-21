-- C07 | Lignes en anomalie : sinistres survenus avant la date d'effet du contrat
SELECT 'TOUS' AS maille, s.sinistre_id AS objet, ABS(s.provision_dossier) AS montant, 1 AS poids,
       'survenance ' || CAST(s.date_survenance AS VARCHAR) || ' ; effet du contrat ' || CAST(c.date_effet AS VARCHAR) AS valeurs
FROM gestion_sinistres s
JOIN (SELECT contrat_id, MIN(date_effet) AS date_effet FROM gestion_contrats WHERE arrete = $arrete GROUP BY contrat_id) c
  ON c.contrat_id = s.contrat_id
WHERE s.arrete = $arrete AND s.date_survenance < c.date_effet
