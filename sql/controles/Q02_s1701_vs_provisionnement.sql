-- Q02 | Rapprochement | Best estimate sinistres brut : état S.17.01 vs outil de provisionnement, par segment
-- Critères : exactitude | Fréquence : trimestrielle | Flux sécurisé : F08
SELECT q.segment AS maille, a.be_sinistres_brut AS v1, q.be_sinistres_brut AS v2
FROM qrt_s1701 q
JOIN actuariat_be a ON a.segment = q.segment AND a.arrete = q.arrete
WHERE q.arrete = $arrete
