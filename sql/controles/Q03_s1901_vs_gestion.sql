-- Q03 | Rapprochement | Triangle S.19.01 (dernière diagonale des paiements cumulés) vs règlements cumulés de gestion
-- Critères : exhaustivité, exactitude | Fréquence : trimestrielle | Flux sécurisé : F08
SELECT g.segment AS maille, g.v1, t.v2
FROM (SELECT segment, SUM(reglements_cumules) AS v1 FROM gestion_sinistres WHERE arrete = $arrete GROUP BY segment) g
JOIN (SELECT segment, SUM(paiements_cumules) AS v2 FROM qrt_s1901_diagonale WHERE arrete = $arrete GROUP BY segment) t
  ON t.segment = g.segment
