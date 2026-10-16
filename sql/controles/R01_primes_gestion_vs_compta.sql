-- R01 | Rapprochement | Primes acquises : gestion vs comptabilité, par segment
-- Critères : exactitude | Fréquence : trimestrielle | SQL ANSI, sans CTE (transposable en PROC SQL)
SELECT g.segment AS maille,
       g.v1,
       c.prime_acquise AS v2
FROM (SELECT segment, SUM(prime_acquise) AS v1
      FROM (SELECT DISTINCT contrat_id, segment, prime_acquise FROM gestion_contrats WHERE arrete = $arrete) u
      GROUP BY segment) g
JOIN compta_primes c ON c.segment = g.segment AND c.arrete = $arrete
