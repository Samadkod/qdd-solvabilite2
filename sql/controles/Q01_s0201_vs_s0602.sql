-- Q01 | Rapprochement inter-états QRT | Bilan S.02.01 (placements) vs somme de la liste des actifs S.06.02, par classe
-- Critères : exhaustivité, exactitude | Fréquence : trimestrielle | Flux sécurisé : F12
SELECT b.classe AS maille, b.v1, l.v2
FROM (SELECT SUBSTR(poste, 12) AS classe, montant AS v1
      FROM qrt_s0201 WHERE arrete = $arrete AND poste LIKE 'PLACEMENTS_%') b
JOIN (SELECT classe, SUM(valeur_marche) AS v2 FROM qrt_s0602 WHERE arrete = $arrete GROUP BY classe) l
  ON l.classe = b.classe
