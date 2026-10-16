-- R02 | Rapprochement | Primes acquises : gestion vs entrepôt de données, par segment
-- Critères : exhaustivité, exactitude | Fréquence : trimestrielle
SELECT g.segment AS maille, g.v1, d.v2
FROM (SELECT segment, SUM(prime_acquise) AS v1
      FROM (SELECT DISTINCT contrat_id, segment, prime_acquise FROM gestion_contrats WHERE arrete = $arrete) u
      GROUP BY segment) g
JOIN (SELECT segment, SUM(prime_acquise) AS v2 FROM dwh_contrats WHERE arrete = $arrete GROUP BY segment) d
  ON d.segment = g.segment
