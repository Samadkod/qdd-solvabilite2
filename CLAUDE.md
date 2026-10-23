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
| Version **production** | `sas/` (00 config → 07 export Qlik, 98 vérification, 99 exécution ; point d'entrée `lancer_qdd.sas` : `&RACINE` + contrôle des fichiers) | Écrite, vérifiée statiquement, **jamais exécutée** (pas de SAS dans l'environnement d'origine) |
| Référence testée | `qdd_s2/` (moteur, campagne, gouvernance, sensibilité, rapport Excel, export Qlik) | 95 tests verts |
| Contrôles | `sql/controles/*.sql` (20, ANSI, sans CTE) + macros SAS équivalentes dans `sas/02_controles.sas` | Testés sur DuckDB |
| Référentiels | `referentiels/` : dictionnaire, référentiel des contrôles, lignage (flux + chemins), plan de campagne, historique | Source de vérité |
| Atelier HTML | `app/template.html` + `app/moteur.js` + `app/contenu.js` → `scripts/construire_appli.py` | Parité JS = Python testée |
| Application | `streamlit_app.py` : deux espaces. Atelier QDD (Pilotage QDD : Synthèse, Note & données, Contrôles, Anomalies, Lignes en anomalie, Règles de contrôle, Lignage & dictionnaire ; Exploitation : Chargement & exécution ; Évolutions : Feuille de route dans `feuille_de_route.py`) et, sous le bouton Documentation, Comprendre / Se former / Technique ; tuiles avec évolution depuis N-1 colorée selon le sens ; tuiles de la Synthèse dans `synthese.py` (valeur = moteur = lignes de la liste ouverte : `tests/test_synthese.py`) ; guide dans `guide_terrain.py`, explications « d'où sortent les chiffres » et lecture des graphiques dans `explications.py` (recalcul vérifié égal au moteur : `tests/test_explications.py`), habillage dans `style_app.py` + `.streamlit/config.toml` | Testée avec `streamlit.testing` (`tests/test_streamlit.py`) |
| Exercices SAS | Corrigés dans `sas/10_exercices_corriges.sas` (source unique, non appelé par `99_executer.sas`) ; énoncés et résultats attendus (DuckDB sur `sas/donnees_demo`) dans `exercices_sas.py` | Lint SAS OK, résultats attendus testés (`tests/test_exercices_sas.py`) ; **jamais exécutés dans SAS** |
| Contrôles de chargement (niveau 0) | `chargement.py` + `sas/08_chargement.sas` (%qdd_volumetrie) : table vide = Bloquant ; variation > 10 % (ou petite table < 50 lignes modifiée) = À expliquer ; rejeu des requêtes de contrôle (échec technique, durée). Hors note | Règle testée (`tests/test_chargement.py`), aucune fausse alerte sur le SI fictif ; SAS jamais exécuté |
| Lignes en anomalie | `sql/lignes/C01…C10` (une ligne par objet fautif) + `lignes_anomalie.py` (lignes, regroupements, catalogue des règles) | Par contrôle et par maille, nombre de lignes = nombre d'anomalies du contrôle agrégé, sur N-1 et N (`tests/test_lignes_anomalie.py`) ; pas d'équivalent SAS |
| Suivi des contrôles | `suivi_controles.py` (page Contrôles) : statut d'exécution (Exécuté, Saisi hors outil, Non réalisé, Échec technique) séparé du résultat, dernière réalisation, prochaine échéance (`qdd_s2.anteriorite.prochaine_echeance`), durée au rejeu, tendance sur les campagnes (échelle commune 85-100 %), filtres, avancement de la campagne, accès aux lignes en anomalie | Échéance passée ⇔ antériorité > 0 sur les 3 campagnes ; compteurs = moteur (`tests/test_suivi_controles.py`) ; pas d'équivalent SAS |
| Données fictives | `scripts/generer_donnees_btp.py` → `data/btp_fictif.duckdb` (3 arrêtés : 31/03, 30/06, 30/09/2026) ; CSV pour SAS dans `sas/donnees_demo/` | Déterministes ; un flux aléatoire par arrêté |

## Commandes
```bash
pip install -r requirements.txt
python scripts/generer_donnees_btp.py      # base fictive
python -m qdd_s2                           # campagnes N-2, N-1 et N -> output/ (Excel, JSON, registre, journal, Qlik)
python -m pytest -q                        # 95 tests, tous doivent passer
python scripts/lint_sas.py                 # vérification statique du SAS (doit afficher « Lint SAS OK »)
python scripts/construire_appli.py         # régénère l'atelier HTML (après python -m qdd_s2)
streamlit run streamlit_app.py
```
Recalcul des formules Excel : `tests/test_excel_recalcul.py` recalcule le rapport avec LibreOffice et vérifie que la colonne B de « Synthèse » (formules) est égale à la colonne C (moteur), 11 valeurs ; ignoré si LibreOffice est absent. Vérifié 11/11 le 21/10/2026.

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
- Python ↔ SAS : régénérer `sas/donnees_demo/valeurs_attendues.csv` (59 valeurs, `python scripts/valeurs_attendues.py`) si un calcul ou une donnée change. `sas/98_verifier.sas` les compare à l'exécution SAS.
- Les tableaux 3, 5, 6, 7, 9, 11, 14, 16, 17, 22 et 24 du mémoire doivent rester reproduits (`tests/test_memoire.py`).

## Valeurs de référence (campagne N, 30/09/2026)
| Indicateur | Valeur |
|---|---|
| Note QDD / objectif | 97,49 % / 97,10 % |
| Données critiques hors tolérance | 2 sur 8 |
| Restitutions QRT conformes | 10 sur 11 |
| Zones de risque couvertes | 25 sur 33 |
| Anomalies ouvertes | 14, dont 4 de gravité haute |
| Anomalies clôturées (registre) | 3, clôturées en N-1 : C06, R04 RC décennale, Q04 RC décennale |

Si l'une de ces valeurs change, c'est une **régression**, sauf si le changement est voulu et documenté dans le commit.
Historique : 97,45 % → 97,49 % (octobre 2026) après correction, validée par le propriétaire, des dates de sinistres fictives (survenance entre l'effet du contrat et l'arrêté, déclaration jamais après l'arrêté) ; seuls note, note avant dégradation, écart à l'objectif et étapes de variation ont bougé (17 valeurs attendues SAS sur 43).
Ajout (octobre 2026, validé par le propriétaire) d'une campagne N-2 au 31/03/2026 pour montrer le cycle de vie complet du registre : nouvel arrêté généré avec son propre flux aléatoire (indice 2), données N-1 et N identiques au bit près ; note, objectif et compteurs de N inchangés ; seuls changent les identifiants d'anomalies, les dates de détection et 4 valeurs attendues (N-1 : récurrentes 0 → 10, en retard 0 → 10, clôturées 0 → 3 ; N : clôturées 0 → 3).

## Ce qui n'est PAS vérifié
- Exécution SAS : à faire sur SAS OnDemand ou en entreprise avec `99_executer.sas`, puis lire le log et `WORK.VERIFICATION`.
- Script Qlik `app/chargement_qdd.qvs` et gabarit ODBC : jamais exécutés.
- SCR : formule standard simplifiée, non réglementaire. Corrélations entre segments illustratives.

## Conventions
- Commits en français, au présent, avec un corps qui explique le pourquoi.
- Toute nouvelle règle de calcul : d'abord en Python avec un test, puis en SAS, puis en JavaScript si l'atelier l'utilise, puis valeurs attendues régénérées.
- Pas de dépendance nouvelle sans raison ; `requirements.txt` épinglé pour Streamlit.
