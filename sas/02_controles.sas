/* =====================================================================
   02 — BIBLIOTHÈQUE DES CONTRÔLES (PROC SQL)
   Un contrôle = une macro %<ID>(arrete) qui crée WORK._C :
     - rapprochement : maille, v1, v2, v3   (v3 manquant si 2 sources)
     - cohérence     : maille, n_anomalies, n_elements, montant_anomalies, montant_total
   Les macros %mesure_rapprochement / %mesure_coherence transforment WORK._C
   en points de contrôle (1 point = 1 maille = 1 donnée) dans WORK._PTS.
   arrete : date SAS au format DATE9 (ex. 30SEP2026)
   ===================================================================== */

/* ---------------- Mesures génériques ---------------- */
%macro mesure_rapprochement(id);
  data work._pts;
    set work._c;
    length point_id $40 controle $8 detail $120;
    array v{3} v1-v3;
    mesure = 0;
    do k = 1 to 3;
      do j = 1 to 3;
        if k ne j and not missing(v{k}) and not missing(v{j}) then do;
          %if %upcase(&METHODE_ECART) = MEMOIRE %then %do;
            /* éq. 28 : écart relatif de la source j par rapport à la source k */
            if v{k} ne 0 then e = abs(v{j} / v{k} - 1);
            else e = (v{j} ne v{k});
          %end;
          %else %do;
            /* amélioration : écart symétrique borné */
            m = max(abs(v{k}), abs(v{j}));
            if m = 0 then e = 0; else e = min(1, abs(v{k} - v{j}) / m);
          %end;
          mesure = max(mesure, e);               /* éq. 30 : max des écarts deux à deux */
        end;
      end;
    end;
    resultat_brut = min(1, max(0, 1 - mesure)); /* éq. 27 bornée */
    controle = "&id";
    point_id = cats("&id", "|", maille);
    detail   = catx(' | ', put(v1, commax18.2), put(v2, commax18.2), ifc(missing(v3), '', put(v3, commax18.2)));
    keep point_id controle maille mesure resultat_brut detail;
  run;
%mend;

%macro mesure_coherence(id);
  data work._pts;
    set work._c;
    length point_id $40 controle $8 detail $120;
    if &POND_MONTANT = 1 and montant_total > 0 then
      mesure = montant_anomalies / montant_total;     /* amélioration : pondéré en montant */
    else if n_elements > 0 then
      mesure = n_anomalies / n_elements;               /* éq. 33 */
    else mesure = 0;
    resultat_brut = min(1, max(0, 1 - mesure));
    controle = "&id";
    point_id = cats("&id", "|", maille);
    detail   = catx(' ', put(n_anomalies, 8.), 'anomalies /', put(n_elements, 8.));
    keep point_id controle maille mesure resultat_brut detail;
  run;
%mend;

/* ---------------- Contrôles : primes ---------------- */
%macro R01(arrete);  /* Primes acquises : gestion vs comptabilité, par segment */
  proc sql;
    create table work._c as
    select g.segment as maille length=32, g.v1, c.prime_acquise as v2, . as v3
    from (select segment, sum(prime_acquise) as v1
          from (select distinct contrat_id, segment, prime_acquise
                from SI.gestion_contrats where arrete = "&arrete"d)
          group by segment) as g
         inner join SI.compta_primes as c
         on c.segment = g.segment and c.arrete = "&arrete"d;
  quit;
%mend;

%macro R02(arrete);  /* Primes acquises : gestion vs entrepôt */
  proc sql;
    create table work._c as
    select g.segment as maille length=32, g.v1, d.v2, . as v3
    from (select segment, sum(prime_acquise) as v1
          from (select distinct contrat_id, segment, prime_acquise
                from SI.gestion_contrats where arrete = "&arrete"d)
          group by segment) as g
         inner join
         (select segment, sum(prime_acquise) as v2
          from SI.dwh_contrats where arrete = "&arrete"d group by segment) as d
         on d.segment = g.segment;
  quit;
%mend;

%macro C01(arrete);  /* Contrats de gestion absents de l'entrepôt */
  proc sql;
    create table work._c as
    select g.segment as maille length=32,
           sum(missing(d.contrat_id))                              as n_anomalies,
           count(*)                                                as n_elements,
           sum(case when d.contrat_id is null then abs(g.prime_acquise) else 0 end) as montant_anomalies,
           sum(abs(g.prime_acquise))                               as montant_total
    from (select distinct contrat_id, segment, prime_acquise
          from SI.gestion_contrats where arrete = "&arrete"d) as g
         left join (select contrat_id from SI.dwh_contrats where arrete = "&arrete"d) as d
         on d.contrat_id = g.contrat_id
    group by g.segment;
  quit;
%mend;

