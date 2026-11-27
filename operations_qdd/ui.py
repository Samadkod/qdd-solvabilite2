"""Écrans additionnels intégrés à l'application Streamlit existante."""
from __future__ import annotations

from dataclasses import asdict
from html import escape
import pandas as pd
import streamlit as st
from .diagnostic import diagnostic, impact
from .correction import (ESSAIS_VALIDABLES, REGLES, candidats, declarer, fiches_ajustement, lire_corrections,
                         modele_corrections, rejouer, valider)
from .evidence import completude, dossier_zip, json_bytes
from explications import MODALITES
from statuts import tableau
from langue import t as tr



def _pct(v) -> str:
    """Pourcentage au format français : 97,49 %."""
    return "—" if v is None or pd.isna(v) else f"{v * 100:.2f} %".replace(".", ",")


def _euros(v) -> str:
    """Montant au format français : -4 948,63 €."""
    return "" if pd.isna(v) else f"{v:,.2f} €".replace(",", " ").replace(".", ",")

def scenarios_contexte(c, methode):
    return [s for s in st.session_state.get('qdd_scenarios', []) if s['campagne'] == c['campagne']
            and s['date'] == str(c['date']) and s['params'] == asdict(c['params']) and s['methode'] == methode]


def afficher_diagnostic(c, prev, lignes, aller):
    with st.expander(tr('Diagnostic explicable de la campagne'), expanded=False):
        st.caption('Constats déterministes issus du moteur, sans IA. Priorité de revue : criticité hors seuil, '
                   'puis non-réalisation, puis autres écarts ; ce classement n’est pas une nouvelle note de risque.')
        df = diagnostic(c, lignes, prev)
        if df.empty:
            st.success('Aucun écart ni contrôle non réalisé dans les résultats retenus.')
            return
        st.dataframe(df[['Point', 'Donnée', 'Priorité de revue', 'Constat', 'Écart récurrent']],
                     hide_index=True, width='stretch')
        pid = st.selectbox('Point à expliquer', df.Point.tolist(), key='diagnostic_point')
        row = df.set_index('Point').loc[pid]
        st.markdown(f'**Constat vérifié** — {row["Constat"]}')
        st.write('Règle :', row['Règle'])
        st.write('Preuve moteur :', row['Preuve moteur'])
        st.caption(f'Dernière réalisation : {row["Dernière réalisation"]} · Responsable : {row["Responsable référentiel"]}')
        st.info('Cause métier non déterminée. Une valeur incohérente ne prouve ni une erreur de saisie ni un défaut de flux. '
                'Documenter une hypothèse avec le propriétaire avant de la retenir.')
        code, maille = pid.split('|', 1)
        lig = lignes[(lignes.controle == code) & (lignes.maille == maille)]
        if not row['Réalisé campagne']:
            st.warning('Les lignes ci-dessous sont détectées par un rejeu à cet arrêté ; elles ne prouvent pas '
                       'que le contrôle a été réalisé dans le plan historique.')
        if not lig.empty:
            st.dataframe(lig, hide_index=True, width='stretch')
        else:
            st.caption('Pas de détail ligne disponible pour ce point : consulter la preuve agrégée et la requête SQL.')
        cols = st.columns(2)
        if cols[0].button('Analyser les usages aval', key='diagnostic_impact', width='stretch'):
            aller('lignage', impact_donnee=row['Donnée'])
        if cols[1].button('Ouvrir l’atelier de résolution', key='diagnostic_resolution', width='stretch'):
            aller('resolution')
        st.download_button('Exporter le diagnostic · CSV', df.to_csv(index=False, sep=';').encode('utf-8-sig'),
                           file_name=f'diagnostic_{c["campagne"]}.csv', mime='text/csv')


