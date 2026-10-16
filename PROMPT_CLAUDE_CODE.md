# Prompt à coller dans Claude Code (sur ton PC, dans le dossier qdd-s2 décompressé)

---

Tu reprends le projet qdd-s2 situé dans ce dossier. Commence par lire CLAUDE.md en entier, puis README.md et sas/README_SAS.md. Ensuite, dans cet ordre :

1. **Vérifier l'état.**
   - Installe les dépendances (`pip install -r requirements.txt`).
   - Lance `python scripts/generer_donnees_btp.py`, `python -m qdd_s2`, `python -m pytest -q` et `python scripts/lint_sas.py`.
   - Confirme que les 32 tests passent et que les valeurs de la campagne N sont celles de CLAUDE.md. Si quelque chose diffère, arrête-toi et explique-moi pourquoi avant de corriger.

2. **Publier sur GitHub.** Mon compte est `Samadkod`.
   - Vérifie que `gh auth status` est connecté. Sinon, guide-moi pour `gh auth login`.
   - Vérifie qu'aucun secret ni fichier lourd n'est suivi : `data/*.duckdb` et `output/` sont dans `.gitignore`.
   - Crée le dépôt public `Samadkod/qdd-solvabilite2` et pousse la branche `main` : `gh repo create Samadkod/qdd-solvabilite2 --public --source=. --remote=origin --push`. Si le dépôt existe déjà, ajoute-le comme remote et pousse.
   - Donne-moi l'URL du dépôt.

3. **Préparer le déploiement Streamlit Community Cloud.**
   - Vérifie que `streamlit_app.py` démarre en local (`streamlit run streamlit_app.py`) et que l'onglet « Campagne live » affiche une note de 97,45 %.
   - Le déploiement final se fait sur share.streamlit.io : *Create app* → dépôt `Samadkod/qdd-solvabilite2`, branche `main`, fichier `streamlit_app.py`. Guide-moi pas à pas et ne prétends pas l'avoir fait toi-même.

4. **Vérifier l'intégration continue.** Le workflow `.github/workflows/tests.yml` lance pytest et `scripts/lint_sas.py` à chaque push. Après le push, vérifie avec `gh run list` qu'il passe au vert. Sinon, corrige la cause et explique-la-moi.

5. **Me faire un compte rendu court :** ce qui a été fait, ce qui a échoué, et ce qui reste à faire de mon côté.

Règles : respecte toutes les règles de méthode et les invariants de parité de CLAUDE.md. Ne modifie aucun calcul sans me demander. Écris en français. Si un résultat ne correspond pas aux valeurs de référence, considère que c'est une régression jusqu'à preuve du contraire.

---

## Étape suivante (plus tard, une fois SAS disponible)
« Exécute ou aide-moi à exécuter `sas/99_executer.sas`. Lis le log et la table `WORK.VERIFICATION`, corrige les écarts dans le SAS sans toucher au Python de référence, puis relance `scripts/lint_sas.py`. »
