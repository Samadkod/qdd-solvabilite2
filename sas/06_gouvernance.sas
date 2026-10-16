/* =====================================================================
   06 — GOUVERNANCE : lignage et couverture, registre des anomalies, journal
   Miroir de qdd_s2/gouvernance.py (mêmes règles, mêmes identifiants).
   %qdd_couverture(camp=N)
   %qdd_registre(camp=N, arrete=30SEP2026)
   %qdd_journal(camp=N, arrete=30SEP2026)
   ===================================================================== */

/* ---------- 1. Couverture du lignage par les contrôles ---------- */
/* Un passage (donnée, flux) est couvert s'il existe un point de contrôle sur la donnée
   dont le référentiel déclare ce flux. Seules les zones de risque des données critiques comptent. */
%macro qdd_couverture(camp=);
  data work._cf;
    set QDD.controles_&camp(keep=donnee_id controle flux);
    length flux_id $8;
    do k = 1 to countw(flux, ',');
      flux_id = strip(scan(flux, k, ','));
      output;
    end;
    keep donnee_id controle flux_id;
  run;
  proc sql;
    create table work._cfu as
    select distinct donnee_id, flux_id, controle from work._cf order by donnee_id, flux_id, controle;
  quit;
  data work._cfa;
    set work._cfu;
    by donnee_id flux_id;
    length controles $200;
    retain controles;
    if first.flux_id then controles = '';
    controles = catx(', ', controles, controle);
    if last.flux_id then output;
    keep donnee_id flux_id controles;
  run;
  proc sql;
    create table QDD.couverture_&camp as
    select l.donnee_id, d.libelle as libelle_donnee, coalesce(d.critique, 0) as critique, l.ordre, l.flux_id,
           f.systeme_source, f.systeme_cible, f.traitement, f.mode, f.zone_risque,
           (not missing(a.controles)) as couvert, a.controles, d.proprietaire
    from QDD.lignage_donnees as l
         left join QDD.lignage_flux   as f on f.flux_id = l.flux_id
         left join work._cfa          as a on a.donnee_id = l.donnee_id and a.flux_id = l.flux_id
         left join QDD.donnees_&camp  as d on d.donnee_id = l.donnee_id
    order by l.donnee_id, l.ordre;

    create table QDD.gouv_couverture_&camp as
    select "&camp" as campagne length=8,
           mean(couvert)       as taux_couverture_zones_risque format=percent10.1,
           count(*)            as nb_zones_risque_critiques,
           sum(couvert = 0)    as nb_zones_non_couvertes
    from QDD.couverture_&camp where zone_risque = 1 and critique = 1;
  quit;
%mend;

/* ---------- 2. Registre des anomalies (cycle de vie) ----------
   - point évalué rouge/orange -> anomalie (Haute/Moyenne) ; « Contrôle non réalisé » si antériorité > 0 ;
   - zone de risque critique non couverte -> anomalie « Couverture » (Moyenne) ;
   - toujours constatée -> « Récurrente » ;
   - clôture : Couverture dès qu'elle n'est plus constatée ; autres types seulement si le point
     a été RÉALISÉ dans la campagne (antériorité 0) et n'est plus en anomalie ;
   - échéance = date de détection + 30 j (Haute) / 60 j (Moyenne). */
