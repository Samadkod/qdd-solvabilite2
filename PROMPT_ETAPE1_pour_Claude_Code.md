# Étape 1 — Interface « entreprise » de l'Atelier QDD (à coller dans Claude Code)

Contexte : refonte validée par Samadou le 28/11/2026 (maquettes vues dans Cowork).
Sauvegarde déjà faite : branche `sauvegarde-2026-11-28-avant-v2` (copie de `main`).
Règles du dépôt (CLAUDE.md) inchangées : français, données fictives, aucun nom d'employeur, tests verts.

## 0. Travailler sur une branche
```
git checkout main && git pull
git checkout -b refonte-etape1
```

## 1a. Feuille de route allégée — FAIT par Cowork, à appliquer
Appliquer le fichier joint `etape1a_feuille_de_route.patch` :
```
git apply etape1a_feuille_de_route.patch
```
Ce qu'il change (`assurance_feuille.py`, fonction `afficher_feuille_de_route`) :
- les compteurs par statut restent en tête ;
- vue en colonnes « En cours / En attente de décision / Plus tard / À vérifier » : une carte repliable par élément (titre visible, « Pourquoi » et « Prérequis » au clic) ;
- « Fait » regroupé dans un seul volet replié, sous forme de tableau (pas d'expander imbriqué, interdit par Streamlit) ;
- export CSV inchangé.
Vérifié : page exécutée sans erreur (Streamlit AppTest), `tests/test_fiche_assistant.py` vert.

## 1b. Mode démo de l'assistant (à faire)
Objectif : un visiteur sans compte voit l'assistant sans consommer de budget.
- Ajouter un fichier `referentiels/assistant_demo.json` : 4 à 6 questions + réponses réelles déjà générées par l'assistant (mode diagnostic), avec date, campagne, sources consultées, coût d'origine.
- Sur la page Assistant : si l'utilisateur n'est pas connecté (`st.user.is_logged_in` faux, ou absence de secrets d'authentification), afficher un bandeau « Mode démo : réponses préparées à l'avance », les questions de démo en boutons, et la zone de saisie désactivée avec un bouton « Se connecter ».
- Ne jamais appeler l'API en mode démo. Ajouter un test qui le vérifie (faux client qui échoue s'il est appelé).

## 1c. Visite guidée en 2 minutes (à faire)
- Bouton « Visite en 2 min » sur la Synthèse ; 5 étapes : verdict et note → points de vigilance → un contrôle bloquant → l'anomalie et son responsable → une question à l'assistant (démo).
- Implémentation simple : état `st.session_state["visite_etape"]`, encadré d'explication + boutons « Passer » / « Suivant », navigation vers la page concernée. Réutiliser `visite.py` si pertinent.

## 2. Connexion (étape suivante, après validation de l'étape 1)
- Authentification native Streamlit (`st.login` / `st.user`, OIDC Google ou Microsoft). Secrets dans Streamlit Cloud uniquement, jamais dans le dépôt.
- L'assistant en direct n'est accessible qu'une fois connecté ; le plafond mensuel global reste actif.

## 3. Historique durable E14 + rôles + « Mon espace » E16 (ensuite)
- Base PostgreSQL **Neon** (choix validé, au lieu de Supabase) : tables `utilisateurs`, `conversations`, `messages` (campagne, sources consultées, mode, modèle, coût, avis), durée de conservation 12 mois, mention d'information RGPD.
- Rôles : Lecteur, Responsable de contrôle, Administrateur QDD.
- Export d'une conversation vers le dossier de campagne (piste d'audit).

## Fin de chaque étape
Tests verts, puis aperçu avant fusion dans `main` (Streamlit Cloud redéploie `main`). Ne fusionner qu'après le feu vert de Samadou.
