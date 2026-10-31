# Déployer la copie assurance

Créer une nouvelle application Streamlit Community Cloud, sans modifier l'application originale.

- Dépôt : `Samadkod/qdd-solvabilite2`
- Branche : `design-assurance`
- Fichier d'entrée : `streamlit_assurance.py`
- Version Python recommandée : 3.13 (version utilisée pour les vérifications locales)

L'application utilise les dépendances existantes de `requirements.txt`, génère des données fictives et ne nécessite aucun secret. Le choix du sous-domaine dépend de sa disponibilité sur Streamlit.

Les 17 pages du point d'entrée de publication ont été vérifiées localement. La synthèse, le sélecteur de campagne et le détail des données critiques fonctionnent. Les moteurs Python, SQL/SAS et l'entrée historique `streamlit_app.py` restent inchangés.

Le code de la copie est disponible sur GitHub ; sa présence dans cette branche ne constitue pas, à elle seule, un déploiement Streamlit. La branche `main` et l'application originale restent inchangées.

Pour lancer localement :

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_assurance.py
```
