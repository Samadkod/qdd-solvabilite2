/* =====================================================================
   03 — CAMPAGNE QDD : exécution, historisation, notes, indicateurs
   %qdd_campagne(camp=N, arrete=30SEP2026, non_realises=C07 R04 C08 R05)
   Sorties (bibliothèque QDD) :
     SENS_<camp>        sensibilités + diagnostic de linéarité
     CONTROLES_<camp>   points de contrôle (résultat brut, antériorité, résultat retenu, seuil, statut)
     DONNEES_<camp>     données (criticité, note, note min, statut, couverture E/X/P)
     INDICATEURS_<camp> indicateurs de la campagne (1 ligne)
   ===================================================================== */

/* ---------- 1. Sensibilités à partir des relances du moteur SCR (éq. 4) ---------- */
%macro qdd_sensibilites(arrete=, out=);
  proc sql;
    create table work._rel as
    select r.donnee_id, r.choc, r.valeur, r.scr, ref.scr as scr_ref,
           abs(r.scr - ref.scr) / ref.scr / abs(r.choc) as s
    from QDD.relances_scr as r
         inner join (select donnee_id, scr from QDD.relances_scr
                     where arrete = "&arrete"d and choc = 0) as ref
         on ref.donnee_id = r.donnee_id
    where r.arrete = "&arrete"d and r.choc ne 0;

    create table &out as
    select a.donnee_id, a.valeur, a.scr_ref, a.s as sensibilite,
           max(abs(b.s - a.s)) / a.s as non_linearite,
           (calculated non_linearite <= &SEUIL_NL) as lineaire
    from (select * from work._rel where abs(choc - &CHOC_REF) < 1e-9) as a
         inner join work._rel as b on b.donnee_id = a.donnee_id
    group by a.donnee_id, a.valeur, a.scr_ref, a.s;
  quit;
%mend;

/* ---------- 2. Exécution des contrôles réalisés et historisation ---------- */
%macro qdd_executer_controles(arrete=, non_realises=);
  %local n i id fam;
  %global _nb_exec;
  %let _nb_exec = 0;
  proc sql noprint;
    select controle_id, famille into :cid1-, :fam1- from QDD.referentiel_controles;
    %let n = &sqlobs;
    delete from QDD.hist_resultats where date_realisation = "&arrete"d;  /* relance idempotente */
  quit;
  %do i = 1 %to &n;
    %let id  = &&cid&i;
    %let fam = &&fam&i;
    %if %sysfunc(indexw(%str( &non_realises), &id)) = 0 %then %do;
      %&id(&arrete);
      %if &fam = rapprochement %then %mesure_rapprochement(&id);
      %else %mesure_coherence(&id);
      data work._pts; set work._pts; date_realisation = "&arrete"d; format date_realisation date9.; run;
      proc append base=QDD.hist_resultats data=work._pts force; run;
      %let _nb_exec = %eval(&_nb_exec + 1);
    %end;
    %else %put NOTE: [QDD] contrôle &id non réalisé au &arrete : son dernier résultat sera dégradé.;
  %end;
%mend;

