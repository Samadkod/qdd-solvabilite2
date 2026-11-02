# Extensions opérationnelles de l’Atelier QDD

Les quatre axes sont disponibles via `streamlit_assurance.py`, sur la branche
`design-assurance`. Le moteur, l’entrée historique et les référentiels originaux
restent inchangés. Toutes les données sont fictives.

## Où les trouver

| Fonction | Emplacement |
|---|---|
| Diagnostic explicable | Synthèse → Diagnostic explicable de la campagne |
| Correction et recontrôle | Exploitation → Atelier de résolution ; également Documentation → Atelier QDD |
| Dossier de preuves | Exploitation → Dossier de campagne ; également Synthèse |
| Analyse d’impact | Lignage & dictionnaire → Analyse d’impact |
| Copilote futur | Feuille de route → E12, Claude envisagé, aucun service branché |

## Essai de bout en bout

1. Garder la campagne N et les paramètres par défaut.
2. Dans Atelier de résolution, choisir C05 et AUTO_FLOTTE.
3. Choisir tous les objets modifiables du segment.
4. Déclarer un correcteur fictif, une nouvelle valeur 0 et une justification
   pédagogique. **Zéro n’est pas une valeur métier prouvée.** Confirmer le périmètre fictif.
5. Déclarer puis relancer les 20 contrôles : les requêtes SQL tournent réellement
   sur une copie DuckDB privée à la session d’exécution, supprimée ensuite.
6. Examiner les points liés et tous les résultats. Le scénario peut être validé
   par un nom déclaré différent, avec un commentaire. Cela ne clôture aucune
   anomalie du registre historique.
7. Dans Dossier de campagne, préparer puis télécharger le ZIP. Les preuves du
   scénario sont incluses séparément de la campagne de référence.

## Conditions de validation

- Un recontrôle réel réussi et une preuve non obsolète sont obligatoires.
- Aucune ligne fautive restante sur la règle et le segment ciblés.
- Tous les points associés à la donnée corrigée disposent d’un seuil QDD
  calculé et restent au-dessus de ce seuil.
- Aucune nouvelle non-conformité ailleurs et aucune diminution du résultat
  d’un point déjà sous seuil. Les variations de points encore conformes
  sont montrées, sans bloquer à elles seules la validation.
- Auteur, rôle de validation et commentaire requis ; séparation déclarative
  configurable, activée par défaut.

Une correction partielle peut rester bloquée. Une donnée non critique peut
avoir des défauts de règle mais aucun seuil QDD de notation : cela est indiqué
explicitement, sans conclure automatiquement à la conformité. Étendre les
seuils relève d’une décision de méthode, pas d’une correction silencieuse.

## Comparaison et limites

Le bac à sable rejoue les 20 règles à l’arrêté choisi, même si le plan historique
en omettait certaines. La note « avant » est donc celle de ce recontrôle neuf,
pas nécessairement celle de la campagne historique. Les seuils et sensibilités
sont recalculés avec le même moteur. Aucun flux aval n’est corrigé automatiquement.

C02 et C05 sont les seules corrections prises en charge. Les montants proposés
sont manuels, non une vérité métier reconstruite. Les identifiants dupliqués
sont exclus faute de clé technique stable. Les autres règles restent consultables.

Le lignage décrit les relations connues, avec des flux parfois parallèles.
Il ne prouve pas leur exécution et n’invente aucun effet BE, ORSA, tarification
ou SCR réglementaire. Les causes métier restent à instruire.

Le ZIP contient les CSV de la campagne sélectionnée, le rapport Excel des trois
campagnes de référence, les SQL/référentiels, les scénarios et événements, les
lacunes de preuve et un manifeste SHA-256. Les valeurs absentes du moteur sont
exportées en `null` JSON, pas en zéro. Le manifeste n’est ni signé ni immuable.

**La session est volatile.** Exporter avant de quitter. Les noms/rôles ne sont pas
authentifiés : aucune validation métier de campagne, signature ou conformité
ACPR/CAC n’est attestée. Ne pas saisir de données réelles dans l’application publique.
Pour l’entreprise : hébergement approuvé, stockage durable, authentification,
habilitations et audit ; voir E13 et le statut de correction d’entreprise E9.

## Vérification

- 121 tests Python réussis : 106 historiques et 15 nouveaux cas d’extension.
- 19 pages sans exception via Streamlit AppTest.
- Parcours réel dans Chrome : déclaration, recontrôle, validation, téléchargement ZIP.
- Séparation déclarative et corrections partielles bloquantes testées.
- ZIP téléchargé : intégrité et toutes les empreintes de fichiers vérifiées.
- Vue mobile 390 px sans débordement du document ; note N conservée à 97,49 %.
- Vérification SAS historique F11 préservée : 59/59 valeurs, SAS OnDemand du 23/10/2026.
  Les nouveaux écrans de workflow ne constituent pas une nouvelle exécution SAS.

Exécution locale :

```bash
pip install -r requirements.txt pytest
python scripts/generer_donnees_btp.py
python -m pytest -q
streamlit run streamlit_assurance.py
```

La publication Streamlit existante conserve son point d’entrée ; aucun nouveau
service, stockage ou fournisseur IA n’est nécessaire pour cette version.