%macro C02(arrete);  /* Prime acquise négative ou supérieure à la prime émise */
  proc sql;
    create table work._c as
    select segment as maille length=32,
           sum(prime_acquise < 0 or prime_acquise > prime_emise) as n_anomalies,
           count(*) as n_elements,
           sum(case when prime_acquise < 0 or prime_acquise > prime_emise then abs(prime_acquise) else 0 end) as montant_anomalies,
           sum(abs(prime_acquise)) as montant_total
    from SI.gestion_contrats where arrete = "&arrete"d
    group by segment;
  quit;
%mend;

%macro C03(arrete);  /* Doublons de contrats */
  proc sql;
    create table work._c as
    select segment as maille length=32,
           count(*) - count(distinct contrat_id) as n_anomalies,
           count(*) as n_elements,
           . as montant_anomalies, . as montant_total
    from SI.gestion_contrats where arrete = "&arrete"d
    group by segment;
  quit;
%mend;

/* ---------------- Contrôles : sinistres / provisions ---------------- */
%macro R03(arrete);  /* Provisions dossier : gestion vs entrepôt vs inputs actuariat (3 sources) */
  proc sql;
    create table work._c as
    select g.segment as maille length=32, g.v1, d.v2, a.provision_dossier_total as v3
    from (select segment, sum(provision_dossier) as v1
          from SI.gestion_sinistres where arrete = "&arrete"d group by segment) as g
         inner join
         (select segment, sum(provision_dossier) as v2
          from SI.dwh_sinistres where arrete = "&arrete"d group by segment) as d
         on d.segment = g.segment
         inner join SI.actuariat_inputs as a
         on a.segment = g.segment and a.arrete = "&arrete"d;
  quit;
%mend;

%macro R04(arrete);  /* Règlements cumulés : gestion vs comptabilité */
  proc sql;
    create table work._c as
    select g.segment as maille length=32, g.v1, c.reglements as v2, . as v3
    from (select segment, sum(reglements_cumules) as v1
          from SI.gestion_sinistres where arrete = "&arrete"d group by segment) as g
         inner join SI.compta_reglements as c
         on c.segment = g.segment and c.arrete = "&arrete"d;
  quit;
%mend;

%macro C04(arrete);  /* Sinistres sans contrat (orphelins) */
  proc sql;
    create table work._c as
    select s.segment as maille length=32,
           sum(missing(c.contrat_id)) as n_anomalies,
           count(*) as n_elements,
           sum(case when c.contrat_id is null then abs(s.provision_dossier) else 0 end) as montant_anomalies,
           sum(abs(s.provision_dossier)) as montant_total
    from SI.gestion_sinistres as s
         left join (select distinct contrat_id from SI.gestion_contrats where arrete = "&arrete"d) as c
         on c.contrat_id = s.contrat_id
    where s.arrete = "&arrete"d
    group by s.segment;
  quit;
%mend;

%macro C05(arrete);  /* Provisions dossier négatives */
  proc sql;
    create table work._c as
    select segment as maille length=32,
           sum(provision_dossier < 0) as n_anomalies,
           count(*) as n_elements,
           sum(case when provision_dossier < 0 then abs(provision_dossier) else 0 end) as montant_anomalies,
           sum(abs(provision_dossier)) as montant_total
    from SI.gestion_sinistres where arrete = "&arrete"d
    group by segment;
  quit;
%mend;

%macro C06(arrete);  /* Survenance postérieure à la déclaration */
  proc sql;
    create table work._c as
    select 'TOUS' as maille length=32,
           sum(date_survenance > date_declaration) as n_anomalies,
           count(*) as n_elements,
           sum(case when date_survenance > date_declaration then abs(provision_dossier) else 0 end) as montant_anomalies,
           sum(abs(provision_dossier)) as montant_total
    from SI.gestion_sinistres where arrete = "&arrete"d;
  quit;
%mend;

%macro C07(arrete);  /* Sinistre survenu avant la date d'effet du contrat */
  proc sql;
    create table work._c as
    select 'TOUS' as maille length=32,
           sum(s.date_survenance < c.date_effet) as n_anomalies,
           count(*) as n_elements,
           sum(case when s.date_survenance < c.date_effet then abs(s.provision_dossier) else 0 end) as montant_anomalies,
           sum(abs(s.provision_dossier)) as montant_total
    from SI.gestion_sinistres as s
         inner join (select contrat_id, min(date_effet) as date_effet
                     from SI.gestion_contrats where arrete = "&arrete"d group by contrat_id) as c
         on c.contrat_id = s.contrat_id
    where s.arrete = "&arrete"d;
  quit;
%mend;

/* ---------------- Contrôles : réassurance et placements ---------------- */
%macro R05(arrete);  /* Taux de cession : traités vs paramètre du modèle SCR */
  proc sql;
    create table work._c as
    select t.segment as maille length=32, t.taux_cession as v1, m.taux_cession as v2, . as v3
    from SI.reassurance_traites as t
         inner join SI.modele_parametres as m
         on m.segment = t.segment and m.arrete = t.arrete
    where t.arrete = "&arrete"d;
  quit;