%macro qdd_registre(camp=, arrete=);
  %local nreg;
  %if not %sysfunc(exist(QDD.registre_anomalies)) %then %do;
    data QDD.registre_anomalies;
      length anomalie_id $14 type $25 objet $80 donnee_id $60 libelle $120 gravite $8 proprietaire $60
             campagne_detection $8 date_detection echeance 8 derniere_campagne $8 nb_campagnes 8
             statut $12 date_cloture 8 constat $160 action_attendue $160;
      format date_detection echeance date_cloture date9.;
      stop;
    run;
  %end;

  data work._constats;
    length objet $80 type $25 donnee_id $60 libelle $120 gravite $8 proprietaire $60
           constat $160 action_attendue $160;
    set QDD.controles_&camp(where=(statut in ('rouge', 'orange')));
    objet = point_id;
    if anteriorite > 0 then type = 'Contrôle non réalisé';
    else if inclus_note = 0 then type = 'Restitution QRT';
    else type = 'Qualité de donnée';
    gravite = ifc(statut = 'rouge', 'Haute', 'Moyenne');
    proprietaire = responsable;
    constat = catx(' ', 'Résultat', strip(put(resultat, percent10.2)), '< seuil', strip(put(seuil, percent10.2)));
    if anteriorite > 0 then constat = catx(' ', constat, cat('(antériorité ', strip(put(anteriorite, best12.)), ')'));
    if type = 'Contrôle non réalisé' then action_attendue = 'Réaliser le contrôle et transmettre le résultat';
    else if type = 'Restitution QRT' then action_attendue = "Aligner l'état sur sa source avant la remise et tracer l'ajustement";
    else action_attendue = "Analyser l'écart, corriger la source, documenter l'ajustement (notice, point 37)";
    keep objet type donnee_id libelle gravite proprietaire constat action_attendue;
  run;
  data work._constats_couv;
    length objet $80 type $25 donnee_id $60 libelle $120 gravite $8 proprietaire $60
           constat $160 action_attendue $160;
    set QDD.couverture_&camp(where=(zone_risque = 1 and critique = 1 and couvert = 0)
                             rename=(proprietaire=_prop));
    objet = cats(donnee_id, '|', flux_id);
    type = 'Couverture';
    libelle = catx(' ', 'Flux', flux_id, 'non contrôlé :', systeme_source, '→', systeme_cible);
    gravite = 'Moyenne';
    proprietaire = _prop;
    constat = catx(' ', 'Zone de risque «', traitement, '» sans contrôle de niveau 1');
    action_attendue = "Concevoir un contrôle sur ce flux et l'ajouter au référentiel";
    keep objet type donnee_id libelle gravite proprietaire constat action_attendue;
  run;
  data work._constats; set work._constats work._constats_couv; run;
  proc sort data=work._constats; by type objet; run;   /* identifiants déterministes */

  proc sql;
    create table work._realises as
    select point_id from QDD.controles_&camp where anteriorite = 0;

    /* Clôtures */
    update QDD.registre_anomalies as r
      set statut = 'Clôturée', date_cloture = "&arrete"d, derniere_campagne = "&camp"
      where r.statut in ('Ouverte', 'Récurrente')
        and not exists (select 1 from work._constats as c where c.type = r.type and c.objet = r.objet)
        and (r.type = 'Couverture' or r.objet in (select point_id from work._realises));

    /* Récurrences */
    update QDD.registre_anomalies as r
      set statut = 'Récurrente',
          nb_campagnes = nb_campagnes + 1,
          derniere_campagne = "&camp",
          constat = (select c.constat from work._constats as c where c.type = r.type and c.objet = r.objet),
          gravite = case when exists (select 1 from work._constats as c
                                      where c.type = r.type and c.objet = r.objet and c.gravite = 'Haute')
                         then 'Haute' else r.gravite end
      where r.statut in ('Ouverte', 'Récurrente')
        and exists (select 1 from work._constats as c where c.type = r.type and c.objet = r.objet);

    /* Nouvelles anomalies */
    create table work._nouveaux as
    select c.* from work._constats as c
    where not exists (select 1 from QDD.registre_anomalies as r
                      where r.type = c.type and r.objet = c.objet and r.statut in ('Ouverte', 'Récurrente'))
    order by c.type, c.objet;
    select count(*) into :nreg trimmed from QDD.registre_anomalies;
  quit;

  data work._nouveaux;
    set work._nouveaux;
    length anomalie_id $14 campagne_detection $8 derniere_campagne $8 statut $12;
    anomalie_id = cats('ANO-', year("&arrete"d), '-', put(&nreg + _n_, z3.));
    campagne_detection = "&camp";
    date_detection = "&arrete"d;
    echeance = "&arrete"d + ifn(gravite = 'Haute', 30, 60);
    derniere_campagne = "&camp";
    nb_campagnes = 1;
    statut = 'Ouverte';
    date_cloture = .;
    format date_detection echeance date_cloture date9.;
  run;
  proc append base=QDD.registre_anomalies data=work._nouveaux force; run;

  proc sql;
    create table QDD.gouv_anomalies_&camp as
    select "&camp" as campagne length=8,
           sum(statut in ('Ouverte', 'Récurrente'))                          as nb_anomalies_ouvertes,
           sum(statut in ('Ouverte', 'Récurrente') and gravite = 'Haute')    as nb_anomalies_haute,
           sum(statut = 'Récurrente')                                        as nb_anomalies_recurrentes,
           sum(statut in ('Ouverte', 'Récurrente') and echeance < "&arrete"d) as nb_anomalies_en_retard,
           sum(statut = 'Clôturée')                                          as nb_anomalies_cloturees
    from QDD.registre_anomalies;
  quit;
%mend;

/* ---------- 3. Journal d'exécution (piste d'audit ACPR / CAC) ---------- */
%macro qdd_journal(camp=, arrete=);
  %local tables n i t vol;
  /* volumétries : tables sources ayant une colonne ARRETE */
  proc sql noprint;
    select memname into :t1- from dictionary.columns
    where libname = 'SI' and upcase(name) = 'ARRETE';
    %let n = &sqlobs;
  quit;
  %let vol = ;
  %do i = 1 %to &n;
    proc sql noprint;
      select count(*) into :_c trimmed from SI.&&t&i where arrete = "&arrete"d;
    quit;
    %let vol = &vol.%lowcase(&&t&i)=&_c.%str(;);
  %end;

  data work._j;
    length horodatage $19 utilisateur $32 campagne $8 version_sas $40 parametres $300 volumetries_sources $1000;
    horodatage  = put(datetime(), e8601dt19.);
    utilisateur = "&sysuserid";
    campagne    = "&camp";
    date_arrete = "&arrete"d;
    version_sas = "&sysvlong";
    parametres  = "SEUIL=&SEUIL;MODE_TOL=&MODE_TOL;DSCR=&DSCR;TOL_GLOBALE=&TOL_GLOBALE;COEF=&COEF;"
                  || "DEGRADATION=&DEGRADATION;MARGE=&MARGE;METHODE_ECART=&METHODE_ECART;POND_MONTANT=&POND_MONTANT";
    volumetries_sources = "&vol";
    nb_controles_executes = &_nb_exec;
    format date_arrete date9.;
  run;
  proc sql;
    create table work._j as
    select j.*, i.note format=percent10.2, i.note_min format=percent10.2
    from work._j as j, QDD.indicateurs_&camp as i;
  quit;
  proc append base=QDD.journal_executions data=work._j force; run;
%mend;