/* ---------- 3. Campagne complète ---------- */
%macro qdd_campagne(camp=, arrete=, non_realises=);
  %local smoy_calc smoy coh;

  %qdd_executer_controles(arrete=&arrete, non_realises=&non_realises);
  %qdd_sensibilites(arrete=&arrete, out=QDD.sens_&camp);

  /* 3a. Dernier résultat connu de chaque point à la date de campagne */
  proc sort data=QDD.hist_resultats(where=(date_realisation <= "&arrete"d)) out=work._h;
    by point_id date_realisation;
  run;
  data work._dern; set work._h; by point_id; if last.point_id; run;

  /* 3b. Points enrichis du référentiel + antériorité (éq. 34) + dégradation (éq. 36/37) */
  proc sql;
    create table work._points as
    select d.point_id, d.controle, d.maille, d.resultat_brut, d.mesure, d.detail,
           d.date_realisation as date_derniere_real format=date9.,
           r.libelle, r.famille, r.criteres, r.frequence, r.poids, r.etape, r.responsable,
           r.flux, r.seuil_fixe, coalesce(r.inclus_note, 1) as inclus_note,
           tranwrd(r.donnee_id, '{maille}', strip(d.maille)) as donnee_id length=60
    from work._dern as d
         inner join QDD.referentiel_controles as r
         on r.controle_id = d.controle;
  quit;

  data work._points;
    set work._points;
    length intervalle $10;
    select (frequence);
      when ('M') intervalle = 'month';
      when ('T') intervalle = 'qtr';
      when ('S') intervalle = 'semiyear';
      otherwise  intervalle = 'year';
    end;
    /* nb de fins de période (calendaires) dans ]dernière réalisation ; arrêté] */
    anteriorite = intck(intervalle, date_derniere_real + 1, "&arrete"d + 1);
    realise_campagne = (date_derniere_real = "&arrete"d);
    if missing(resultat_brut) then do; resultat_brut = 0; resultat = 0; end;
    else do;
      %if %upcase(&DEGRADATION) = SIMPLE %then %do;
        resultat = resultat_brut * max(0, 1 - &COEF * anteriorite);
      %end;
      %else %do;
        resultat = resultat_brut * (1 - &COEF) ** anteriorite;
      %end;
    end;
    if missing(poids) then poids = 1;
    drop intervalle;
  run;

  /* 3c. Données : sensibilité, criticité (seuil ou dire d'expert) */
  proc sql;
    create table work._don as
    select r.*, coalesce(s.sensibilite, 0) as sensibilite, s.valeur, s.non_linearite
    from QDD.repertoire_donnees as r
         left join QDD.sens_&camp as s
         on s.donnee_id = r.donnee_id;
    select mean(sensibilite) into :smoy_calc trimmed from work._don where sensibilite >= &SEUIL;
  quit;

  data work._don;
    set work._don;
    if upcase(critique_expert) = 'TRUE' then critique = 1;
    else if upcase(critique_expert) = 'FALSE' then critique = 0;
    else critique = (sensibilite >= &SEUIL);
    /* critique à dire d'expert sans sensibilité calculable : convention = sensibilité moyenne */
    if critique = 1 and sensibilite = 0 then sensibilite = &smoy_calc;
  run;

  proc sql noprint;
    select mean(sensibilite) into :smoy trimmed from work._don where critique = 1;
  quit;

  /* Cohérence tolérance / criticité (éq. 12 et 19) */
  %if %upcase(&MODE_TOL) = DONNEE %then %let coh = %sysevalf(&DSCR < &SEUIL);
  %else %let coh = %sysevalf(&TOL_GLOBALE < &SEUIL / &smoy);
  %if &coh = 0 %then %do;
    %put ERROR: [QDD] Paramètres incohérents : tolérance >= seuil de significativité (éq. 12 / 19). Campagne arrêtée.;
    %return;
  %end;

  /* 3d. Notes par donnée (éq. 22) */
  proc sql;
    create table work._notes as
    select donnee_id,
           sum(poids * resultat)      / sum(poids) as note,
           sum(poids * resultat_brut) / sum(poids) as note_avant_degradation,
           count(*) as nb_controles
    from work._points where inclus_note = 1 group by donnee_id;
  quit;

  /* Couverture des critères E / X / P par donnée */
  data work._crit;
    set work._points(keep=donnee_id criteres inclus_note where=(inclus_note = 1));
    length critere $1;
    do k = 1 to countw(criteres, ',');
      critere = strip(scan(criteres, k, ','));
      output;
    end;
    keep donnee_id critere;
  run;
  proc sql;
    create table work._couv as
    select donnee_id,
           cats(ifc(sum(critere='E')>0,'E',''), ifc(sum(critere='P')>0,'P',''), ifc(sum(critere='X')>0,'X','')) as criteres_couverts length=3
    from work._crit group by donnee_id;
  quit;

  /* 3e. Tolérance (éq. 10 ou 21), statut tricolore */
  proc sql;
    create table QDD.donnees_&camp as
    select d.donnee_id, d.libelle, d.proprietaire, d.valeur, d.sensibilite, d.critique_expert, d.critique,
           d.non_linearite,
           case when d.critique = 1 then
             %if %upcase(&MODE_TOL) = DONNEE %then %do; &DSCR / d.sensibilite %end;
             %else %do; &TOL_GLOBALE * &smoy / d.sensibilite %end;
           end as tolerance,
           1 - calculated tolerance as note_min,
           n.note, n.note_avant_degradation, coalesce(n.nb_controles, 0) as nb_controles,
           c.criteres_couverts
    from work._don as d
         left join work._notes as n on n.donnee_id = d.donnee_id
         left join work._couv  as c on c.donnee_id = d.donnee_id
    order by d.critique desc, d.sensibilite desc;
  quit;

  data QDD.donnees_&camp;
    set QDD.donnees_&camp;
    length statut $6;
    if critique = 1 and not missing(note) then do;
      if note >= note_min then statut = 'vert';
      else if note >= note_min - &MARGE then statut = 'orange';
      else statut = 'rouge';
    end;
    format sensibilite tolerance note_min note note_avant_degradation non_linearite percent10.2;
  run;

  /* 3f. Seuil d'acceptation des contrôles = note min de la donnée (éq. 38) */
  proc sql;
    create table QDD.controles_&camp as
    select p.*, coalesce(d.critique, 0) as critique,
           /* seuil fixe pour les contrôles de restitution QRT, sinon note min de la donnée */
           case when not missing(p.seuil_fixe) then p.seuil_fixe else d.note_min end as seuil,
           (calculated critique = 1 or not missing(p.seuil_fixe)) as evalue,
           case when calculated evalue = 1 then (p.resultat >= calculated seuil) end as conforme
    from work._points as p
         left join QDD.donnees_&camp as d on d.donnee_id = p.donnee_id
    order by p.donnee_id, p.point_id;
  quit;
  data QDD.controles_&camp;
    set QDD.controles_&camp;
    length statut $6;
    if evalue = 1 then do;
      if resultat >= seuil then statut = 'vert';
      else if not missing(seuil_fixe) then statut = 'rouge';     /* restitution : binaire */
      else if resultat >= seuil - &MARGE then statut = 'orange';
      else statut = 'rouge';
    end;
    format resultat_brut resultat seuil seuil_fixe mesure percent10.2;
  run;

  /* 3g. Indicateurs (tableau 18 + améliorations) */
  proc sql;
    create table work._i1 as
    select sum(sensibilite * note) / sum(sensibilite)                   as note,
           sum(sensibilite * note_min) / sum(sensibilite)               as note_min,
           sum(sensibilite * note_avant_degradation) / sum(sensibilite) as note_avant_degradation,
           calculated note - calculated note_min                        as ecart_objectif,
           1 - calculated note / calculated note_avant_degradation      as degradation_moyenne,
           sum(note < note_min)                                         as nb_donnees_hors_tolerance,
           min(note)                                                    as note_plancher
    from QDD.donnees_&camp where critique = 1 and nb_controles > 0;

    create table work._i2 as
    select count(*)                as nb_donnees_critiques,
           mean(sensibilite)       as sensibilite_moyenne,
           sum(nb_controles = 0)   as nb_critiques_non_controlees
    from QDD.donnees_&camp where critique = 1;

    create table work._i3 as
    select mean(anteriorite = 0)   as taux_validation,
           mean(anteriorite)       as anteriorite_moyenne,
           mean(conforme)          as taux_conformite_controles
    from QDD.controles_&camp where critique = 1 and inclus_note = 1;

    create table work._i4 as
    select count(*) as nb_controles_restitution,
           mean(conforme) as taux_conformite_restitutions
    from QDD.controles_&camp where inclus_note = 0 and evalue = 1;

    create table QDD.indicateurs_&camp as
    select "&camp" as campagne length=8, "&arrete"d as date_arrete format=date9., *
    from work._i1, work._i2, work._i3, work._i4;
  quit;

  data QDD.indicateurs_&camp;
    set QDD.indicateurs_&camp;
    format note note_min note_avant_degradation ecart_objectif degradation_moyenne note_plancher
           sensibilite_moyenne taux_validation taux_conformite_controles taux_conformite_restitutions percent10.2;
  run;

  title "QDD — campagne &camp (arrêté &arrete)";
  proc print data=QDD.indicateurs_&camp noobs; run;
  title;