%mend;

%macro R06(arrete);  /* Valeur de marché : dépositaire vs comptabilité, par classe */
  proc sql;
    create table work._c as
    select d.classe as maille length=32, sum(d.valeur_marche) as v1, sum(c.valeur_marche) as v2, . as v3
    from SI.placements_depositaire as d
         inner join SI.placements_compta as c
         on c.actif_id = d.actif_id and c.arrete = d.arrete
    where d.arrete = "&arrete"d
    group by d.classe;
  quit;
%mend;

%macro C08(arrete);  /* ISIN absent ou mal formé */
  proc sql;
    create table work._c as
    select classe as maille length=32,
           sum(lengthn(strip(isin)) ne 12) as n_anomalies,
           count(*) as n_elements,
           sum(case when lengthn(strip(isin)) ne 12 then valeur_marche else 0 end) as montant_anomalies,
           sum(valeur_marche) as montant_total
    from SI.placements_depositaire where arrete = "&arrete"d
    group by classe;
  quit;
%mend;

%macro C09(arrete);  /* CIC incohérent avec la classe d'actif (3e caractère = catégorie) */
  proc sql;
    create table work._c as
    select classe as maille length=32,
           sum((classe = 'ACTIONS' and substr(cic, 3, 1) ne '3')
            or (classe = 'OBLIGATIONS' and substr(cic, 3, 1) not in ('1', '2'))) as n_anomalies,
           count(*) as n_elements,
           sum(case when (classe = 'ACTIONS' and substr(cic, 3, 1) ne '3')
                      or (classe = 'OBLIGATIONS' and substr(cic, 3, 1) not in ('1', '2'))
                    then valeur_marche else 0 end) as montant_anomalies,
           sum(valeur_marche) as montant_total
    from SI.placements_depositaire where arrete = "&arrete"d
    group by classe;
  quit;
%mend;

%macro C10(arrete);  /* Code activité BTP hors nomenclature */
  proc sql;
    create table work._c as
    select 'TOUS' as maille length=32,
           sum(missing(r.code_activite)) as n_anomalies,
           count(*) as n_elements,
           . as montant_anomalies, . as montant_total
    from SI.gestion_contrats as g
         left join SI.ref_activites_btp as r
         on r.code_activite = g.code_activite
    where g.arrete = "&arrete"d;
  quit;
%mend;

/* ---------------- Contrôles de restitution : états QRT vs sources ----------------
   Seuil fixe (référentiel : seuil_fixe = 0.999) et exclus de la note (inclus_note = 0) :
   un écart entre un état et sa source est une erreur de production, pas une incertitude. */
%macro Q01(arrete);  /* Bilan S.02.01 (placements) vs liste des actifs S.06.02, par classe */
  proc sql;
    create table work._c as
    select b.classe as maille length=32, b.montant as v1, l.v2, . as v3
    from (select substr(poste, 12) as classe length=32, montant
          from SI.qrt_s0201 where arrete = "&arrete"d and poste like 'PLACEMENTS_%') as b
         inner join
         (select classe, sum(valeur_marche) as v2
          from SI.qrt_s0602 where arrete = "&arrete"d group by classe) as l
         on l.classe = b.classe;
  quit;
%mend;

%macro Q02(arrete);  /* BE sinistres S.17.01 vs outil de provisionnement */
  proc sql;
    create table work._c as
    select q.segment as maille length=32, a.be_sinistres_brut as v1, q.be_sinistres_brut as v2, . as v3
    from SI.qrt_s1701 as q
         inner join SI.actuariat_be as a on a.segment = q.segment and a.arrete = q.arrete
    where q.arrete = "&arrete"d;
  quit;
%mend;

%macro Q03(arrete);  /* Triangle S.19.01 (dernière diagonale) vs règlements cumulés de gestion */
  proc sql;
    create table work._c as
    select g.segment as maille length=32, g.v1, t.v2, . as v3
    from (select segment, sum(reglements_cumules) as v1
          from SI.gestion_sinistres where arrete = "&arrete"d group by segment) as g
         inner join
         (select segment, sum(paiements_cumules) as v2
          from SI.qrt_s1901_diagonale where arrete = "&arrete"d group by segment) as t
         on t.segment = g.segment;
  quit;
%mend;

%macro Q04(arrete);  /* Primes S.05.01 vs comptabilité */
  proc sql;
    create table work._c as
    select c.segment as maille length=32, c.prime_acquise as v1, q.primes_acquises_brutes as v2, . as v3
    from SI.compta_primes as c
         inner join SI.qrt_s0501 as q on q.segment = c.segment and q.arrete = c.arrete
    where c.arrete = "&arrete"d;
  quit;
%mend;
