-- C02 | Lignes en anomalie : prime acquise négative ou supérieure à la prime émise
SELECT segment AS maille, contrat_id AS objet, ABS(prime_acquise) AS montant, 1 AS poids,
       'acquise ' || CAST(ROUND(prime_acquise, 2) AS VARCHAR) || ' € ; émise ' || CAST(ROUND(prime_emise, 2) AS VARCHAR) || ' €' AS valeurs
FROM gestion_contrats
WHERE arrete = $arrete AND (prime_acquise < 0 OR prime_acquise > prime_emise)
