/* =====================================================================
   10 — EXERCICES SAS CORRIGÉS (données fictives du projet)
   Progression : bases -> PROC SQL -> contrôles QDD -> macros -> automatisation.
   Chaque bloc « ===== Exx » correspond à un exercice de l'onglet
   « SAS pratique » de l'application, qui affiche aussi le résultat attendu
   (recalculé en SQL sur les mêmes fichiers CSV).
   Conseil : faire l'exercice soi-même AVANT d'ouvrir le corrigé, puis
   lancer le corrigé bloc par bloc (sélectionner le bloc, F3) et lire le journal.
   Ce fichier n'est pas appelé par 99_executer.sas.
   ===================================================================== */

/* ===== E00 | Préparer la session ===== */
/* À lancer une fois par session SAS : déclare les bibliothèques et charge les tables fictives. */
/* &RACINE : défini par lancer_qdd.sas ; sinon, valeur par défaut ci-dessous */
%global RACINE;
%let RACINE = %sysfunc(coalescec(&RACINE, /home/&sysuserid./qdd-s2));
%include "&RACINE./sas/00_config.sas";
%include "&RACINE./sas/01_import_demo.sas";
%let ARRETE = 30SEP2026;    /* date d'arrêté utilisée par tous les exercices */

/* ===== E01 | Combien de lignes par arrêté ? ===== */
proc freq data=SI.gestion_contrats;
  tables arrete / nocum;
run;

/* ===== E02 | Étape DATA : filtrer, calculer, formater ===== */
data work.contrats_rc;
  set SI.gestion_contrats;
  where segment = "RC_DECENNALE" and arrete = "&ARRETE"d;
  if prime_emise > 0 then taux_acquisition = prime_acquise / prime_emise;
  format date_effet ddmmyy10. taux_acquisition percent9.2;
  keep contrat_id code_activite date_effet prime_emise prime_acquise taux_acquisition;
run;

proc means data=work.contrats_rc n mean min max maxdec=4;
  var taux_acquisition;
run;

/* ===== E03 | Les dates sont des nombres ===== */
data work.delais;
  set SI.gestion_sinistres;
  where arrete = "&ARRETE"d;
  length categorie $40;
  delai_jours = date_declaration - date_survenance;
  if delai_jours < 0 then categorie = "1. Déclaration avant survenance";
  else if delai_jours <= 365 then categorie = "2. De 0 à 365 jours";
  else categorie = "3. Plus de 365 jours";
  format date_survenance date_declaration ddmmyy10.;
run;

proc freq data=work.delais;
  tables categorie / nocum;
run;

/* ===== E04 | PROC SQL : totaliser par segment ===== */
proc sql;
  create table work.primes_gestion as
  select segment, sum(prime_acquise) as prime_acquise format=commax18.2
  from SI.gestion_contrats
  where arrete = "&ARRETE"d
  group by segment
  order by segment;
quit;

/* ===== E05 | Rapprochement gestion / comptabilité (contrôle R01) ===== */
proc sql;
  create table work.rappro_primes as
  select g.segment,
         g.prime_acquise as gestion format=commax18.2,
         c.prime_acquise as comptabilite format=commax18.2,
         g.prime_acquise - c.prime_acquise as ecart format=commax18.2,
         calculated ecart / c.prime_acquise as ecart_relatif format=percent9.2
  from work.primes_gestion as g
       inner join SI.compta_primes as c
       on g.segment = c.segment and c.arrete = "&ARRETE"d
  order by g.segment;
quit;

/* ===== E06 | Doublons de contrats (contrôle C03) ===== */
proc sql;
  create table work.doublons_contrats as
  select contrat_id, count(*) as nb_lignes
  from SI.gestion_contrats
  where arrete = "&ARRETE"d
  group by contrat_id
  having count(*) > 1
  order by contrat_id;
quit;

/* ===== E07 | Sinistres orphelins (contrôle C04) ===== */
proc sql;
  create table work.sinistres_orphelins as
  select s.sinistre_id, s.contrat_id, s.segment, s.provision_dossier
  from SI.gestion_sinistres as s
  where s.arrete = "&ARRETE"d
    and not exists (select 1 from SI.gestion_contrats as c
                    where c.arrete = s.arrete and c.contrat_id = s.contrat_id);

  select count(*) as nb_orphelins, sum(provision_dossier) as provisions format=commax18.2
  from work.sinistres_orphelins;
quit;

/* ===== E08 | Contrats absents de l'entrepôt (contrôle C01) ===== */
proc sql;
  create table work.absents_entrepot as
  select g.contrat_id, g.segment, g.prime_acquise
  from SI.gestion_contrats as g
       left join SI.dwh_contrats as d
       on d.arrete = g.arrete and d.contrat_id = g.contrat_id
  where g.arrete = "&ARRETE"d and d.contrat_id is missing;

  select count(*) as nb_absents, sum(prime_acquise) as primes format=commax18.2
  from work.absents_entrepot;
