-- R03 | Rapprochement 3 sources | Provisions dossier/dossier : gestion vs entrepôt vs inputs actuariat
-- Critères : exhaustivité, exactitude | Fréquence : trimestrielle | Mesure : max des écarts 2 à 2 (éq. 30)
SELECT g.segment AS maille, g.v1, d.v2, a.provision_dossier_total AS v3
FROM (SELECT segment, SUM(provision_dossier) AS v1 FROM gestion_sinistres WHERE arrete = $arrete GROUP BY segment) g
JOIN (SELECT segment, SUM(provision_dossier) AS v2 FROM dwh_sinistres WHERE arrete = $arrete GROUP BY segment) d
  ON d.segment = g.segment
JOIN actuariat_inputs a ON a.segment = g.segment AND a.arrete = $arrete
