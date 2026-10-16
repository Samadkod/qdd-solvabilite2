-- Q04 | Rapprochement | Primes acquises brutes : état S.05.01 vs comptabilité, par segment
-- Critères : exactitude | Fréquence : trimestrielle | Flux sécurisé : F03
SELECT c.segment AS maille, c.prime_acquise AS v1, q.primes_acquises_brutes AS v2
FROM compta_primes c
JOIN qrt_s0501 q ON q.segment = c.segment AND q.arrete = c.arrete
WHERE c.arrete = $arrete
