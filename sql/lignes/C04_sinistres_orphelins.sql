-- C04 | Lignes en anomalie : sinistres rattachés à un contrat inconnu de l'outil de gestion
SELECT s.segment AS maille, s.sinistre_id AS objet, ABS(s.provision_dossier) AS montant, 1 AS poids,
       'contrat ' || s.contrat_id || ' ; provision ' || CAST(ROUND(s.provision_dossier, 2) AS VARCHAR) || ' €' AS valeurs
FROM gestion_sinistres s
LEFT JOIN (SELECT DISTINCT contrat_id FROM gestion_contrats WHERE arrete = $arrete) c ON c.contrat_id = s.contrat_id
WHERE s.arrete = $arrete AND c.contrat_id IS NULL
