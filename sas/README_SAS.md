# Version SAS / PROC SQL — version production

Même logique, mêmes noms, mêmes résultats attendus que la référence Python (`qdd_s2/`).

| Fichier | Rôle |
|---|---|
| `00_config.sas` | Bibliothèques, **paramètres de la méthode**, gabarit **ODBC** et pass-through (commenté) |
| `01_import_demo.sas` | Import des CSV fictifs (`donnees_demo/`) : SI, états QRT simplifiés, dictionnaire, référentiel, lignage. **À retirer en prod** |
| `02_controles.sas` | 20 contrôles en macros `%R01(arrete)`… `%Q04(arrete)` + mesures génériques |
| `03_campagne.sas` | `%qdd_campagne` : exécution, historisation, antériorité (`INTCK`), dégradation, notes, tolérance, seuils fixes de restitution, statuts, indicateurs ; `%qdd_axe` |
| `04_variation.sas` | `%qdd_variation` : analyse de variation N-1 → N |
| `05_rapport.sas` | `%qdd_rapport` : classeur Excel (synthèse, variation, données, contrôles, axes, sensibilités, lignage, registre, dictionnaire, journal) |
| `06_gouvernance.sas` | `%qdd_couverture`, `%qdd_registre` (cycle de vie des anomalies), `%qdd_journal` (piste d'audit) |
| `07_export_qlik.sas` | `%qdd_export_qlik` : modèle en étoile CSV pour Qlik Sense (script `app/chargement_qdd.qvs`) |
| `98_verifier.sas` | Compare 59 valeurs à `donnees_demo/valeurs_attendues.csv` (référence Python) |
| `99_executer.sas` | Exécute tout, puis lance la vérification |
| `lancer_qdd.sas` | **Point d'entrée unique** : fixe `&RACINE` (seule ligne à adapter), vérifie que les 38 fichiers sont en place, puis lance `99_executer.sas` |

## Tester avant la prise de poste
1. Crée un compte gratuit SAS OnDemand for Academics et ouvre SAS Studio.
2. Copie `qdd-s2/sas/` (avec `donnees_demo/`) dans un dossier de ton espace, par exemple `/home/<ton_id>/qdd-s2/sas/`.
   Les programmes `.sas` vont dans `sas/`, les fichiers `.csv` dans `sas/donnees_demo/`.
3. Ouvre `lancer_qdd.sas`, adapte la ligne `%let RACINE = …` si le dossier n'est pas `/home/<ton_id>/qdd-s2`, lance-le (F3).
   L'import des CSV est fait par `01_import_demo.sas` (étapes DATA, types et longueurs fixés) : pas de PROC IMPORT.
4. Le log doit afficher `NOTE: [QDD] PARITÉ SAS / PYTHON OK`. En cas d'écart, la table `WORK.VERIFICATION` indique les valeurs en écart.

**Première exécution réelle : SAS OnDemand, 23/10/2026** (`lancer_qdd.sas`, SAS 9.4M9). Campagnes N-1 et N et
analyse de variation identiques à la référence Python (44 valeurs sur 59). Les 15 écarts venaient tous de la
campagne N-2 : le fichier `relances_scr.csv` ne contenait pas l'arrêté du 31/03/2026. Corrigé (script
`scripts/relances_scr.py` et test de cohérence) ; une nouvelle exécution doit donner 59 sur 59.

Avant cette exécution, le code avait été :
- vérifié statiquement (`scripts/lint_sas.py` : blocs, macros, guillemets, parenthèses, `%if` hors macro, `%include`) ;
- testé par injection de fautes, pour s'assurer que le vérificateur les détecte ;
- aligné ligne à ligne sur le Python. La logique d'antériorité a été comparée sur les 100 points des deux campagnes.

Une première exécution peut révéler des fautes que seule l'exécution montre (types, longueurs) : le log et `98_verifier.sas` sont faits pour cela.

## Règles importantes
- **Contrôles de restitution** (`inclus_note = 0`, `seuil_fixe = 0.999`) : état QRT comparé à sa source. Statut binaire, suivis à part, **exclus de la note QDD** pour éviter la dilution.
- **Clôture d'une anomalie** : uniquement si le contrôle a été refait dans la campagne et repasse au vert (sauf « Couverture » : dès que le flux est contrôlé).
- **Journal** : aucun mot de passe dans le code ni dans les journaux (DSN système ou `authdomain`).
- **Ajouter un contrôle** : 1 macro `%Xnn(arrete)` qui crée `WORK._C` au format standard, plus 1 ligne au référentiel (dont la colonne `flux`).
