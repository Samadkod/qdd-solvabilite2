# Application unique

Depuis novembre 2026, la version « assurance » est l'application : tout est dans `streamlit_app.py`.

- Application principale : dépôt `Samadkod/qdd-solvabilite2`, branche `main`, fichier `streamlit_app.py`.
- `streamlit_assurance.py` ne fait que lancer `streamlit_app.py` : un déploiement qui pointait vers lui
  continue de fonctionner et affiche la même application.

Aucun secret n'est nécessaire ; les données sont générées (fictives) au démarrage.

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```