def afficher_impact(c):
    st.subheader('Analyse d’impact fondée sur le lignage')
    st.caption('Périmètre documenté, pas une simulation de propagation. L’ordre du référentiel classe les étapes, '
               'mais les flux peuvent être parallèles.')
    mode = st.radio('Point de départ', ['Donnée', 'Point de contrôle', 'Flux'], horizontal=True, key='impact_mode')
    ids = c['donnees'].donnee_id.tolist()
    if mode == 'Point de contrôle':
        pid = st.selectbox('Point de contrôle source', c['controles'].controle_id.tolist(), key='impact_pid')
        ids = c['controles'].loc[c['controles'].controle_id == pid, 'donnee_id'].unique().tolist()
    elif mode == 'Flux':
        fid = st.selectbox('Flux source', sorted(c['couverture'].flux_id.unique()), key='impact_flux')
        ids = c['couverture'].loc[c['couverture'].flux_id == fid, 'donnee_id'].unique().tolist()
        st.caption(f'{len(ids)} donnée(s) liée(s) à ce flux dans le référentiel.')
    initial = st.session_state.get('impact_donnee')
    did = st.selectbox('Donnée à analyser', ids, index=ids.index(initial) if initial in ids else 0, key=f'impact_did_{mode}')
    im = impact(c, did)
    d = im['donnee']
    st.markdown(f'**{d["libelle"]}** · propriétaire : {d["proprietaire"]}')
    st.write('Règle de gestion :', d['regle_gestion'])
    st.write('Usages documentés :', im['usages'])
    st.write('Restitutions / destinations déclarées :', im['restitutions'])
    st.dataframe(im['parcours'][['ordre', 'flux_id', 'systeme_source', 'systeme_cible', 'traitement',
                               'mode', 'couvert', 'controles']], hide_index=True, width='stretch',
                 column_config={'ordre': 'Ordre', 'flux_id': 'Flux', 'systeme_source': 'Source', 'systeme_cible': 'Cible',
                                'traitement': 'Traitement', 'mode': 'Mode', 'couvert': 'Contrôlé', 'controles': 'Contrôles'})
    st.markdown('**Contrôles associés à cette donnée**')
    tableau(im['controles'][['controle_id', 'etape', 'responsable', 'resultat', 'seuil', 'statut', 'realise_campagne']],
            formats={'resultat': _pct, 'seuil': _pct}, hide_index=True, width='stretch',
            column_config={'controle_id': 'Point de contrôle', 'etape': 'Étape', 'responsable': 'Responsable',
                           'resultat': 'Résultat', 'seuil': 'Seuil', 'realise_campagne': 'Réalisé ce trimestre'})
    if im['parcours'].empty:
        st.warning('Aucun parcours documenté : absence de preuve de lignage, pas absence d’impact.')
    if not im['lacunes'].empty:
        st.warning(f'{len(im["lacunes"])} étape(s) de risque sans contrôle associé : couverture incomplète.')
        st.dataframe(im['lacunes'][['flux_id', 'traitement', 'systeme_cible']], hide_index=True, width='stretch')
    st.info(im['limite'])
    st.download_button('Exporter ce périmètre d’impact · CSV', im['parcours'].to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name=f'impact_{did}_{c["campagne"]}.csv', mime='text/csv')
    st.divider()


