-- R04 | Rapprochement | Règlements cumulés : gestion vs comptabilité (alimentent les triangles du BE)
-- Critères : exactitude | Fréquence : trimestrielle
SELECT g.segment AS maille, g.v1, c.reglements AS v2
FROM (SELECT segment, SUM(reglements_cumules) AS v1 FROM gestion_sinistres WHERE arrete = $arrete GROUP BY segment) g
JOIN compta_reglements c ON c.segment = g.segment AND c.arrete = $arrete
