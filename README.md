# qdd-s2 — Évaluation quantitative de la qualité des données Solvabilité 2

Prototype industrialisable de la méthode du mémoire de **Camille Motard** (*Analyse quantitative de la qualité des données sous Solvabilité 2*, ISFA / Grant Thornton, mars 2024). La méthode y est **corrigée et complétée**, puis appliquée à un **assureur dommages BTP fictif**.

> Toutes les données du dossier `data/` sont **simulées**. Le SCR utilisé est une formule standard **simplifiée et non réglementaire** : il faut la remplacer par le moteur SCR de l'organisme.

## Ce que fait l'outil

```
Référentiels (répertoire de données, référentiel des contrôles, plan de campagne)
  + base (SI gestion / entrepôt / comptabilité / actuariat / placements)
  → contrôles SQL (rapprochement | cohérence) → points de contrôle (1 donnée chacun)
  → historique des résultats → antériorité + dégradation des contrôles non réalisés
  → sensibilités du SCR → criticité, pondération, tolérance, seuils d'acceptation
  → note QDD par donnée → note QDD agrégée (+ par axe : segment, étape SI, critère, responsable)
  → analyse de variation N-1 → N → rapport Excel vivant + export JSON (tableau de bord)
```

## Application en ligne (Streamlit)

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
Elle a trois onglets : l'**Atelier** (fiches, QCM, vrai/faux, simulateur, avis critique, plan 90 jours), la **Campagne live** (le moteur tourne en direct, avec des paramètres modifiables et un rapport Excel téléchargeable) et le **Code SAS / SQL**.

## Version production : SAS / PROC SQL
Le dossier `sas/` est un portage complet : contrôles, campagne, variation et rapport ODS EXCEL. Voir `sas/README_SAS.md`.

## Démarrage

```bash
pip install pandas numpy openpyxl duckdb pytest
python scripts/generer_donnees_btp.py      # base fictive data/btp_fictif.duckdb
python -m qdd_s2                           # campagnes N-1 et N -> output/
python -m qdd_s2 --symetrique              # variante : écart symétrique borné
python -m pytest -q                        # 19 tests
```

## Arborescence

| Chemin | Rôle |
|---|---|
| `qdd_s2/mesures.py` | Résultat quantitatif d'un contrôle (éq. 27-33) + écart symétrique, ratio pondéré en montant |
| `qdd_s2/anteriorite.py` | Antériorité (base fréquence / annuelle) et dégradation simple / composée (éq. 34-37) |
| `qdd_s2/moteur.py` | Criticité, notes, tolérance (2 approches), seuils, indicateurs, axes, analyse de variation |
| `qdd_s2/sensibilite.py` | Sensibilités du SCR + **test de linéarité** + SCR jouet |
| `qdd_s2/campagne.py` | Orchestration : exécution SQL, historique, campagnes |
| `qdd_s2/rapport_excel.py` | Rapport Excel : les onglets Paramètres / Contrôles / Données critiques sont recalculés par des formules |
| `sql/controles/*.sql` | 16 contrôles (ANSI, sans CTE : transposables en SAS PROC SQL) |
| `sql/agregation_note_qdd.sql` | Note agrégée en SQL pur (parité testée avec Python) |
| `referentiels/*.csv` | Répertoire des données (ACPR, points 47-48), référentiel des contrôles (points 67-70), plan, historique |
| `tests/test_memoire.py` | **Reproduction des tableaux 3, 5, 6, 7, 9, 11, 14, 16, 17, 22, 24 du mémoire** |

## Corrections et améliorations par rapport au mémoire

