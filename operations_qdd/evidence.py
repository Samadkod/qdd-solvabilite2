"""Dossier de campagne reproductible ; manifeste d'intégrité, pas certification."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
from io import BytesIO
import json
import math
import numbers
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd
from .diagnostic import diagnostic
from .correction import empreinte, fiches_ajustement, maintenant

RACINE = Path(__file__).resolve().parents[1]


def json_bytes(value) -> bytes:
    def nettoyer(x):
        if isinstance(x, dict):
            return {str(k): nettoyer(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [nettoyer(v) for v in x]
        if isinstance(x, numbers.Real) and not math.isfinite(x):
            return None  # absent du moteur, surtout seuils hors périmètre ; jamais « zéro »
        return x
    return json.dumps(nettoyer(value), ensure_ascii=False, indent=2, default=str, allow_nan=False).encode('utf-8')


def completude(scenarios: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {'Pièce': 'Résultats et référentiels fictifs', 'État': 'Disponible', 'Limite': 'Référence calculée dans l’application'},
        {'Pièce': 'Identité et droits des intervenants', 'État': 'Manquant', 'Limite': 'Noms/rôles déclaratifs, aucune authentification'},
        {'Pièce': 'Scénarios de correction', 'État': 'Disponible' if scenarios else 'Non produit', 'Limite': 'Copie fictive uniquement'},
        {'Pièce': 'Recontrôles des scénarios', 'État': 'Disponible' if scenarios and all(s.get('preuve') for s in scenarios) else 'Incomplet',
         'Limite': 'Un recontrôle disponible peut être bloquant ; consulter chaque preuve'},
        {'Pièce': 'Validation des scénarios', 'État': 'Disponible · déclarative' if scenarios and all(
            s['statut'] == 'Validée dans le bac à sable' for s in scenarios) else 'Non acquise',
         'Limite': 'Pas une validation métier de campagne ni une signature'},
        {'Pièce': 'Validation métier de campagne', 'État': 'Manquant', 'Limite': 'À obtenir dans l’organisation'},
        {'Pièce': 'Journal durable et horodatage de confiance', 'État': 'Manquant', 'Limite': 'Session et horloge serveur seulement'},
        {'Pièce': 'Preuves de propagation aval', 'État': 'Manquant', 'Limite': 'Lignage déclaré ; pas de chaîne aval rejouée'},
    ])


def dossier_zip(c: dict, prev: dict | None, lignes: pd.DataFrame, volumes: pd.DataFrame,
                executions: pd.DataFrame, xlsx: bytes, base: Path | str,
                scenarios: list[dict], methode: dict) -> bytes:
    payload = {}
    tableaux = {'donnees': c['donnees'], 'controles': c['controles'], 'anomalies': c['registre'],
                'lignes_detectees': lignes, 'lignage_couverture': c['couverture'],
                'diagnostic': diagnostic(c, lignes, prev), 'volumetries': volumes,
                'execution_technique_SQL': executions, 'completude': completude(scenarios),
                'fiches_ajustement': fiches_ajustement(scenarios)}
    for nom, df in tableaux.items():
        payload[f'{nom}.csv'] = df.to_csv(index=False, sep=';').encode('utf-8-sig')
    if c.get('niveau2') is not None:
        payload['controle_niveau2.csv'] = c['niveau2'].to_csv(index=False, sep=';').encode('utf-8-sig')
    if c.get('document_cadre'):
        payload['document_cadre.md'] = c['document_cadre'].encode('utf-8')
    payload['journal_reference.json'] = json_bytes(c['journal'])
    payload['scenarios_et_evenements.json'] = json_bytes(scenarios)
    payload['rapport_reference_3_campagnes.xlsx'] = xlsx
    for folder in ('referentiels', 'sql/controles', 'sql/lignes', 'archives/donnees_en_defaut'):
        for p in sorted((RACINE / folder).rglob('*')):
            if p.suffix in ('.sql', '.csv', '.json'):
                payload[str(p.relative_to(RACINE))] = p.read_bytes()
    payload['LIRE-MOI.md'] = (
        f'# Dossier QDD fictif — {c["campagne"]} / {c["date"]}\n\n'
        'Les CSV correspondent à la campagne sélectionnée ; le rapport Excel contient les trois campagnes de référence.\n\n'
        'La campagne historique et les scénarios sont distincts. Les scénarios ne modifient ni le registre ni le rapport '
        'de référence. Les 20 règles sont rejouées dans le bac à sable même si le plan historique en omet certaines ; '
        'comparer avant/après de recontrôle, pas directement la note historique.\n\n'
        'execution_technique_SQL.csv prouve un rejeu technique des requêtes, pas leur réalisation dans le plan historique. '
        'Les lignes détectées incluent aussi les règles non réalisées dans ce plan.\n\n'
        'Les montants de lignes ne mesurent pas une perte. SCR simplifié non réglementaire, QRT simplifiés hors taxonomie. '
        'Aucune preuve de conformité ACPR/CAC. Voir completude.csv pour les pièces manquantes.\n\n'
        'Le manifeste permet de vérifier les empreintes des fichiers exportés ; il n’est ni signé ni ancré dans un journal '
        'immuable. Les identités, décisions et horaires sont déclaratifs. La session est volatile : conserver cet export.\n'
    ).encode('utf-8')
    manifest = {'schema': 1, 'export_utc': maintenant(), 'campagne': c['campagne'], 'arrete': str(c['date']),
                'donnees': '100 % fictives', 'params_moteur': asdict(c['params']), 'methode': methode,
                'source_sha256': empreinte(base),
                'code_sha256': {str(p.relative_to(RACINE)): empreinte(p) for p in sorted(RACINE.rglob('*.py'))
                                if '.git' not in p.parts and '__pycache__' not in p.parts},
                'fichiers_sha256': {nom: hashlib.sha256(data).hexdigest() for nom, data in payload.items()},
                'perimetre': 'CSV sélectionnés + Excel 3 campagnes + scénarios séparés ; aucune conformité attestée'}
    payload['manifest.json'] = json_bytes(manifest)
    buf = BytesIO()
    with ZipFile(buf, 'w', ZIP_DEFLATED) as z:
        for nom, data in payload.items():
            z.writestr(nom, data)
    return buf.getvalue()
