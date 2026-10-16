-- R06 | Rapprochement | Valeur de marché des placements : dépositaire vs comptabilité, par classe
-- Critères : exactitude | Fréquence : trimestrielle
SELECT d.classe AS maille, SUM(d.valeur_marche) AS v1, SUM(c.valeur_marche) AS v2
FROM placements_depositaire d
JOIN placements_compta c ON c.actif_id = d.actif_id AND c.arrete = d.arrete
WHERE d.arrete = $arrete
GROUP BY d.classe
