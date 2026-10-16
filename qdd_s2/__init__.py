"""qdd_s2 — évaluation quantitative de la qualité des données Solvabilité 2.

Implémentation de la méthode du mémoire de C. Motard (ISFA, 2024),
corrigée et industrialisée.
"""
from .mesures import (ecart_relatif, ecart_symetrique, mesure_rapprochement,
                      mesure_rapprochement_maille, ratio_anomalie, resultat_controle)
from .anteriorite import anteriorite, degrader
from .moteur import Parametres, Evaluation, Etat, evaluer, analyse_variation
from .sensibilite import sensibilites, scr_formule_standard_simplifiee

__version__ = "1.0.0"