| # | Constat dans le mémoire | Traitement ici |
|---|---|---|
| 1 | `1 − note` est interprété comme une incertitude relative sur la donnée, alors que, pour un contrôle de cohérence, le ratio d'anomalies est un **nombre** de lignes | Ratio d'anomalies **pondéré en montant** par défaut (`montant en anomalie / montant total`), ce qui le rend homogène avec un écart de rapprochement |
| 2 | L'écart `max/min − 1` (éq. 31) n'est pas borné et devient faux avec des montants négatifs ; l'éq. 27 peut alors donner une note négative | Résultat borné dans [0 ; 1] + option `ecart_symetrique` = `min(1, \|a−b\| / max(\|a\|,\|b\|))` |
| 3 | Les moyennes compensent : une donnée critique très dégradée peut se cacher derrière une bonne note agrégée | Règle du **maillon faible** : statut tricolore par donnée et par contrôle, nombre de données hors tolérance, note plancher |
| 4 | Linéarité du SCR posée comme « hypothèse forte », jamais testée (sauf sur les primes) | Sensibilité calculée avec 4 chocs (−15 %, +5 %, +15 %, +30 %) et indicateur de non-linéarité |
| 5 | Le mémoire suppose qu'il n'existe pas de donnée critique sans contrôle | Ces données sont signalées ; option `donnee_sans_controle="zero"` (approche prudente) |
| 6 | Cohérence tolérance / criticité (éq. 12, 19) énoncée mais pas outillée | Vérification bloquante dans `Parametres.verifier_coherence` |
| 7 | La formule de la « variation proratisée » (p. 84) ne laisse pas la note inchangée quand la qualité est stable | Non implémentée ; c'est l'analyse de variation par substitutions (tableau 20) qui est retenue, conformément à la conclusion du mémoire |
| 8 | Partie « outil » (§3.2.1) sans architecture | Modèle de données, contrôles SQL, rapport, tests, JSON pour tableau de bord |

Erreurs relevées dans le texte du mémoire (sans effet sur le code) :
- p. 21 : le ratio de solvabilité est écrit SCR / fonds propres ; c'est fonds propres / SCR.
- p. 54 : avec une sensibilité de 10 %, une variation de 1 % de la donnée fait varier le SCR de **0,1 %**, pas de 10 %.
- Sensibilité des provisions mathématiques : 4,57 % (tableaux 3 et 14) mais 5,74 % (tableaux 5 à 9).
- Le tableau 4 reprend les pondérations du tableau 2 au lieu des sensibilités.
- Le tableau 19 a des colonnes décalées.

## Passage en production (cible : actuariat d'un assureur BTP)

1. **Périmètre et criticité** : remplacer `scr_formule_standard_simplifiee` par des relances du moteur SCR réel. Pour la formule standard, les volumes de primes et réserves par segment, le BE de la décennale, les taux de cession et les placements sont les premiers candidats. Faire valider le seuil de significativité et le ΔSCR max par la fonction actuarielle, puis les formaliser dans la politique QDD (notice ACPR, point 17).
2. **Données** : remplacer les tables DuckDB par des vues sur les extractions réelles (SAS, base de gestion). Les SQL sont écrits sans CTE, ils passent tels quels en PROC SQL (seule la syntaxe des paramètres change).
3. **Référentiels** : compléter `repertoire_donnees.csv` et `referentiel_controles.csv` avec les propriétaires de données et les relais. Une ligne = un contrôle ; `{maille}` génère automatiquement les points de contrôle.
4. **Campagnes** : planification trimestrielle (après l'arrêté). Historisation des résultats dans une table, plus de CSV.
5. **Restitution** : rapport Excel pour le comité de pilotage S2 et tableau de bord (export JSON) pour le comité opérationnel.
6. **Gouvernance** : tout changement de paramètre ou de contrôle passe par l'analyse de variation, présentée en comité.

## Limites connues

- Le SCR est un SCR jouet ; les corrélations entre segments sont illustratives.
- Une donnée critique à dire d'expert qui n'a pas de sensibilité calculable reçoit par convention la sensibilité moyenne des données critiques. Cette convention doit être validée.
- L'analyse de variation couvre la note agrégée, pas la note minimum.
