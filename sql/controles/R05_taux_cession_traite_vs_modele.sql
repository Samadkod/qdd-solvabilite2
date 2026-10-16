-- R05 | Rapprochement | Taux de cession : traités de réassurance vs paramètre du modèle SCR, par segment
-- Critères : exactitude, pertinence | Fréquence : annuelle
SELECT t.segment AS maille, t.taux_cession AS v1, m.taux_cession AS v2
FROM reassurance_traites t
JOIN modele_parametres m ON m.segment = t.segment AND m.arrete = t.arrete
WHERE t.arrete = $arrete