def afficher_resolution(c, base, methode):
    def etape(numero, titre):
        st.markdown(f'<div class="qdd-work-heading"><span>{numero:02d}</span>'
                    f'<h2>{escape(titre)}</h2></div>', unsafe_allow_html=True)

    st.caption('Bac à sable · données fictives · campagne historique inchangée')
    from fiche_atelier import afficher as afficher_fiche
    afficher_fiche(c, base)
    scenarios = scenarios_contexte(c, methode)
    choix = st.session_state.get('qdd_scenario_choix')
    courant = next((s for s in scenarios if s['id'] == choix), scenarios[-1] if scenarios else None)
    actif = (4 if courant and courant['statut'] == 'Validée dans le bac à sable' else
             3 if courant and courant['statut'] == 'Recontrôle réussi · à valider' else
             2 if courant else 1)
    st.markdown('<div class="qdd-process">' + ''.join(
        f'<div class="qdd-step{" active" if i == actif else ""}"><b>{i}</b><span>{titre}</span></div>'
        for i, titre in enumerate(['Proposer', 'Recontrôler', 'Valider', 'Exporter'], 1)) + '</div>',
        unsafe_allow_html=True)
    essais = ESSAIS_VALIDABLES.get(c['campagne'])
    if essais is not None:
        if essais:
            liste = ' ; '.join(f"**{r} · {MODALITES.get(m, m)}**" for r, m in essais)
            st.info(f"Scénarios qui vont jusqu'à la validation sur la campagne {c['campagne']} : {liste} "
                    "(tous les objets du segment). Les autres sont bloqués par un autre défaut de la même donnée, "
                    "ou par une donnée non critique.", icon=':material/lightbulb:')
        else:
            st.warning(f"Sur la campagne {c['campagne']}, aucun scénario ne peut être validé : ses défauts "
                       "volontaires (dates C06, règlements R04, état S.05.01 Q04) touchent les mêmes données et ne "
                       "sont réglés qu'à la campagne suivante. Pour l'essai complet, choisir la campagne **N** "
                       "en haut du menu.", icon=':material/info:')
    with st.expander('Périmètre et limites du bac à sable', expanded=False):
        st.warning('Session volatile : exporter les preuves avant de quitter. Aucune écriture dans la base '
                   'ou le registre de référence. Noms et rôles déclaratifs, sans droits réels.')
        st.caption('Seules C02 et C05 sont modifiables. Aucune propagation automatique vers les systèmes aval. '
                   'Pour les autres règles, consulter le diagnostic et le lignage.')
    with st.expander('Rôles et règle de validation configurables'):
        role_correction = st.text_input('Rôle de correction', 'Propriétaire de donnée', key='qdd_role_correction')
        role_validation = st.text_input('Rôle de validation', 'Référent QDD', key='qdd_role_validation')
        separation = st.checkbox('Exiger un validateur différent du correcteur (déclaratif)', value=True,
                                 key='qdd_separation')
        st.caption('Configuration figée lors de la déclaration. À remplacer par les habilitations de l’organisation en usage réel.')
    etape(1, 'Choisir les lignes à corriger')
    regles = list(REGLES)
    code = st.selectbox('Règle à corriger', regles, index=regles.index('C05'), format_func=lambda v: {
        'C02': 'C02 · Prime acquise hors bornes', 'C05': 'C05 · Provision négative'}[v], key='qdd_regle')
    points = c['controles'][c['controles'].controle == code]
    mailles = sorted(points.maille.unique())
    maille = st.selectbox('Segment de correction', mailles, key='qdd_maille',
                          index=mailles.index('AUTO_FLOTTE') if 'AUTO_FLOTTE' in mailles else 0,
                          format_func=lambda m: MODALITES.get(m, m))
    # Prévenir avant la déclaration : une donnée non critique n'a pas de seuil, le scénario ne pourra pas être validé.
    donnee = points.loc[points.maille == maille, 'donnee_id'].iloc[0]
    critique = bool(c['donnees'].set_index('donnee_id').loc[donnee, 'critique']) if 'donnee_id' in c['donnees'] else True
    if not critique:
        st.warning(f'« {donnee} » n’est pas une donnée critique : elle n’a pas de seuil QDD. Ce scénario pourra être '
                   'recontrôlé, mais **jamais validé**. Pour le premier essai, choisir **C05 · Provision négative** '
                   'et **Flottes auto**.', icon=':material/info:')
    df = candidats(base, c['date'], code, maille)
    aff = df.assign(**{col: df[col].map(_euros) for col in ('ancienne', 'plafond') if col in df})
    st.dataframe(aff, hide_index=True, width='stretch', column_config={
        'objet': st.column_config.TextColumn('Identifiant'),
        'ancienne': st.column_config.TextColumn('Valeur actuelle'),
        'plafond': st.column_config.TextColumn('Plafond (prime émise)'),
        'modifiable': st.column_config.CheckboxColumn('Modifiable sur copie'),
    })
    valides = df[df.modifiable]
    if not valides.empty:
        if len(valides) < len(df):
            st.info(f'{len(df) - len(valides)} ligne(s) en anomalie ne sont pas modifiables (identifiant dupliqué) : il '
                    'restera des lignes fautives sur la cible, et la validation sera bloquée.', icon=':material/info:')
        etape(2, 'Proposer une correction justifiée')
        st.caption('Une valeur et une pièce justificative par ligne : chaque identifiant reçoit sa propre valeur, tirée '
                   'de sa pièce. Toutes les lignes du segment sont corrigées dans une seule déclaration : c\'est ce qui '
                   'permet la validation. Décocher une ligne la laisse en anomalie, et la validation sera alors bloquée.')
        grille = valides[[k for k in ('objet', 'ancienne', 'plafond') if k in valides]].copy()
        grille.insert(0, 'corriger', True)
        grille['nouvelle'] = 0.0
        grille['piece'] = ''
        cle_grille = f'qdd_grille_{code}_{maille}'
        with st.expander('Beaucoup de lignes ? Importer un fichier de corrections (CSV)', icon=':material/upload_file:'):
            st.caption('Téléchargez le modèle (une ligne par identifiant, valeur actuelle rappelée), remplissez '
                       '« nouvelle_valeur » et « piece », puis déposez-le : le tableau ci-dessous se remplit, vous '
                       'relisez avant de déclarer.')
            st.download_button('Télécharger le modèle', modele_corrections(valides),
                               file_name=f'corrections_{code}_{maille}.csv', mime='text/csv',
                               icon=':material/download:', key=f'qdd_modele_{code}_{maille}')
            fichier = st.file_uploader('Fichier de corrections', type=['csv'], key=f'qdd_import_{code}_{maille}')
            if fichier is not None:
                lu, erreurs = lire_corrections(fichier.getvalue(), valides)
                for e in erreurs:
                    st.error(e)
                if len(lu):
                    par_id = lu.set_index('objet')
                    grille['corriger'] = grille['objet'].isin(par_id.index)
                    grille['nouvelle'] = grille['objet'].map(par_id['nouvelle']).fillna(0.0)
                    grille['piece'] = grille['objet'].map(par_id['piece']).fillna('')
                    cle_grille += f'_{fichier.file_id}'
                    st.success(f'{len(lu)} ligne(s) reprise(s) du fichier ; les identifiants absents du fichier sont '
                               'décochés.')
        with st.form('qdd_declaration'):
            saisie = st.data_editor(grille, hide_index=True, width='stretch', key=cle_grille,
                                    disabled=[k for k in ('objet', 'ancienne', 'plafond') if k in grille],
                                    column_config={
                                        'corriger': st.column_config.CheckboxColumn('Corriger'),
                                        'objet': st.column_config.TextColumn('Identifiant'),
                                        'ancienne': st.column_config.NumberColumn('Valeur actuelle (€)', format='%.2f'),
                                        'plafond': st.column_config.NumberColumn('Plafond : prime émise (€)', format='%.2f'),
                                        'nouvelle': st.column_config.NumberColumn('Nouvelle valeur (€)', min_value=0.0,
                                                                                  step=1.0, format='%.2f'),
                                        'piece': st.column_config.TextColumn(
                                            'Pièce justificative', help='Référence du document qui prouve la valeur : '
                                            'nature, numéro ou date (ex. « Rapport d\'expert n° 2026-114 du '
                                            '12/10/2026 »). Fictive ici.')})
            auteur = st.text_input('Correcteur (nom déclaré)')
            st.caption('Zéro est une proposition pédagogique, pas une valeur métier prouvée. En entreprise, chaque '
                       'valeur doit être justifiée par une pièce source.')
            justification = st.text_area('Justification d\'ensemble (pourquoi ces corrections)')
            confirme = st.checkbox('Je confirme cette proposition sur la copie fictive uniquement')
            submitted = st.form_submit_button('Déclarer la correction', type='primary')
        if submitted:
            try:
                if not confirme:
                    raise ValueError('Confirmer le périmètre fictif avant de déclarer.')
                choix_lignes = saisie[saisie['corriger'].astype(bool)]
                sans_piece = [r.objet for r in choix_lignes.itertuples() if not str(r.piece or '').strip()]
                if sans_piece:
                    raise ValueError('Pièce justificative manquante pour : ' + ', '.join(sans_piece)
                                     + '. Chaque valeur corrigée doit citer sa pièce (notice ACPR, points 36-37).')
                config = {'role_correction': role_correction, 'role_validation': role_validation, 'separation': separation}
                edits = [{'objet': r.objet, 'nouvelle': float(r.nouvelle), 'piece': str(r.piece).strip()}
                         for r in choix_lignes.itertuples()]
                record = declarer(c, base, code, maille, edits, auteur, justification, config, methode)
                st.session_state.setdefault('qdd_scenarios', []).append(record)
                st.session_state['qdd_scenario_choix'] = record['id']
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    else:
        st.info('Aucune anomalie modifiable pour cette règle et ce segment.')
    scenarios = scenarios_contexte(c, methode)
    if not scenarios:
        return
    st.divider()
    etape(3, 'Recontrôler et comparer')
    st.caption('Un changement de campagne ou de paramètres masque les scénarios des autres contextes sans les supprimer.')
    par_id = {s['id']: s for s in scenarios}
    if st.session_state.get('qdd_scenario_choix') not in par_id:
        st.session_state['qdd_scenario_choix'] = scenarios[-1]['id']
    sid = st.selectbox('Scénario à suivre', list(par_id), key='qdd_scenario_choix',
                       format_func=lambda id: f'{par_id[id]["code"]} · {MODALITES.get(par_id[id]["maille"], par_id[id]["maille"])} · '
                                           f'scénario {id[:8]}')  # l'état est affiché juste en dessous, à jour
    record = par_id[sid]
    st.markdown(f'**État : {record["statut"]}**')
    st.write('Justification :', record['justification'])
    st.caption(f'Correcteur : {record["auteur"]} · Rôle déclaré : {record["configuration"]["role_correction"]}')
    ed = pd.DataFrame(record['edits'])
    st.dataframe(ed.assign(ancienne=ed['ancienne'].map(_euros), nouvelle=ed['nouvelle'].map(_euros)),
                 hide_index=True, width='stretch',
                 column_config={'objet': 'Identifiant', 'ancienne': 'Valeur avant', 'nouvelle': 'Valeur proposée',
                                'piece': 'Pièce justificative'})
    if record['statut'] != 'Validée dans le bac à sable':
        if st.button('Relancer les 20 contrôles sur la copie', key='qdd_rejouer', type='primary'):
            try:
                with st.spinner('Copie isolée et exécution réelle des contrôles SQL…'):
                    rejouer(record, base, c['params'])
                st.rerun()
            except Exception as e:
                # Une erreur de recontrôle invalide toute ancienne preuve utilisable pour validation.
                record['preuve'] = None
                record['statut'] = 'Recontrôle en échec · à reprendre'
                from .correction import maintenant
                record['evenements'].append({'date': maintenant(), 'action': 'Échec de recontrôle',
                                             'erreur': f'{type(e).__name__}: {e}'})
                st.error(f'Recontrôle refusé / en échec : {type(e).__name__}: {e}')
    p = record.get('preuve')
    if p:
        st.info(p['limite'])
        cols = st.columns(2)
        cols[0].metric('Note avant · recontrôle neuf', _pct(p["note_avant_recontrole"]))
        cols[1].metric('Note après · scénario', _pct(p["note_apres"]))
        comp = pd.DataFrame(p['comparaison'])
        fmt = {'Avant': _pct, 'Après': _pct, 'Seuil après': _pct}
        tableau(comp[comp['Lié à la donnée corrigée']], formats=fmt, hide_index=True, width='stretch')
        with st.expander('Tous les points et preuves d’exécution'):
            tableau(comp, formats=fmt, hide_index=True, width='stretch')
            st.dataframe(pd.DataFrame(p['executions']), hide_index=True, width='stretch')
        if p['blocages']:
            st.error('Pourquoi la validation est bloquée :\n\n' + '\n\n'.join(f'- {b}' for b in p['blocages'])
                     + '\n\nLa validation exige que la donnée corrigée soit conforme sur **tous** ses contrôles, '
                       'pas seulement sur la règle corrigée.')
        else:
            st.success('Cible sans ligne fautive, contrôles liés au-dessus des seuils, aucune nouvelle non-conformité '
                       'ni dégradation d’un point déjà sous seuil. Les variations de points encore conformes restent visibles.')
    etape(4, 'Valider le scénario, puis exporter')
    if record['statut'] == 'Validée dans le bac à sable':
        v = next((e for e in reversed(record['evenements']) if e.get('action') == 'Validation déclarative'), {})
        st.success(f"Scénario validé par {v.get('acteur', '?')} ({v.get('role', '')}). Étape suivante : exporter la "
                   "preuve ci-dessous.", icon=':material/verified:')
    elif record['statut'] == 'Recontrôle bloquant':
        st.warning('Validation impossible pour ce scénario : le recontrôle a trouvé des blocages (voir ci-dessus). '
                   'Un scénario bloqué ne se valide jamais : faire une nouvelle déclaration à l’étape 1, '
                   'par exemple C05 · Flottes auto · tous les objets.', icon=':material/block:')
    elif record['statut'] != 'Recontrôle réussi · à valider' and record['statut'] != 'Validée dans le bac à sable':
        st.caption('Prochaine action : obtenir un recontrôle réussi sans blocage pour activer la validation.')
    with st.form('qdd_validation'):
        acteur = st.text_input('Validateur (nom déclaré)')
        st.caption('Rôle attendu : ' + record['configuration']['role_validation'])
        commentaire = st.text_area('Commentaire de validation')
        submit = st.form_submit_button('Valider dans le bac à sable',
                                      disabled=record['statut'] != 'Recontrôle réussi · à valider')
    if submit:
        try:
            valider(record, acteur, record['configuration']['role_validation'], commentaire)
            st.rerun()
        except ValueError as e:
            st.error(str(e))
    st.caption('Validation limitée au scénario : elle ne clôture aucune anomalie historique et n’approuve pas la campagne.')
    with st.expander('Journal du scénario', expanded=False):
        ev = pd.DataFrame(record['evenements'])
        ev['date'] = pd.to_datetime(ev['date']).dt.strftime('%d/%m/%Y %H:%M')
        for col in ev.columns:
            ev[col] = ev[col].map(lambda v: ' ; '.join(v) if isinstance(v, list) else ('' if v is None or
                                                                                        (isinstance(v, float) and pd.isna(v)) else v))
        st.dataframe(ev, hide_index=True, width='stretch',
                     column_config={'date': 'Date (UTC)', 'action': 'Action', 'acteur': 'Acteur', 'blocages': 'Blocages',
                                    'role': 'Rôle', 'commentaire': 'Commentaire', 'erreur': 'Erreur'})
    fiche = fiches_ajustement([record])
    with st.expander('Fiche d’ajustement', expanded=record['statut'] == 'Validée dans le bac à sable'):
        st.caption('Limite constatée, données en défaut conservées (archive figée et son empreinte), méthode et '
                   'responsables : tout est repris du scénario, rien n’est ressaisi.')
        st.dataframe(fiche.T.rename(columns={0: 'Valeur'}), width='stretch')
    st.download_button('Exporter la fiche d’ajustement · CSV', fiche.to_csv(index=False, sep=';').encode('utf-8-sig'),
                       file_name=f'fiche_ajustement_{sid[:8]}.csv', mime='text/csv')
    st.download_button('Exporter le scénario et ses preuves · JSON', json_bytes(record),
                       file_name=f'scenario_qdd_{sid[:8]}.json', mime='application/json')


