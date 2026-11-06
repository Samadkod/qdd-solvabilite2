"""Constats traçables : aucune inférence de cause métier ou de perte financière."""
from __future__ import annotations

import pandas as pd
from lignes_anomalie import MESSAGES


def diagnostic(c: dict, lignes: pd.DataFrame, prev: dict | None = None) -> pd.DataFrame:
    rows = []
    anciennes = prev['controles'].set_index('controle_id') if prev else None
    donnees = c['donnees'].set_index('donnee_id')
    for r in c['controles'].itertuples():
        code, maille = r.controle_id.split('|', 1)
        d = donnees.loc[r.donnee_id]
        lig = lignes[(lignes.controle == code) & (lignes.maille == maille)]
        hors_perimetre = pd.isna(r.seuil)
        if r.realise_campagne and (r.statut == 'vert' or (hors_perimetre and lig.empty)):
            continue
        actuel = bool(r.realise_campagne)
        faits = []
        if hors_perimetre:
            faits.append('Donnée hors périmètre de notation critique : pas de seuil QDD calculé ; '
                         'les lignes détectées signalent un défaut de règle, pas un statut moteur non conforme.')
        if not actuel:
            faits.append('Non réalisé dans le plan de cette campagne ; résultat historique dégradé par antériorité.')
        if r.resultat < r.seuil:
            faits.append(f'Résultat retenu {r.resultat * 100:.2f} % < seuil {r.seuil * 100:.2f} %.'.replace('.', ',', 2))
        if pd.notna(r.resultat_brut) and r.resultat < r.resultat_brut:
            faits.append('La dégradation temporelle diminue le résultat brut connu.')
        avant = anciennes.loc[r.controle_id] if anciennes is not None and r.controle_id in anciennes.index else None
        delta = float(r.resultat - avant.resultat) if avant is not None else None
        recurrent = avant is not None and avant.statut in ('rouge', 'orange') and r.statut in ('rouge', 'orange')
        rows.append({
            'Point': r.controle_id, 'Donnée': r.donnee_id, 'Critique': bool(d.critique),
            'Statut moteur': 'Hors périmètre note' if hors_perimetre else r.statut, 'Réalisé campagne': actuel,
            'Priorité de revue': '1 · Critique hors seuil' if d.critique and r.resultat < r.seuil else
                                ('2 · Non réalisé' if not actuel else '3 · Autre écart'),
            'Constat': ' '.join(faits) or 'Point à surveiller selon le statut du moteur.',
            'Règle': MESSAGES.get(code, r.libelle), 'Résultat brut': r.resultat_brut,
            'Résultat retenu': r.resultat, 'Seuil': r.seuil, 'Antériorité': r.anteriorite,
            'Écart depuis précédente (pt)': None if delta is None else delta * 100,
            'Écart récurrent': bool(recurrent), 'Lignes détectées à cet arrêté': int(lig.poids.sum()),
            'Preuve moteur': str(r.detail), 'Dernière réalisation': str(r.date_derniere_real),
            'Responsable référentiel': r.responsable,
            'Cause métier': 'Non déterminée : à instruire avec le propriétaire.',
        })
    cols = ['Point', 'Donnée', 'Critique', 'Statut moteur', 'Réalisé campagne', 'Priorité de revue',
            'Constat', 'Règle', 'Résultat brut', 'Résultat retenu', 'Seuil', 'Antériorité',
            'Écart depuis précédente (pt)', 'Écart récurrent', 'Lignes détectées à cet arrêté',
            'Preuve moteur', 'Dernière réalisation', 'Responsable référentiel', 'Cause métier']
    return pd.DataFrame(rows, columns=cols).sort_values(['Priorité de revue', 'Point']).reset_index(drop=True)


def impact(c: dict, donnee_id: str) -> dict:
    """Jointures du lignage déclaré ; ordre ne signifie pas propagation financière."""
    d = c['donnees'].set_index('donnee_id').loc[donnee_id]
    parcours = c['couverture'][c['couverture'].donnee_id == donnee_id].sort_values('ordre').copy()
    controles = c['controles'][c['controles'].donnee_id == donnee_id].copy()
    lacunes = parcours[parcours.zone_risque & ~parcours.couvert].copy()
    return {'donnee': d.to_dict(), 'parcours': parcours, 'controles': controles,
            'lacunes': lacunes, 'usages': str(d.get('usage', 'Non documenté')),
            'restitutions': str(d.get('etats_qrt', 'Non documenté')),
            'limite': 'Liens déclarés, pas une preuve de propagation exécutée. Pas de dépendance champ/table '
                      'ou de chiffrage BE, ORSA, tarification ou SCR réglementaire dans ce lignage.'}
