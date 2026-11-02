"""Tests des extensions assurance ; aucun remplacement des tests du moteur."""
from copy import deepcopy
from dataclasses import asdict
from io import BytesIO
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from qdd_s2.campagne import Config, lancer_campagnes
from qdd_s2.rapport_excel import ecrire_rapport
from scripts.generer_donnees_btp import generer
from lignes_anomalie import lignes, referentiel
from chargement import execution, volumetrie
from operations_qdd.diagnostic import diagnostic, impact
from operations_qdd.correction import candidats, declarer, rejouer, valider, empreinte
from operations_qdd.evidence import dossier_zip, completude

METHODE = {'methode_ecart': 'memoire', 'ponderation_montant': True}
ROLES = {'role_correction': 'Propriétaire', 'role_validation': 'QDD', 'separation': True}


@pytest.fixture(scope='module')
def contexte(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('operations')
    base = tmp / 'fictif.duckdb'
    generer(base)
    camps, var = lancer_campagnes(Config(base=base))
    out = []
    for r in camps:
        out.append({'campagne': r.campagne, 'date': r.date_arrete, 'params': r.evaluation.params,
                    'ind': r.evaluation.indicateurs, 'donnees': r.evaluation.donnees.reset_index(),
                    'controles': r.evaluation.controles, 'registre': r.registre, 'couverture': r.couverture,
                    'journal': r.journal})
    rapport = tmp / 'rapport.xlsx'
    ecrire_rapport(camps, var, rapport)
    return base, out, rapport.read_bytes()


def scenario(contexte, tous=True):
    base, camps, _ = contexte
    c = camps[-1]
    df = candidats(base, c['date'], 'C05', 'AUTO_FLOTTE')
    if not tous:
        df = df.iloc[:1]
    return declarer(c, base, 'C05', 'AUTO_FLOTTE', [{'objet': x, 'nouvelle': 0} for x in df.objet],
                    'Alice', 'Pièce fictive P-001 : hypothèse de remise à zéro pour apprentissage', ROLES, METHODE)


def test_diagnostic_trace_resultat_historique(contexte):
    base, camps, _ = contexte
    c, p = camps[-1], camps[-2]
    df = diagnostic(c, lignes(base, c['date']), p)
    assert not df.empty
    assert df.Point.is_unique
    row = df.set_index('Point').loc['R04|RC_DECENNALE']
    assert not row['Réalisé campagne']
    assert 'historique' in row.Constat
    assert row['Cause métier'].startswith('Non déterminée')
    assert row['Résultat retenu'] == c['controles'].set_index('controle_id').loc[row.name, 'resultat']


def test_diagnostic_aucun_ecart(contexte):
    _, camps, _ = contexte
    c = dict(camps[-1])
    c['controles'] = c['controles'].assign(statut='vert', realise_campagne=True)
    assert diagnostic(c, pd.DataFrame(columns=['controle', 'maille', 'poids'])).empty


def test_impact_jointures_et_lacunes(contexte):
    _, camps, _ = contexte
    im = impact(camps[-1], 'provisions_sinistres_AUTO_FLOTTE')
    assert set(im['parcours'].flux_id) == {'F14', 'F05', 'F06', 'F07', 'F08', 'F09'}
    assert 'F09' in set(im['lacunes'].flux_id)
    assert 'S.17.01' in im['restitutions']
    assert im['controles'].donnee_id.eq('provisions_sinistres_AUTO_FLOTTE').all()
    assert 'pas une preuve' in im['limite']


@pytest.mark.parametrize('nouvelle', [-1, float('nan'), float('inf')])
def test_valeurs_invalides(contexte, nouvelle):
    base, camps, _ = contexte
    df = candidats(base, camps[-1]['date'], 'C05', 'AUTO_FLOTTE')
    with pytest.raises(ValueError):
        declarer(camps[-1], base, 'C05', 'AUTO_FLOTTE', [{'objet': df.objet.iloc[0], 'nouvelle': nouvelle}],
                 'Alice', 'Pièce', ROLES, METHODE)


def test_c02_plafond_et_objet_hors_segment(contexte):
    base, camps, _ = contexte
    df = candidats(base, camps[-1]['date'], 'C02', 'AUTO_FLOTTE')
    with pytest.raises(ValueError, match='Valeur invalide'):
        declarer(camps[-1], base, 'C02', 'AUTO_FLOTTE', [{'objet': df.objet.iloc[0], 'nouvelle': 1e12}],
                 'Alice', 'Pièce', ROLES, METHODE)
    with pytest.raises(ValueError, match='Objet absent'):
        declarer(camps[-1], base, 'C02', 'AUTO_FLOTTE', [{'objet': 'RC000172', 'nouvelle': 0}],
                 'Alice', 'Pièce', ROLES, METHODE)


def test_declaration_sans_preuve_ne_valide_pas(contexte):
    record = scenario(contexte)
    assert record['preuve'] is None
    with pytest.raises(ValueError, match='recontrôle réussi'):
        valider(record, 'Bob', 'QDD', 'OK')


def test_recontrole_reel_validation_et_reference_intacte(contexte):
    base, camps, _ = contexte
    sha = empreinte(base)
    s = scenario(contexte)
    rejouer(s, base, camps[-1]['params'])
    assert empreinte(base) == sha
    assert s['statut'] == 'Recontrôle réussi · à valider'
    assert len(s['preuve']['executions']) == 20
    assert not s['preuve']['blocages']
    compare = pd.DataFrame(s['preuve']['comparaison']).set_index('Point')
    assert compare.loc['C05|AUTO_FLOTTE', 'Après'] == 1
    assert compare.loc['C05|AUTO_FLOTTE', 'Avant'] < 1
    assert 'Q02|AUTO_FLOTTE' in s['preuve']['controles_lies']
    with pytest.raises(ValueError, match='validateur différent'):
        valider(s, 'alice', 'QDD', 'OK')
    with pytest.raises(ValueError, match='rôle attendu'):
        valider(s, 'Bob', 'Autre rôle', 'OK')
    stale = deepcopy(s)
    stale['preuve']['fichiers_sha256']['referentiels/plan_campagnes.csv'] = 'invalide'
    with pytest.raises(ValueError, match='modifié'):
        valider(stale, 'Bob', 'QDD', 'OK')
    valider(s, 'Bob', 'QDD', 'Revu uniquement pour ce scénario fictif')
    assert s['statut'] == 'Validée dans le bac à sable'
    assert len(s['evenements']) == 3
    with pytest.raises(ValueError, match='déjà validé'):
        rejouer(s, base, camps[-1]['params'])
    # Résultats historiques inchangés, y compris les clôtures du registre.
    fresh = lancer_campagnes(Config(base=base))[0][-1]
    pd.testing.assert_frame_equal(fresh.evaluation.controles, camps[-1]['controles'])
    pd.testing.assert_frame_equal(fresh.registre, camps[-1]['registre'])


def test_correction_partielle_bloquee(contexte):
    base, camps, _ = contexte
    s = scenario(contexte, tous=False)
    rejouer(s, base, camps[-1]['params'])
    assert s['statut'] == 'Recontrôle bloquant'
    assert any('encore en anomalie' in x for x in s['preuve']['blocages'])
    with pytest.raises(ValueError):
        valider(s, 'Bob', 'QDD', 'OK')


def test_source_ou_params_obsoletes_refuses(contexte):
    base, camps, _ = contexte
    s = scenario(contexte)
    s['source_sha256'] = 'autre source'
    with pytest.raises(ValueError, match='Source ou paramètres'):
        rejouer(s, base, camps[-1]['params'])
    s = scenario(contexte)
    s['params']['coef_degradation'] += 0.01
    with pytest.raises(ValueError, match='Source ou paramètres'):
        rejouer(s, base, camps[-1]['params'])


def test_export_recontrole_seuils_absents_en_null(contexte):
    from operations_qdd.evidence import json_bytes
    base, camps, _ = contexte
    s = scenario(contexte)
    rejouer(s, base, camps[-1]['params'])
    exported = json.loads(json_bytes(s))
    assert any(r['Seuil après'] is None for r in exported['preuve']['comparaison'])
    assert 'NaN' not in json_bytes(s).decode()


def test_validation_noncritique_seuil_manquant_bloquee(contexte):
    base, camps, _ = contexte
    c = camps[-1]
    df = candidats(base, c['date'], 'C02', 'DOMMAGES_OUVRAGE')
    s = declarer(c, base, 'C02', 'DOMMAGES_OUVRAGE', [{'objet': x, 'nouvelle': 0} for x in df.objet],
                 'Alice', 'Correction pédagogique', ROLES, METHODE)
    rejouer(s, base, c['params'])
    assert any('seuil QDD non calculé' in b for b in s['preuve']['blocages'])
    with pytest.raises(ValueError):
        valider(s, 'Bob', 'QDD', 'OK')


def test_dossier_zip_empreintes_et_pieces_manquantes(contexte):
    base, camps, xlsx = contexte
    c, p = camps[-1], camps[-2]
    data = dossier_zip(c, p, lignes(base, c['date']), volumetrie(c, p), execution(base, c['date'], referentiel()),
                       xlsx, base, [scenario(contexte)], METHODE)
    with ZipFile(BytesIO(data)) as z:
        assert z.testzip() is None
        m = json.loads(z.read('manifest.json'))
        for nom, expected in m['fichiers_sha256'].items():
            assert hashlib.sha256(z.read(nom)).hexdigest() == expected
        assert m['source_sha256'] == empreinte(base)
        assert m['methode'] == METHODE
        assert 'rapport_reference_3_campagnes.xlsx' in z.namelist()
        assert len([n for n in z.namelist() if n.startswith('sql/controles/')]) == 20
        assert 'aucune conformité' in m['perimetre']
        sc = json.loads(z.read('scenarios_et_evenements.json'))
        assert sc[0]['preuve'] is None
    missing = completude([]).set_index('Pièce')
    assert missing.loc['Validation métier de campagne', 'État'] == 'Manquant'
    assert missing.loc['Identité et droits des intervenants', 'État'] == 'Manquant'


def test_roadmap_claude_futur_et_sas_preserve():
    from assurance_feuille import tableau
    df = tableau().set_index('id')
    assert df.loc['E12', 'statut'] == 'Plus tard'
    assert 'Claude' in df.loc['E12', 'titre']
    assert 'Aucun service IA branché' in df.loc['E12', 'prerequis']
    assert '59 valeurs sur 59' in df.loc['F11', 'titre']
