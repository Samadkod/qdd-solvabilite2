"""Exercices SAS corrigés : énoncés, indices et résultats attendus.

Le corrigé de chaque exercice est lu dans sas/10_exercices_corriges.sas (bloc « ===== Exx | … ===== »),
qui est la source unique du code SAS. Le résultat attendu est recalculé en SQL (DuckDB) sur les CSV de
sas/donnees_demo, c'est-à-dire sur exactement les données que SAS charge avec 01_import_demo.sas.
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd

RACINE = Path(__file__).resolve().parent
FICHIER_SAS = RACINE / "sas" / "10_exercices_corriges.sas"
DEMO = RACINE / "sas" / "donnees_demo"
ARRETE = "2026-09-30"

NIVEAUX = {1: "Bases", 2: "PROC SQL", 3: "Contrôles QDD", 4: "Macros et automatisation"}

EXERCICES = [
    dict(id="E01", niveau=1, duree=10, titre="Combien de lignes par arrêté ?",
         apprend="PROC FREQ, lire un résultat et le journal.",
         enonce="Comptez le nombre de lignes de la table `SI.gestion_contrats` pour chaque date d'arrêté.",
         indice="`PROC FREQ` avec une instruction `TABLES` sur la variable `arrete`. L'option `/ nocum` retire "
                "les colonnes cumulées.",
         attendu="select strftime(arrete, '%d/%m/%Y') as arrete, count(*) as nb_lignes "
                 "from gestion_contrats group by arrete order by min(arrete)"),
    dict(id="E02", niveau=1, duree=20, titre="Étape DATA : filtrer, calculer, formater",
         apprend="SET, WHERE, IF, KEEP, FORMAT, PROC MEANS.",
         enonce="Créez `work.contrats_rc` avec les contrats **RC décennale** au **30/09/2026**, et une colonne "
                "`taux_acquisition` = prime acquise ÷ prime émise (seulement si la prime émise est positive). "
                "Gardez 6 colonnes utiles, affichez les dates en jj/mm/aaaa, puis calculez le nombre, la moyenne, "
                "le minimum et le maximum du taux.",
         indice="Une date littérale s'écrit `\"30SEP2026\"d` (guillemets doubles pour qu'une macro-variable soit "
                "résolue). Ne divisez pas par zéro : `if prime_emise > 0 then …`.",
         attendu=f"select count(*) as nb_contrats, "
                 f"avg(case when prime_emise > 0 then prime_acquise / prime_emise end) as taux_moyen, "
                 f"min(case when prime_emise > 0 then prime_acquise / prime_emise end) as taux_min, "
                 f"max(case when prime_emise > 0 then prime_acquise / prime_emise end) as taux_max "
                 f"from gestion_contrats where segment = 'RC_DECENNALE' and arrete = DATE '{ARRETE}'",
         remarque="Un taux négatif signale une prime acquise négative : c'est ce que cherche le contrôle C02."),
    dict(id="E03", niveau=1, duree=20, titre="Les dates sont des nombres",
         apprend="Calcul sur les dates, LENGTH, IF / ELSE IF, catégories.",
         enonce="Pour les sinistres au 30/09/2026, calculez le délai en jours entre la survenance et la "
                "déclaration, puis classez chaque sinistre en trois catégories : déclaration avant survenance, "
                "de 0 à 365 jours, plus de 365 jours. Comptez chaque catégorie.",
         indice="En SAS, une date est un nombre de jours : `delai_jours = date_declaration - date_survenance;`. "
                "Déclarez la longueur de la variable texte (`length categorie $40;`) avant de la remplir, "
                "sinon elle prend la longueur de la première valeur.",
         attendu=f"select case when date_declaration - date_survenance < 0 then '1. Déclaration avant survenance' "
                 f"when date_declaration - date_survenance <= 365 then '2. De 0 à 365 jours' "
                 f"else '3. Plus de 365 jours' end as categorie, count(*) as nb_sinistres "
                 f"from gestion_sinistres where arrete = DATE '{ARRETE}' group by 1 order by 1",
         remarque="La première catégorie est exactement ce que détecte le contrôle C06 : c'est impossible, donc "
                  "c'est une erreur de saisie."),
    dict(id="E04", niveau=2, duree=15, titre="PROC SQL : totaliser par segment",
         apprend="CREATE TABLE … AS SELECT, SUM, GROUP BY, FORMAT= dans PROC SQL.",
         enonce="Créez `work.primes_gestion` : la somme des primes acquises par segment au 30/09/2026, dans "
                "l'outil de gestion.",
         indice="Le SQL est le même qu'ailleurs. Seules différences : `quit;` à la fin, et `format=commax18.2` "
                "pour afficher 1.234,56.",
         attendu=f"select segment, round(sum(prime_acquise), 2) as prime_acquise from gestion_contrats "
                 f"where arrete = DATE '{ARRETE}' group by segment order by segment"),
    dict(id="E05", niveau=3, duree=25, titre="Rapprochement gestion / comptabilité (contrôle R01)",
         apprend="Jointure, écart absolu et relatif, mot-clé CALCULATED.",
         enonce="Comparez, par segment, vos totaux de l'exercice E04 à la table `SI.compta_primes` au même "
                "arrêté : affichez le montant gestion, le montant comptable, l'écart et l'écart relatif.",
         indice="Joignez sur le segment **et** sur l'arrêté. Pour réutiliser une colonne calculée dans la même "
                "requête, préfixez-la par `calculated`.",
         attendu=f"select g.segment, round(g.p, 2) as gestion, round(c.prime_acquise, 2) as comptabilite, "
                 f"round(g.p - c.prime_acquise, 2) as ecart, (g.p - c.prime_acquise) / c.prime_acquise as ecart_relatif "
                 f"from (select segment, sum(prime_acquise) as p from gestion_contrats where arrete = DATE '{ARRETE}' "
                 f"group by segment) g join compta_primes c on c.segment = g.segment and c.arrete = DATE '{ARRETE}' "
                 f"order by g.segment",
         remarque="Un écart de quelques euros (arrondis) n'a pas la même gravité qu'un écart de 0,9 % : c'est "
                  "le seuil du contrôle qui tranche."),
    dict(id="E06", niveau=3, duree=15, titre="Doublons de contrats (contrôle C03)",
         apprend="GROUP BY … HAVING.",
         enonce="Listez les numéros de contrat présents plusieurs fois dans l'outil de gestion au 30/09/2026, "
                "avec leur nombre de lignes.",
         indice="`having count(*) > 1` filtre **après** le regroupement, là où `where` filtre avant.",
         attendu=f"select contrat_id, count(*) as nb_lignes from gestion_contrats where arrete = DATE '{ARRETE}' "
                 f"group by contrat_id having count(*) > 1 order by contrat_id"),
    dict(id="E07", niveau=3, duree=20, titre="Sinistres orphelins (contrôle C04)",
         apprend="Sous-requête NOT EXISTS (anti-jointure).",
         enonce="Trouvez les sinistres au 30/09/2026 dont le contrat n'existe pas dans l'outil de gestion au "
                "même arrêté. Donnez leur nombre et le total de leurs provisions.",
         indice="`where not exists (select 1 from … where c.contrat_id = s.contrat_id and c.arrete = s.arrete)`.",
         attendu=f"select count(*) as nb_orphelins, round(sum(provision_dossier), 2) as provisions "
                 f"from gestion_sinistres s where arrete = DATE '{ARRETE}' and not exists "
                 f"(select 1 from gestion_contrats c where c.arrete = s.arrete and c.contrat_id = s.contrat_id)",
         remarque="Un sinistre sans contrat est provisionné, mais on ne peut ni vérifier sa garantie ni le "
                  "rattacher à un segment de façon fiable."),
    dict(id="E08", niveau=3, duree=20, titre="Contrats absents de l'entrepôt (contrôle C01)",
         apprend="LEFT JOIN et IS MISSING : l'autre façon d'écrire une anti-jointure.",
         enonce="Trouvez les contrats de l'outil de gestion au 30/09/2026 absents de l'entrepôt de données "
                "(`SI.dwh_contrats`). Donnez leur nombre et leurs primes acquises.",
         indice="Après un `left join`, les colonnes de la table de droite sont vides quand il n'y a pas de "
                "correspondance : `where d.contrat_id is missing`.",
         attendu=f"select count(*) as nb_absents, round(sum(prime_acquise), 2) as primes from gestion_contrats g "
                 f"where arrete = DATE '{ARRETE}' and not exists (select 1 from dwh_contrats d "
                 f"where d.arrete = g.arrete and d.contrat_id = g.contrat_id)",
         remarque="Ces primes existent dans l'outil de gestion mais pas dans l'entrepôt, qui alimente les "
                  "calculs : elles manqueront au SCR."),
    dict(id="E09", niveau=3, duree=20, titre="Code activité hors nomenclature (contrôle C10)",
         apprend="NOT IN (sous-requête) et le piège des valeurs manquantes.",
         enonce="Comptez, par code, les contrats au 30/09/2026 dont le code activité ne figure pas dans "
                "`SI.ref_activites_btp`.",
         indice="Regardez bien la première ligne du résultat : un code **vide** n'appartient à aucune liste.",
         attendu=f"select coalesce(code_activite, '(vide)') as code_activite, count(*) as nb_contrats "
                 f"from gestion_contrats where arrete = DATE '{ARRETE}' and coalesce(code_activite, '') not in "
                 f"(select code_activite from ref_activites_btp) group by 1 order by nb_contrats desc, 1",
         remarque="En SAS, un code vide est compté hors nomenclature. Dans beaucoup de bases SQL, `NOT IN` "
                  "écarte au contraire les valeurs nulles sans prévenir : un contrôle peut alors passer à côté "
                  "des données manquantes."),
    dict(id="E10", niveau=3, duree=20, titre="Profiler avant de contrôler : les codes ISIN",
         apprend="LENGTHN, STRIP, profilage d'une colonne.",
         enonce="Avant d'écrire une règle « un ISIN fait 12 caractères », regardez la réalité : distribution des "
                "longueurs des codes ISIN des placements au 30/09/2026.",
         indice="`lengthn(strip(isin))` : `LENGTHN` renvoie 0 pour une valeur vide, alors que `LENGTH` renvoie 1.",
         attendu=f"select coalesce(length(trim(isin)), 0) as longueur, count(*) as nb_placements "
                 f"from placements_depositaire where arrete = DATE '{ARRETE}' group by 1 order by 1",
         remarque="Les codes à 12 caractères sont bien formés (2 lettres pays, 9 caractères, 1 clé de contrôle). "
                  "Les autres sont des valeurs manquantes ou fantaisistes (vide, « N/A », « FR12 ») : ce sont elles "
                  "que le contrôle C08 doit signaler. Leçon : profiler les données avant de fixer une règle. "
                  "Pour aller plus loin, la 12e position est une clé de contrôle (algorithme de Luhn) : "
                  "on peut aussi la vérifier."),
    dict(id="E11", niveau=4, duree=30, titre="Première macro : un contrôle, plusieurs tables",
         apprend="%MACRO / %MEND, paramètres, SELECT … INTO :, %PUT.",
         enonce="Écrivez une macro `%ctrl_doublons(table=, cle=, arrete=)` qui compte les valeurs en double de "
                "`cle` dans `table` à la date `arrete` et écrit le résultat dans le journal. Appelez-la sur les "
                "contrats, les sinistres et les placements.",
         indice="`select count(*) into :nb_doublons trimmed from (…)` range le résultat dans une macro-variable. "
                "Dans le texte, `&arrete..` : le premier point termine le nom de la macro-variable, le second "
                "s'affiche.",
         attendu=f"select 'SI.gestion_contrats' as table_controlee, (select count(*) from (select contrat_id "
                 f"from gestion_contrats where arrete = DATE '{ARRETE}' group by 1 having count(*) > 1)) as nb_doublons "
                 f"union all select 'SI.gestion_sinistres', (select count(*) from (select sinistre_id "
                 f"from gestion_sinistres where arrete = DATE '{ARRETE}' group by 1 having count(*) > 1)) "
                 f"union all select 'SI.placements_depositaire', (select count(*) from (select actif_id "
                 f"from placements_depositaire where arrete = DATE '{ARRETE}' group by 1 having count(*) > 1))"),
    dict(id="E12", niveau=4, duree=40, titre="Boucle macro sur les segments",
         apprend="%DO … %TO, %SCAN, %SYSFUNC(COUNTW), PROC APPEND, précision de INTO.",
         enonce="Écrivez `%rappro_segments(segments=, arrete=)` qui refait le rapprochement de E05 segment par "
                "segment, en empilant une ligne par segment dans `work.rappro`.",
         indice="Piège classique : `into :g` stocke le nombre avec le format par défaut `BEST8.` et peut perdre "
                "des chiffres sur des millions. Écrivez `select sum(prime_acquise) format=32.2 into :g trimmed`.",
         attendu=f"select g.segment, round(g.p, 2) as gestion, round(c.prime_acquise, 2) as comptabilite, "
                 f"g.p / c.prime_acquise - 1 as ecart_relatif from (select segment, sum(prime_acquise) as p "
                 f"from gestion_contrats where arrete = DATE '{ARRETE}' group by segment) g join compta_primes c "
                 f"on c.segment = g.segment and c.arrete = DATE '{ARRETE}' "
                 f"order by case g.segment when 'RC_DECENNALE' then 1 when 'DOMMAGES_OUVRAGE' then 2 else 3 end",
         remarque="Mêmes écarts relatifs qu'en E05 : c'est la preuve que la macro est juste."),
    dict(id="E13", niveau=4, duree=45, titre="Automatiser : journal d'exécution et export",
         apprend="Macro de campagne, DATETIME(), OUTPUT multiple, PROC APPEND, PROC EXPORT.",
         enonce="Écrivez `%lancer_controles(arrete=)` qui exécute les contrôles C03, C04 et C01 des exercices "
                "précédents et ajoute une ligne par contrôle dans `work.journal_exercices` (date et heure "
                "d'exécution, arrêté, contrôle, nombre d'anomalies). Lancez-la pour les trois arrêtés "
                "(31/03, 30/06 et 30/09/2026), puis exportez le journal en CSV dans `&SORTIE`.",
         indice="Dans une étape DATA, chaque `output;` écrit une ligne : trois `output;` = trois lignes. "
                "`proc datasets … nowarn; delete …;` vide le journal au début sans avertissement.",
         attendu="select strftime(a, '%d/%m/%Y') as arrete, controle, nb_anomalies from ("
                 "select arrete a, 1 o, 'C03 doublons contrats' controle, (select count(*) from (select contrat_id "
                 "from gestion_contrats g where g.arrete = x.arrete group by 1 having count(*) > 1)) nb_anomalies "
                 "from (select distinct arrete from gestion_contrats) x "
                 "union all select arrete, 2, 'C04 sinistres orphelins', (select count(*) from gestion_sinistres s "
                 "where s.arrete = x.arrete and not exists (select 1 from gestion_contrats c "
                 "where c.arrete = s.arrete and c.contrat_id = s.contrat_id)) from (select distinct arrete from gestion_contrats) x "
                 "union all select arrete, 3, 'C01 absents entrepot', (select count(*) from gestion_contrats g "
                 "where g.arrete = x.arrete and not exists (select 1 from dwh_contrats d "
                 "where d.arrete = g.arrete and d.contrat_id = g.contrat_id)) from (select distinct arrete from gestion_contrats) x"
                 ") order by a, o",
         remarque="C'est le principe de toute l'automatisation : le même programme, rejoué à chaque arrêté, "
                  "laisse une trace datée de ce qu'il a trouvé."),
]

TABLES = ["gestion_contrats", "dwh_contrats", "compta_primes", "gestion_sinistres", "ref_activites_btp",
          "placements_depositaire"]


def corriges() -> dict[str, tuple[str, str]]:
    """{id: (titre du bloc, code SAS)} lu dans le fichier SAS, y compris E00 (préparation)."""
    texte = FICHIER_SAS.read_text(encoding="utf-8")
    blocs = re.split(r"^/\* ===== (E\d\d) \| (.+?) ===== \*/\n", texte, flags=re.M)
    return {blocs[i]: (blocs[i + 1], blocs[i + 2].strip()) for i in range(1, len(blocs), 3)}


def _connexion() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for t in TABLES:
        con.execute(f"create view {t} as select * from read_csv('{(DEMO / f'{t}.csv').as_posix()}', "
                    f"delim=';', header=true)")
    return con


def resultats_attendus() -> dict[str, pd.DataFrame]:
    con = _connexion()
    try:
        return {e["id"]: con.execute(e["attendu"]).df() for e in EXERCICES}
    finally:
        con.close()


# ====================================================================== onglet Streamlit
def _formater(df: pd.DataFrame) -> pd.DataFrame:
    """Taux en %, montants en 1 234 567,89 (affichage français)."""
    out = df.copy()
    for col in out.columns:
        if not pd.api.types.is_float_dtype(out[col]):
            continue
        if "taux" in col or "relatif" in col:
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else f"{x * 100:.2f} %".replace(".", ","))
        else:
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else
                                    f"{x:,.2f}".replace(",", " ").replace(".", ","))
    return out


def afficher_exercices() -> None:
    import streamlit as st

    from style_app import etiquettes

    @st.cache_data(show_spinner=False)
    def _donnees():
        return corriges(), resultats_attendus()

    code, attendus = _donnees()
    fait = {e["id"] for e in EXERCICES if st.session_state.get(f"fait_{e['id']}")}

    st.markdown(
        "**13 exercices progressifs** sur les tables fictives du projet, des bases jusqu'à l'automatisation "
        "d'une campagne de contrôles. Chaque exercice reprend un vrai contrôle QDD.")
    c1, c2, c3 = st.columns(3)
    with c1, st.container(border=True):
        st.markdown("**1. Préparer**  \nCréez un compte **SAS OnDemand for Academics** (gratuit pour apprendre), "
                    "déposez-y le projet dans `qdd-s2/`, puis lancez le bloc **E00** du fichier des corrigés.")
    with c2, st.container(border=True):
        st.markdown("**2. Chercher seul**  \nLisez l'énoncé, écrivez votre programme, lancez-le, lisez le journal. "
                    "N'ouvrez l'indice qu'après 10 minutes bloqué.")
    with c3, st.container(border=True):
        st.markdown("**3. Vérifier**  \nComparez votre résultat au **résultat attendu**, puis lisez le corrigé : "
                    "il y a souvent plusieurs bonnes façons d'écrire.")
    with st.expander("E00 · Préparer la session SAS (à lancer une fois par session)"):
        st.code(code["E00"][1], language="sql")
        st.caption("Si votre dossier n'est pas /home/<identifiant>/qdd-s2, modifiez la première ligne (&RACINE).")

    total = sum(e["duree"] for e in EXERCICES)
    st.progress(len(fait) / len(EXERCICES),
                text=f"{len(fait)} exercice(s) terminé(s) sur {len(EXERCICES)} · durée totale estimée "
                     f"{total // 60} h {total % 60:02d}")
    niveaux = st.segmented_control("Niveau", list(NIVEAUX.values()), selection_mode="multi",
                                   default=list(NIVEAUX.values()))
    st.download_button("Télécharger tous les corrigés (10_exercices_corriges.sas)", icon=":material/download:", data=
                       FICHIER_SAS.read_bytes(), file_name=FICHIER_SAS.name, mime="text/plain")

    for e in EXERCICES:
        if NIVEAUX[e["niveau"]] not in (niveaux or []):
            continue
        with st.container(border=True):
            tete, coche = st.columns([5, 1])
            with tete:
                st.markdown(f"#### {e['id']} · {e['titre']}")
                etiquettes((f"Niveau {e['niveau']} · {NIVEAUX[e['niveau']]}", ""), (f"≈ {e['duree']} min", "gris"),
                           (e["apprend"], "or"))
            with coche:
                st.checkbox("Fait", key=f"fait_{e['id']}")
            st.markdown(e["enonce"])
            with st.expander("Indice", icon=":material/lightbulb:"):
                st.markdown(e["indice"])
            with st.expander("Corrigé SAS", icon=":material/code:"):
                st.code(code[e["id"]][1], language="sql")
            with st.expander("Résultat attendu", icon=":material/task_alt:"):
                st.dataframe(_formater(attendus[e["id"]]), hide_index=True, width="stretch")
                if e.get("remarque"):
                    st.info(e["remarque"], icon=":material/search_insights:")
    st.caption("Résultats attendus recalculés en SQL (DuckDB) sur les mêmes fichiers CSV que ceux chargés par SAS "
               "(sas/donnees_demo). Les corrigés SAS passent la vérification statique du projet mais n'ont pas "
               "encore été exécutés dans SAS : signalez tout écart.")