def afficher_dossier(c, prev, lignes, volumes, executions, xlsx, base, methode, ouvert=False):
    with st.expander('Dossier de preuves de la campagne', expanded=ouvert):
        scenarios = scenarios_contexte(c, methode)
        st.caption('Résultats historiques + référentiels + règles SQL + scénarios séparés + manifeste SHA-256. '
                   'Conserver le ZIP : aucun archivage durable n’est fourni par la session publique.')
        tableau(completude(scenarios), hide_index=True, width='stretch')
        if c.get('document_cadre'):
            st.download_button('Document cadre généré · Markdown', c['document_cadre'].encode('utf-8'),
                               file_name=f"document_cadre_{c['campagne']}.md", mime='text/markdown',
                               icon=':material/description:', key='document_cadre_md')
            st.caption('Généré depuis les référentiels et les paramètres du moteur ; les rôles, la comitologie et la '
                       'validation par la direction générale restent à compléter par l’organisme.')
        st.warning('Dossier pédagogique, pas une attestation de conformité. Les pièces manquantes restent visibles ; '
                   'les noms et les validations sont déclaratifs.')
        key = f'qdd_zip_{c["campagne"]}'
        if st.button('Préparer le dossier ZIP', key='qdd_preparer_dossier'):
            st.session_state[key] = dossier_zip(c, prev, lignes, volumes, executions, xlsx, base, scenarios, methode)
            st.session_state[key + '_contexte'] = json_bytes({'params': asdict(c['params']), 'methode': methode,
                                                            'scenarios': scenarios})
        signature = json_bytes({'params': asdict(c['params']), 'methode': methode, 'scenarios': scenarios})
        if key in st.session_state and st.session_state.get(key + '_contexte') == signature:
            st.download_button('Télécharger le dossier de preuves · ZIP', st.session_state[key],
                               file_name=f'dossier_qdd_{c["campagne"]}.zip', mime='application/zip', type='primary')
        elif key in st.session_state:
            st.info('Paramètres ou scénarios modifiés : préparer un nouveau dossier avant de télécharger.')
