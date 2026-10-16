# CLAUDE.md — Projet qdd-s2 (qualité des données Solvabilité 2)

Ce fichier est lu automatiquement par Claude Code. Il donne le contexte, les règles et les vérifications obligatoires.

## Contexte
- Propriétaire : Samadou Kodon (GitHub `Samadkod`). Il prend un poste d'analyste qualité des données / Solvabilité 2 (SAS, SQL) au service actuariat d'un assureur dommages.
- Objectif : un dispositif QDD **réel et concret**, pas une démonstration. Rigueur absolue : aucun chiffre non vérifié, aucune affirmation non sourcée.
- Langue : **français** (code, commentaires, documentation, messages de commit).
- Données : **100 % fictives** (assureur BTP simulé, graine fixe). Ne jamais nommer l'employeur réel dans le code, les données ou la documentation publique.
- Sources : mémoire de C. Motard (ISFA / Grant Thornton, 2024) sur la notation quantitative de la QDD ; notice ACPR « Exigences en matière de qualité des données » (fin 2023) ; missions de l'offre d'emploi (dictionnaire, lignage, contrôles, fiabilité des QRT, anomalies, SAS/SQL, Qlik Sense, ODBC).

## Architecture
| Couche | Chemin | Statut |
|---|---|---|
| Version **production** | `sas/` (00 config → 07 export Qlik, 98 vérification, 99 exécution) | Écrite, vérifiée statiquement, **jamais exécutée** (pas de SAS dans l'environnement d'origine) |
| Référence testée | `qdd_s2/` (moteur, campagne, gouvernance, sensibilité, rapport Excel, export Qlik) | 32 tests verts |
| Contrôles | `sql/controles/*.sql` (20, ANSI, sans CTE) + macros SAS équivalentes dans `sas/02_controles.sas` | Testés sur DuckDB |
| Référentiels | `referentiels/` : dictionnaire, référentiel des contrôles, lignage (flux + chemins), plan de campagne, historique | Source de vérité |
| Atelier HTML | `app/template.html` + `app/moteur.js` + `app/contenu.js` → `scripts/construire_appli.py` | Parité JS = Python testée |
| Application | `streamlit_app.py` (Atelier, Campagne live, Gouvernance, Code) | Testée avec `streamlit.testing` |
| Données fictives | `scripts/generer_donnees_btp.py` → `data/btp_fictif.duckdb` ; CSV pour SAS dans `sas/donnees_demo/` | Déterministes |

## Commandes
```bash
pip install -r requirements.txt
python scripts/generer_donnees_btp.py      # base fictive
python -m qdd_s2                           # campagnes N-1 et N -> output/ (Excel, JSON, registre, journal, Qlik)
python -m pytest -q                        # 32 tests, tous doivent passer
python scripts/lint_sas.py                 # vérification statique du SAS (doit afficher « Lint SAS OK »)
python scripts/construire_appli.py         # régénère l'atelier HTML (après python -m qdd_s2)
streamlit run streamlit_app.py
```
Recalcul et contrôle des formules Excel, si LibreOffice est disponible : ouvrir `output/rapport_qdd_*.xlsx` et vérifier que la colonne B de « Synthèse » est égale à la colonne C.

## Règles de méthode (ne pas modifier sans accord explicite du propriétaire)
1. **Contrôles de restitution QRT** (`inclus_note = 0`, `seuil_fixe = 0.999`) : statut binaire, suivis à part, **exclus de la note QDD**. Raison : sur le cas fictif, deux contrôles QRT parfaits faisaient passer une donnée du rouge à l'orange (dilution par la moyenne).
2. **Clôture d'une anomalie** : uniquement si le contrôle a été refait dans la campagne (antériorité 0) et n'est plus en anomalie. Les anomalies « Couverture » se clôturent dès que le flux est contrôlé.
3. **Identifiants d'anomalies déterministes** : constats triés par (type, objet). L'ordre doit rester identique en Python et en SAS.
4. **Antériorité** = nombre de fins de période calendaires dans ]dernière réalisation ; arrêté]. En SAS : `INTCK(intervalle, derniere + 1, arrete + 1)`.
5. **Résultat de contrôle** borné dans [0 ; 1] ; ratio d'anomalies pondéré en montant si disponible.
6. **Cohérence** : ΔSCR max < seuil de significativité (éq. 12), ou tolérance globale < seuil / S̄ (éq. 19). Toute violation est bloquante.
7. **Export Qlik** : seules les clés de liaison gardent leur nom (préfixes `cp_ dd_ dc_ fx_ lg_ nd_ rs_ ind_ an_ vr_`), noms valides en SAS (pas de point, 32 caractères max). Le test vérifie l'absence de clé synthétique et de boucle.
8. Aucun secret (mot de passe, jeton) dans le code, les journaux ou le dépôt. ODBC : DSN système ou `authdomain`.

## Invariants de parité (à maintenir après TOUTE modification de calcul)
- Python ↔ JavaScript : `tests/parite_js.mjs` (lancé par pytest si Node est présent).
- Python ↔ SQL : `sql/agregation_note_qdd.sql` (test `test_parite_sql_python`).
- Python ↔ Excel : formules des onglets « Contrôles », « Données critiques », « Synthèse ».
- Python ↔ SAS : régénérer `sas/donnees_demo/valeurs_attendues.csv` (43 valeurs) si un calcul ou une donnée change. `sas/98_verifier.sas` les compare à l'exécution SAS.
- Les tableaux 3, 5, 6, 7, 9, 11, 14, 16, 17, 22 et 24 du mémoire doivent rester reproduits (`tests/test_memoire.py`).

## Valeurs de référence (campagne N, 30/09/2026)
| Indicateur | Valeur |
|---|---|
| Note QDD / objectif | 97,45 % / 97,10 % |
| Données critiques hors tolérance | 2 sur 8 |
| Restitutions QRT conformes | 10 sur 11 |
| Zones de risque couvertes | 25 sur 33 |
| Anomalies ouvertes | 14, dont 4 de gravité haute |

Si l'une de ces valeurs change, c'est une **régression**, sauf si le changement est voulu et documenté dans le commit.

## Ce qui n'est PAS vérifié
- Exécution SAS : à faire sur SAS OnDemand ou en entreprise avec `99_executer.sas`, puis lire le log et `WORK.VERIFICATION`.
- Script Qlik `app/chargement_qdd.qvs` et gabarit ODBC : jamais exécutés.
- SCR : formule standard simplifiée, non réglementaire. Corrélations entre segments illustratives.

## Conventions
- Commits en français, au présent, avec un corps qui explique le pourquoi.
- Toute nouvelle règle de calcul : d'abord en Python avec un test, puis en SAS, puis en JavaScript si l'atelier l'utilise, puis valeurs attendues régénérées.
- Pas de dépendance nouvelle sans raison ; `requirements.txt` épinglé pour Streamlit.
