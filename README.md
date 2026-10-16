# qdd-s2 — Dispositif de qualité des données Solvabilité 2

Prototype d'un dispositif QDD pour un assureur dommages, construit à partir de deux sources :
- les missions d'un poste d'**analyste qualité des données / Solvabilité 2** : dictionnaire, lignage, contrôles, fiabilité des QRT, coordination des anomalies, SAS/SQL, Qlik Sense ;
- la méthode de notation quantitative du mémoire de **Camille Motard** (*Analyse quantitative de la qualité des données sous Solvabilité 2*, ISFA / Grant Thornton, 2024), **corrigée** et appliquée en surcouche.

> Toutes les données sont **fictives** (assureur dommages BTP simulé, graine fixe). Le SCR est une formule standard **simplifiée et non réglementaire** : en production, les sensibilités viennent des relances du moteur SCR de l'organisme.

## Ce que fait le dispositif

```
Dictionnaire des données ─┐
Lignage (14 flux)        ─┼─> Référentiel des contrôles (20 contrôles SQL / SAS, dont 4 de restitution QRT)
                          │        │ exécution par arrêté, historisation
                          │        v
                          │   Points de contrôle (50) : résultat, antériorité, dégradation
                          │        │
                          ├────────┼─> Couverture des zones de risque (lignage x contrôles)
                          │        ├─> Registre des anomalies (cycle de vie entre campagnes)
                          │        └─> Note QDD (méthode du mémoire) : criticité, tolérance, analyse de variation
                          └─> Journal d'exécution (paramètres, version, empreintes, volumétries)
Restitution : rapport Excel (formules vivantes) · export Qlik Sense (modèle en étoile) · application Streamlit
```

## Deux versions, une même logique
| | Rôle | Vérification |
|---|---|---|
| **SAS / PROC SQL** (`sas/`) | Version **production** | Vérification statique (`scripts/lint_sas.py`) ; comparaison automatique de 43 valeurs à la référence Python (`sas/98_verifier.sas`) |
| **Python** (`qdd_s2/`) | Référence testée, prototypage, application | 32 tests, dont la reproduction des tableaux 3, 5, 6, 7, 9, 11, 14, 16, 17, 22 et 24 du mémoire |
| JavaScript (`app/moteur.js`) | Calculs de l'atelier HTML | Parité avec le Python testée sur toutes les valeurs |
| Excel (rapport) | Restitution | Les 11 indicateurs calculés par formules sont égaux à ceux du moteur |

⚠️ Le SAS **n'a pas pu être exécuté** dans l'environnement de développement (SAS n'y est pas installé). Il faut le lancer une première fois sur SAS OnDemand ou en entreprise avec `99_executer.sas` ; `98_verifier.sas` signale alors tout écart avec la référence.

## Démarrage
```bash
pip install -r requirements.txt
python scripts/generer_donnees_btp.py     # SI fictif (DuckDB)
python -m qdd_s2                          # campagnes N-1 et N -> output/
python -m pytest -q                       # 32 tests
python scripts/lint_sas.py                # vérification statique du SAS
streamlit run streamlit_app.py            # application
```

## Résultats de la campagne fictive N (30/09/2026)
| Indicateur | Valeur |
|---|---|
| Note QDD agrégée / objectif | 97,45 % / 97,10 % |
| Données critiques hors tolérance | 2 sur 8 (provisions RC décennale rouge, date de survenance orange) |
| Restitutions QRT conformes | 10 sur 11 (S.17.01 dommages-ouvrage : BE périmé, écart de 3,1 %) |
| Zones de risque couvertes | 25 sur 33 (flux vers l'outil SCR F04, F09, F13 non contrôlés) |
| Anomalies ouvertes | 14, dont 4 de gravité haute et 11 à échéance dépassée |

## Arborescence
| Chemin | Rôle |
|---|---|
| `referentiels/` | Dictionnaire, référentiel des contrôles (flux, seuil fixe, inclusion dans la note), lignage (flux et chemins), plan de campagne, historique |
| `sql/controles/` | 20 contrôles SQL ANSI sans CTE |
| `sas/00`–`07` | Configuration (avec gabarit ODBC), import démo, contrôles, campagne, variation, rapport, gouvernance, export Qlik |
| `sas/98_verifier.sas`, `sas/99_executer.sas` | Vérification contre la référence ; exécution complète |
| `qdd_s2/moteur.py` | Méthode du mémoire, corrigée |
| `qdd_s2/gouvernance.py` | Couverture du lignage, registre des anomalies, journal |
| `qdd_s2/export_qlik.py`, `app/chargement_qdd.qvs` | Modèle en étoile et script de chargement Qlik |
| `app/` | Atelier HTML : fiches, QCM, vrai/faux, simulateur, campagne, avis, plan 90 jours |

## Écarts au mémoire, et pourquoi
| # | Constat | Traitement |
|---|---|---|
| 1 | `1 − note` est lu comme une incertitude relative, alors qu'un ratio d'anomalies compte des lignes | Ratio pondéré en montant par défaut |
| 2 | `max/min − 1` n'est pas borné et faux avec des montants négatifs ; une note peut devenir négative | Résultat borné ; écart symétrique en option |
| 3 | Moyennes compensatoires | Statuts par donnée et par contrôle, nombre de données hors tolérance, note plancher |
| 4 | Dilution **constatée** : deux contrôles QRT parfaits faisaient passer une donnée du rouge à l'orange | Les contrôles de restitution sont exclus de la note et ont un seuil fixe (0,1 %) avec un statut binaire |
| 5 | Linéarité du SCR non testée | Sensibilité à 4 chocs et indicateur de non-linéarité |
| 6 | Données critiques sans contrôle supposées absentes | Signalées ; option prudente « note 0 » |
| 7 | Cohérence tolérance / criticité non outillée | Vérification bloquante (éq. 12 et 19) |
| 8 | Formule de proratisation (p. 84) incohérente | Non retenue ; analyse de variation par substitutions |
| 9 | Pas de gouvernance (lignage, anomalies, audit) | Couverture des zones de risque, registre avec cycle de vie, journal d'exécution |

Erreurs relevées dans le texte du mémoire :
- p. 21 : le ratio de solvabilité est fonds propres / SCR, et non l'inverse.
- p. 54 : une sensibilité de 10 % signifie que +1 % sur la donnée donne +0,1 % de SCR, et non +10 %.
- Les tableaux 3 à 9 utilisent tantôt 4,57 %, tantôt 5,74 % pour les provisions mathématiques.
- Le tableau 4 reprend les pondérations du tableau 2.
- Le tableau 19 a des colonnes décalées.

## Limites connues
- Le SCR est un jouet ; les corrélations entre segments sont illustratives.
- Une donnée critique à dire d'expert reçoit par convention la sensibilité moyenne : c'est un choix à valider.
- Les états QRT sont simplifiés ; ils ne suivent pas la taxonomie EIOPA.
- Le script Qlik et le gabarit ODBC sont fournis non testés, faute de Qlik et de bases distantes dans l'environnement.
