"""Correction bornée sur copie, recontrôle SQL réel, validation déclarative gardée."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
import uuid

import duckdb
import pandas as pd
from qdd_s2.campagne import Config, lancer_campagnes
from lignes_anomalie import lignes
from chargement import execution

RACINE = Path(__file__).resolve().parents[1]
# Scénarios qui vont jusqu'à la validation sur les données fictives (règle, segment), par campagne.
# Vérifié en rejouant toutes les combinaisons ; tests/test_operations_qdd.py contrôle la campagne N.
# N-2 n'en a aucun : ses défauts injectés (C06, R04, Q04) touchent les mêmes données et ne sont réglés qu'en N-1.
ESSAIS_VALIDABLES = {
    'N': [('C05', 'AUTO_FLOTTE'), ('C02', 'RC_DECENNALE')],
    'N-1': [('C05', 'AUTO_FLOTTE'), ('C05', 'DOMMAGES_OUVRAGE'), ('C02', 'RC_DECENNALE')],
    'N-2': [],
}
REGLES = {
    'C02': {'table': 'gestion_contrats', 'id': 'contrat_id', 'champ': 'prime_acquise',
            'condition': 'prime_acquise < 0 OR prime_acquise > prime_emise'},
    'C05': {'table': 'gestion_sinistres', 'id': 'sinistre_id', 'champ': 'provision_dossier',
            'condition': 'provision_dossier < 0'},
}


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def empreinte(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for morceau in iter(lambda: f.read(1024 * 1024), b''):
            h.update(morceau)
    return h.hexdigest()


def candidats(base: Path | str, arrete: str, code: str, maille: str) -> pd.DataFrame:
    r = REGLES[code]
    with duckdb.connect(str(base), read_only=True) as con:
        extra = ', prime_emise AS plafond' if code == 'C02' else ''
        df = con.execute(f"SELECT {r['id']} AS objet, {r['champ']} AS ancienne{extra} FROM {r['table']} "
                         f"WHERE arrete=$a AND segment=$m AND ({r['condition']}) ORDER BY {r['id']}",
                         {'a': arrete, 'm': maille}).df()
        # Un identifiant dupliqué n'est pas un objet modifiable sans clé technique stable.
        comptes = con.execute(f"SELECT {r['id']} AS objet, COUNT(*) AS n FROM {r['table']} "
                              "WHERE arrete=$a AND segment=$m GROUP BY 1", {'a': arrete, 'm': maille}).df()
    df = df.merge(comptes, on='objet')
    df['modifiable'] = df.n == 1
    return df.drop(columns='n')


def declarer(c: dict, base: Path | str, code: str, maille: str, edits: list[dict],
             auteur: str, justification: str, config: dict, methode: dict) -> dict:
    if not auteur.strip() or not justification.strip():
        raise ValueError('Auteur et justification requis.')
    if not edits or len({e['objet'] for e in edits}) != len(edits):
        raise ValueError('Choisir au moins un objet unique à modifier.')
    valides = candidats(base, c['date'], code, maille).set_index('objet')
    nettoyes = []
    for e in edits:
        if e['objet'] not in valides.index:
            raise ValueError('Objet absent des anomalies de cet arrêté / segment.')
        row = valides.loc[e['objet']]
        if isinstance(row, pd.DataFrame) or not row.modifiable:
            raise ValueError('Objet dupliqué : correction non supportée sans clé technique stable.')
        valeur = float(e['nouvelle'])
        if not math.isfinite(valeur) or valeur < 0 or (code == 'C02' and valeur > row.plafond):
            raise ValueError('Valeur invalide : montant fini ≥ 0, et prime acquise ≤ prime émise.')
        if valeur == float(row.ancienne):
            raise ValueError('La valeur proposée ne change pas la donnée.')
        nettoyes.append({'objet': str(e['objet']), 'ancienne': float(row.ancienne), 'nouvelle': valeur})
    if not config.get('role_correction', '').strip() or not config.get('role_validation', '').strip():
        raise ValueError('Les deux rôles doivent être nommés.')
    return {'schema': 1, 'id': str(uuid.uuid4()), 'campagne': c['campagne'], 'date': str(c['date']),
            'code': code, 'maille': maille, 'edits': nettoyes, 'auteur': auteur.strip(),
            'justification': justification.strip(), 'configuration': dict(config), 'methode': dict(methode),
            'params': asdict(c['params']), 'source_sha256': empreinte(base),
            'statut': 'Correction déclarée · à recontrôler', 'preuve': None,
            'evenements': [{'date': maintenant(), 'action': 'Déclaration', 'acteur': auteur.strip()}]}


def rejouer(dossier: dict, base: Path | str, params) -> dict:
    if dossier['statut'] == 'Validée dans le bac à sable':
        raise ValueError('Scénario déjà validé : créer une nouvelle déclaration pour toute modification.')
    if empreinte(base) != dossier['source_sha256'] or asdict(params) != dossier['params']:
        raise ValueError('Source ou paramètres modifiés : créer une nouvelle déclaration.')
    r = REGLES[dossier['code']]
    with tempfile.TemporaryDirectory(prefix='qdd_scenario_') as tmp:
        tmp = Path(tmp)
        copie = tmp / 'scenario.duckdb'
        shutil.copyfile(base, copie)
        refs = tmp / 'referentiels'
        shutil.copytree(RACINE / 'referentiels', refs)
        plan = pd.read_csv(refs / 'plan_campagnes.csv')
        # Recontrôle neuf des 20 règles de l'arrêté sélectionné, pas une modification du plan historique.
        plan.loc[plan.campagne == dossier['campagne'], 'controles_non_realises'] = ''
        plan.to_csv(refs / 'plan_campagnes.csv', index=False)
        kw = dict(referentiels=refs, params=params, **dossier['methode'])
        avant = next(c for c in lancer_campagnes(Config(base=Path(base), **kw))[0]
                     if c.campagne == dossier['campagne'])
        with duckdb.connect(str(copie)) as con:
            con.execute('BEGIN TRANSACTION')
            for e in dossier['edits']:
                cle = {'a': dossier['date'], 'm': dossier['maille'], 'o': e['objet']}
                row = con.execute(f"SELECT {r['champ']} FROM {r['table']} WHERE arrete=$a AND segment=$m "
                                  f"AND {r['id']}=$o", cle).fetchall()
                if len(row) != 1 or float(row[0][0]) != e['ancienne']:
                    raise ValueError('Objet ambigu ou valeur ancienne différente : scénario refusé.')
                con.execute(f"UPDATE {r['table']} SET {r['champ']}=$v WHERE arrete=$a AND segment=$m "
                            f"AND {r['id']}=$o", cle | {'v': e['nouvelle']})
            con.execute('COMMIT')
        ref = pd.read_csv(refs / 'referentiel_controles.csv')
        exe = execution(copie, dossier['date'], ref)
        if (exe.Statut != 'Exécuté').any():
            raise ValueError('Échec technique : validation impossible ; aucune preuve conforme créée.')
        apres = next(c for c in lancer_campagnes(Config(base=copie, **kw))[0]
                     if c.campagne == dossier['campagne'])
        a = avant.evaluation.controles.set_index('controle_id')
        b = apres.evaluation.controles.set_index('controle_id')
        target = f"{dossier['code']}|{dossier['maille']}"
        did = b.loc[target, 'donnee_id']
        affected = b[b.donnee_id == did].index.tolist()
        comparaison = []
        for pid in b.index:
            comparaison.append({'Point': pid, 'Donnée': b.loc[pid, 'donnee_id'],
                                'Lié à la donnée corrigée': pid in affected,
                                'Avant': float(a.loc[pid, 'resultat']), 'Après': float(b.loc[pid, 'resultat']),
                                'Seuil après': float(b.loc[pid, 'seuil']),
                                'Statut avant': a.loc[pid, 'statut'], 'Statut après': b.loc[pid, 'statut'],
                                'Preuve avant': str(a.loc[pid, 'detail']), 'Preuve après': str(b.loc[pid, 'detail'])})
        blocages = []
        for pid in affected:
            if pd.isna(b.loc[pid, 'seuil']):
                blocages.append(f'{pid} : seuil QDD non calculé (hors périmètre de notation), validation non établie')
            elif b.loc[pid, 'resultat'] < b.loc[pid, 'seuil']:
                av, ap, sl = (float(a.loc[pid, 'resultat']), float(b.loc[pid, 'resultat']), float(b.loc[pid, 'seuil']))
                pc = lambda v: f'{v * 100:.2f} %'.replace('.', ',')
                if av < sl and ap <= av + 1e-10:
                    blocages.append(f'{pid} : déjà sous le seuil avant la correction ({pc(av)} pour {pc(sl)} exigé) '
                                    'et non réglé par ce scénario ; la donnée corrigée reste donc non conforme '
                                    '(autre défaut, à traiter à part)')
                else:
                    blocages.append(f'{pid} : sous le seuil après la correction ({pc(ap)} pour {pc(sl)} exigé)')
        for pid in b.index:
            if a.loc[pid, 'resultat'] >= a.loc[pid, 'seuil'] and b.loc[pid, 'resultat'] < b.loc[pid, 'seuil']:
                blocages.append(f'{pid} : nouvelle non-conformité')
            elif (a.loc[pid, 'resultat'] < a.loc[pid, 'seuil'] and
                  b.loc[pid, 'resultat'] < a.loc[pid, 'resultat'] - 1e-10):
                pc = lambda v: f'{v * 100:.2f} %'.replace('.', ',')
                blocages.append(f'{pid} : déjà sous le seuil, et encore dégradé par la correction '
                                f'({pc(float(a.loc[pid, "resultat"]))} avant, {pc(float(b.loc[pid, "resultat"]))} après)')
        reste = lignes(copie, dossier['date'])
        reste = reste[(reste.controle == dossier['code']) & (reste.maille == dossier['maille'])]
        # Une validation d'atelier exige aussi zéro ligne fautive pour la règle et la maille ciblées.
        if not reste.empty:
            blocages.append(f'{int(reste.poids.sum())} ligne(s) encore en anomalie sur la cible')
        preuve = {'date': maintenant(), 'comparaison': comparaison, 'executions': exe.to_dict('records'),
                  'controles_lies': affected, 'blocages': sorted(set(blocages)),
                  'note_avant_recontrole': avant.evaluation.indicateurs['note'],
                  'note_apres': apres.evaluation.indicateurs['note'],
                  'scr_avant_simplifie': avant.scr_ref, 'scr_apres_simplifie': apres.scr_ref,
                  'source_sha256': empreinte(base), 'copie_sha256': empreinte(copie),
                  'fichiers_sha256': {str(p.relative_to(RACINE)): empreinte(p) for folder in
                                     ('qdd_s2', 'operations_qdd', 'referentiels', 'sql/controles', 'sql/lignes')
                                     for p in sorted((RACINE / folder).rglob('*')) if p.suffix in ('.py', '.sql', '.csv')},
                  'plan_recontrole': plan.to_dict('records'),
                  'limite': '20 règles SQL rejouées ; seuils recalculés par le moteur. La note avant est celle '
                            'du recontrôle neuf, pas celle de la campagne historique. Aucun flux aval propagé automatiquement.'}
    dossier['preuve'] = preuve
    dossier['statut'] = 'Recontrôle bloquant' if blocages else 'Recontrôle réussi · à valider'
    dossier['evenements'].append({'date': maintenant(), 'action': 'Recontrôle réel', 'acteur': dossier['auteur'],
                                 'blocages': preuve['blocages']})
    return dossier


def valider(dossier: dict, acteur: str, role: str, commentaire: str) -> dict:
    p = dossier.get('preuve')
    if dossier['statut'] != 'Recontrôle réussi · à valider' or not p or p['blocages']:
        raise ValueError('Un recontrôle réussi sans blocage est obligatoire.')
    # Refuser une preuve devenue obsolète après mise à jour du code ou des référentiels.
    for relatif, attendu in p.get('fichiers_sha256', {}).items():
        chemin = RACINE / relatif
        if not chemin.is_file() or empreinte(chemin) != attendu:
            raise ValueError('Code ou référentiel modifié depuis le recontrôle : relancer les contrôles.')
    if not acteur.strip() or not commentaire.strip() or role != dossier['configuration']['role_validation']:
        raise ValueError('Validateur, rôle attendu et commentaire requis.')
    if dossier['configuration']['separation'] and acteur.strip().casefold() == dossier['auteur'].casefold():
        raise ValueError('La séparation déclarative impose un validateur différent du correcteur.')
    dossier['statut'] = 'Validée dans le bac à sable'
    dossier['evenements'].append({'date': maintenant(), 'action': 'Validation déclarative', 'acteur': acteur.strip(),
                                 'role': role, 'commentaire': commentaire.strip()})
    return dossier


COLONNES_FICHE = ['Campagne', 'Arrêté', 'Donnée', 'Contrôle', 'Segment', 'Limite constatée', 'Risque couvert',
                  'Données en défaut conservées', 'Empreinte SHA-256 de l’archive', 'Méthode d’ajustement',
                  'Valeurs ajustées', 'Justification', 'Responsable de la correction', 'Responsable de la validation',
                  'Déclaré le (UTC)', 'Validé le (UTC)', 'Statut', 'Blocages au recontrôle']


def fiche_ajustement(dossier: dict) -> dict:
    """Fiche d'ajustement d'un scénario (notice QDD, points 36 et 37) : limite, méthode, responsables.

    Tout vient du scénario, du référentiel des contrôles et du manifeste des données en défaut : rien n'est saisi
    à part. Une fiche de scénario non validé le dit ; elle ne vaut pas ajustement réel des données de production.
    """
    from archives_defaut import archive
    from lignes_anomalie import MESSAGES

    ref = pd.read_csv(RACINE / 'referentiels' / 'referentiel_controles.csv', dtype=str,
                      keep_default_na=False).set_index('controle_id').loc[dossier['code']]
    arch = archive(dossier['campagne'], dossier['date'])
    val = next((e for e in reversed(dossier['evenements']) if e.get('action') == 'Validation déclarative'), None)
    conf = dossier['configuration']
    blocages = (dossier.get('preuve') or {}).get('blocages', [])
    n = len(dossier['edits'])
    return dict(zip(COLONNES_FICHE, [
        dossier['campagne'], dossier['date'], ref['donnee_id'].format(maille=dossier['maille']), dossier['code'],
        dossier['maille'],
        f"{MESSAGES.get(dossier['code'], ref['libelle'])} {n} objet(s) en défaut ajusté(s) par ce scénario.",
        ref['risque_couvert'],
        arch['fichier'] if arch else 'Non archivées',
        arch['sha256'] if arch else '',
        'Correction de valeur objet par objet sur une copie de la base, puis recontrôle des 20 règles ; la base de '
        'référence et l’archive des données en défaut ne sont pas modifiées.',
        ' ; '.join(f"{e['objet']} : {e['ancienne']:.2f} → {e['nouvelle']:.2f}" for e in dossier['edits']),
        dossier['justification'],
        f"{dossier['auteur']} ({conf.get('role_correction', '')})",
        f"{val['acteur']} ({val.get('role', '')})" if val else 'Non validé',
        dossier['evenements'][0]['date'],
        val['date'] if val else '',
        dossier['statut'],
        ' ; '.join(blocages),
    ]))


def fiches_ajustement(scenarios: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([fiche_ajustement(s) for s in scenarios], columns=COLONNES_FICHE)