quit;

/* ===== E09 | Code activité hors nomenclature (contrôle C10) ===== */
/* Un code vide n'est dans aucune liste : SAS le compte comme hors nomenclature. */
proc sql;
  create table work.activites_inconnues as
  select code_activite, count(*) as nb_contrats
  from SI.gestion_contrats
  where arrete = "&ARRETE"d
    and code_activite not in (select code_activite from SI.ref_activites_btp)
  group by code_activite
  order by nb_contrats desc, code_activite;
quit;

/* ===== E10 | Profiler avant de contrôler : les codes ISIN ===== */
/* LENGTHN renvoie 0 pour une valeur vide (LENGTH renverrait 1). */
data work.profil_isin;
  set SI.placements_depositaire;
  where arrete = "&ARRETE"d;
  longueur = lengthn(strip(isin));
run;

proc freq data=work.profil_isin;
  tables longueur / nocum;
run;

/* ===== E11 | Première macro : un contrôle, plusieurs tables ===== */
%macro ctrl_doublons(table=, cle=, arrete=);
  proc sql noprint;
    select count(*) into :nb_doublons trimmed
    from (select &cle from &table
          where arrete = "&arrete"d
          group by &cle
          having count(*) > 1);
  quit;
  %put NOTE: [QDD] &table : &nb_doublons valeur(s) de &cle en double au &arrete..;
%mend ctrl_doublons;

%ctrl_doublons(table=SI.gestion_contrats, cle=contrat_id, arrete=&ARRETE);
%ctrl_doublons(table=SI.gestion_sinistres, cle=sinistre_id, arrete=&ARRETE);
%ctrl_doublons(table=SI.placements_depositaire, cle=actif_id, arrete=&ARRETE);

/* ===== E12 | Boucle macro sur les segments ===== */
/* Piège : sans FORMAT=32.2, INTO stocke le montant au format BEST8. et perd des chiffres. */
%macro rappro_segments(segments=, arrete=);
  %local i seg g c;
  proc datasets lib=work nolist nowarn; delete rappro; quit;
  %do i = 1 %to %sysfunc(countw(&segments));
    %let seg = %scan(&segments, &i);
    proc sql noprint;
      select sum(prime_acquise) format=32.2 into :g trimmed
        from SI.gestion_contrats where arrete = "&arrete"d and segment = "&seg";
      select sum(prime_acquise) format=32.2 into :c trimmed
        from SI.compta_primes where arrete = "&arrete"d and segment = "&seg";
    quit;
    data work._un;
      length segment $20;
      segment = "&seg";
      gestion = &g;
      comptabilite = &c;
    run;
    proc append base=work.rappro data=work._un; run;
  %end;
  data work.rappro;
    set work.rappro;
    ecart_relatif = gestion / comptabilite - 1;
    format gestion comptabilite commax18.2 ecart_relatif percent9.2;
  run;
%mend rappro_segments;

%rappro_segments(segments=RC_DECENNALE DOMMAGES_OUVRAGE AUTO_FLOTTE, arrete=&ARRETE);

/* ===== E13 | Automatiser : journal d'exécution et export ===== */
%macro lancer_controles(arrete=);
  %local n_doublons n_orphelins n_absents;
  proc sql noprint;
    select count(*) into :n_doublons trimmed
      from (select contrat_id from SI.gestion_contrats where arrete = "&arrete"d
            group by contrat_id having count(*) > 1);
    select count(*) into :n_orphelins trimmed
      from SI.gestion_sinistres as s
      where s.arrete = "&arrete"d
        and not exists (select 1 from SI.gestion_contrats as c
                        where c.arrete = s.arrete and c.contrat_id = s.contrat_id);
    select count(*) into :n_absents trimmed
      from SI.gestion_contrats as g
      where g.arrete = "&arrete"d
        and not exists (select 1 from SI.dwh_contrats as d
                        where d.arrete = g.arrete and d.contrat_id = g.contrat_id);
  quit;
  data work._journal;
    length controle $30;
    execution = datetime();
    arrete = "&arrete"d;
    controle = "C03 doublons contrats";   nb_anomalies = &n_doublons;  output;
    controle = "C04 sinistres orphelins"; nb_anomalies = &n_orphelins; output;
    controle = "C01 absents entrepot";    nb_anomalies = &n_absents;   output;
    format execution datetime20. arrete date9.;
  run;
  proc append base=work.journal_exercices data=work._journal; run;
%mend lancer_controles;

proc datasets lib=work nolist nowarn; delete journal_exercices; quit;   /* NOWARN : pas d'avertissement au premier lancement */
%lancer_controles(arrete=31MAR2026);
%lancer_controles(arrete=30JUN2026);
%lancer_controles(arrete=&ARRETE);

proc export data=work.journal_exercices outfile="&SORTIE./journal_exercices.csv" dbms=dlm replace;
  delimiter=";";
run;
