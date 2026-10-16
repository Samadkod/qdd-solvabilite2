# Version SAS / PROC SQL — celle qui va en production

Même méthode, mêmes formules et mêmes noms que le moteur Python. Le Python sert de référence testée (19 tests). Le SAS est la version à industrialiser.

| Fichier | Rôle |
|---|---|
| `00_config.sas` | Bibliothèques et **paramètres de la méthode** (seuil, ΔSCR max, coefficient de dégradation…) |
| `01_import_demo.sas` | Import des CSV fictifs (`donnees_demo/`). **À retirer en prod** : on branche les `libname` réels |
| `02_controles.sas` | 16 contrôles = 16 macros `%R01(arrete)` … `%C10(arrete)` + mesures génériques (rapprochement / cohérence) |
| `03_campagne.sas` | `%qdd_campagne` : exécution, historisation, antériorité (`INTCK`), dégradation, notes, tolérance, statuts, indicateurs ; `%qdd_axe` |
| `04_variation.sas` | `%qdd_variation` : analyse de la variation N-1 → N par substitutions successives |
| `05_rapport.sas` | `%qdd_rapport` : classeur Excel (ODS EXCEL, feux tricolores) |
| `99_executer.sas` | Lance tout : 2 campagnes, la variation, le rapport |

## Tester avant ta prise de poste
1. Crée un compte gratuit **SAS OnDemand for Academics** et ouvre SAS Studio.
2. Charge le dossier `qdd-s2/sas/` (avec `donnees_demo/`) dans ton espace `/home/<ton_id>/qdd-s2/`.
3. Ouvre `99_executer.sas` et lance-le (F3).
4. Compare avec les valeurs attendues écrites en bas du fichier (N : note 97,45 %, objectif 97,10 %).

⚠️ **Ce code SAS n'a pas pu être exécuté ici** (il n'y avait pas de SAS dans l'environnement). Les formules sont reprises une à une du Python testé. La logique d'antériorité (`INTCK(intervalle, dernière + 1, arrêté + 1)`) a été vérifiée contre le Python sur les 78 points de contrôle. Une première exécution peut toutefois révéler des fautes de frappe : corrige-les en lisant le log.

## Brancher sur les vraies données
- **Ajouter un contrôle** : 1 macro `%Xnn(arrete)` qui crée `WORK._C` au format standard, plus 1 ligne dans `QDD.REFERENTIEL_CONTROLES`. `{maille}` dans `donnee_id` génère automatiquement un point de contrôle par maille.
- **Sensibilités** : la table `QDD.RELANCES_SCR` (arrêté, donnée, choc, valeur, SCR) est remplie à partir des relances du moteur SCR faites par l'actuariat. Le choc 0 correspond au SCR de référence.
- **Historique** : `QDD.HIST_RESULTATS` est permanente. Relancer une campagne remplace ses propres résultats ; le traitement est idempotent.