%mend;

/* ---------- 4. Déclinaison par axe d'analyse (éq. 40-42) ---------- */
/* axe : maille | etape | criteres | responsable (criteres multi-valué : éclaté) */
%macro qdd_axe(camp=, axe=, out=);
  data work._ax;
    set QDD.controles_&camp(where=(critique = 1 and inclus_note = 1));
    length modalite $60;
    %if &axe = criteres %then %do;
      do k = 1 to countw(criteres, ',');
        modalite = strip(scan(criteres, k, ','));
        output;
      end;
    %end;
    %else %do;
      modalite = &axe; output;
    %end;
  run;
  proc sql;
    create table work._axd as
    select a.modalite, a.donnee_id, d.sensibilite, d.note_min,
           sum(a.poids * a.resultat) / sum(a.poids) as note_d,
           count(*) as nb_controles, sum(a.conforme) as nb_conformes
    from work._ax as a inner join QDD.donnees_&camp as d on d.donnee_id = a.donnee_id
    group by a.modalite, a.donnee_id, d.sensibilite, d.note_min;

    create table &out as
    select modalite,
           sum(sensibilite * note_d) / sum(sensibilite)   as note    format=percent10.2,
           sum(sensibilite * note_min) / sum(sensibilite) as note_min format=percent10.2,
           calculated note - calculated note_min          as ecart_objectif format=percent10.2,
           count(*) as nb_donnees_critiques,
           sum(nb_controles) as nb_controles,
           sum(nb_conformes) / sum(nb_controles)          as taux_conformite format=percent10.1
    from work._axd group by modalite
    order by calculated note;
  quit;
%mend;
