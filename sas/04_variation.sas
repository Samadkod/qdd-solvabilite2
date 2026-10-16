/* =====================================================================
   04 — ANALYSE DE LA VARIATION DE LA NOTE ENTRE DEUX CAMPAGNES
   Substitutions successives (mémoire §3.1.3, tableau 20) :
   on part de N-1 et on bascule un facteur à la fois vers sa valeur N.
   %qdd_variation(prec=N1, cour=N, coef_prec=0.05, coef_cour=0.05, out=QDD.VARIATION)
   Hypothèse : dégradation SIMPLE (celle retenue par le mémoire).
   ===================================================================== */

%macro _qdd_note_hybride(f_supctl, f_supcrit, f_res, f_ant, f_coef, f_poids, f_addctl, f_sens, f_addcrit,
                         coef_prec, coef_cour);
  /* contrôles hybrides */
  data work._hc;
    set work._vc;
    if not ((in_p and (in_c or not &f_supctl)) or (in_c and not in_p and &f_addctl)) then delete;
    nouveau = (in_c and not in_p);
    rb  = ifn(in_c and (&f_res   or nouveau), rb_c,  rb_p);
    ant = ifn(in_c and (&f_ant   or nouveau), ant_c, ant_p);
    po  = ifn(in_c and (&f_poids or nouveau), po_c,  po_p);
    coef = ifn(&f_coef, &coef_cour, &coef_prec);
    r = rb * max(0, 1 - coef * ant);
  run;
  /* données hybrides */
  data work._hd;
    set work._vd;
    sens = ifn(in_c and (&f_sens or not in_p), s_c, s_p);
    crit = (crit_p = 1 and (crit_c = 1 or not &f_supcrit)) or (crit_c = 1 and &f_addcrit);
  run;
  proc sql noprint;
    select sum(d.sens * n.note_d) / sum(d.sens) into :_note trimmed
    from (select donnee_id, sum(po * r) / sum(po) as note_d from work._hc group by donnee_id) as n
         inner join work._hd as d on d.donnee_id = n.donnee_id
    where d.crit = 1;
  quit;
%mend;

%macro qdd_variation(prec=, cour=, coef_prec=&COEF, coef_cour=&COEF, out=QDD.variation);
  %local k libs f1 f2 f3 f4 f5 f6 f7 f8 f9 note_av lib _note;  /* _note : rempli par l'INTO du macro appelé */

  proc sql;
    create table work._vc as
    select coalesce(c.point_id, p.point_id) as point_id length=40,
           coalesce(c.donnee_id, p.donnee_id) as donnee_id length=60,
           p.resultat_brut as rb_p, c.resultat_brut as rb_c,
           p.anteriorite   as ant_p, c.anteriorite  as ant_c,
           p.poids         as po_p, c.poids         as po_c,
           (not missing(p.point_id)) as in_p, (not missing(c.point_id)) as in_c
    from QDD.controles_&prec(where=(inclus_note = 1)) as p
         full join QDD.controles_&cour(where=(inclus_note = 1)) as c
         on c.point_id = p.point_id;

    create table work._vd as
    select coalesce(c.donnee_id, p.donnee_id) as donnee_id length=60,
           p.sensibilite as s_p, c.sensibilite as s_c,
           coalesce(p.critique, 0) as crit_p, coalesce(c.critique, 0) as crit_c,
           (not missing(p.donnee_id)) as in_p, (not missing(c.donnee_id)) as in_c
    from QDD.donnees_&prec as p full join QDD.donnees_&cour as c
         on c.donnee_id = p.donnee_id;
  quit;

  data &out; length etape $70 note impact 8; format note impact percent10.2; stop; run;

  %let libs = Suppression de contrôles|Sortie de données critiques|QDD mesurée par les contrôles|Antériorité des contrôles|Coefficient de dégradation|Pondération des contrôles|Ajout de contrôles|Sensibilités des données critiques|Entrée de données critiques;
  %do k = 1 %to 9; %let f&k = 0; %end;

  %_qdd_note_hybride(&f1,&f2,&f3,&f4,&f5,&f6,&f7,&f8,&f9,&coef_prec,&coef_cour);
  %let note_av = &_note;
  proc sql; insert into &out set etape = "Note QDD agrégée &prec", note = &note_av; quit;

  /* ordre : suppr. contrôles, sortie critiques, résultats, antériorité, coef, poids, ajout contrôles, sensibilités, entrée critiques */
  %do k = 1 %to 9;
    %let f&k = 1;
    %_qdd_note_hybride(&f1,&f2,&f3,&f4,&f5,&f6,&f7,&f8,&f9,&coef_prec,&coef_cour);
    %let lib = %scan(&libs, &k, |);
    proc sql; insert into &out set etape = "&lib", note = &_note, impact = %sysevalf(&_note - &note_av); quit;
    %let note_av = &_note;
  %end;
  proc sql; insert into &out set etape = "Note QDD agrégée &cour", note = &note_av; quit;

  title "Analyse de variation &prec -> &cour";
  proc print data=&out noobs; run;
  title;
%mend;
