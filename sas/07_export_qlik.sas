/* =====================================================================
   07 — EXPORT POUR QLIK SENSE (modèle en étoile, CSV « ; » UTF-8)
   Même schéma que qdd_s2/export_qlik.py : seules les clés de liaison gardent
   leur nom, les autres champs sont préfixés -> ni clé synthétique ni boucle.
   Script de chargement Qlik : sorties/qlik/chargement_qdd.qvs (fourni par le projet).
   %qdd_export_qlik(camps=N1 N, derniere=N)
   ===================================================================== */

/* Préfixe toutes les variables sauf les clés, puis exporte en CSV */
%macro _qlik(in=, nom=, prefixe=, cles=);
  %local liste;
  proc sql noprint;
    select catx('=', name, cats("&prefixe._", name)) into :liste separated by ' '
    from dictionary.columns
    where libname = %upcase("%scan(&in, 1, .)") and memname = %upcase("%scan(&in, 2, .)")
      and indexw(%upcase("&cles"), upcase(name)) = 0;
  quit;
  %local dates;
  proc sql noprint;   /* dates au format ISO, comme l'export Python */
    select name into :dates separated by ' ' from dictionary.columns
    where libname = %upcase("%scan(&in, 1, .)") and memname = %upcase("%scan(&in, 2, .)")
      and upcase(format) like 'DATE%';
  quit;
  data work._q;
    set &in;
    %if %length(&dates) %then %do; format &dates yymmdd10.; %end;
    %if %length(&liste) %then %do; rename &liste; %end;
  run;
  proc export data=work._q outfile="&SORTIE./qlik/&nom..csv" dbms=dlm replace;
    delimiter = ';';
  run;
%mend;

%macro qdd_export_qlik(camps=, derniere=);
  %local i c;
  libname _q "&SORTIE./qlik"; libname _q clear;   /* crée le dossier */
  proc datasets lib=work nolist; delete f_indicateur; quit;

  /* Tables empilées sur les campagnes */
  data work.d_campagne;
    length campagne $8;
    set %do i = 1 %to %sysfunc(countw(&camps)); %let c = %scan(&camps, &i);
          QDD.indicateurs_&c(keep=campagne date_arrete) %end;;
  run;
  data work.f_note_donnee;
    length campagne $8 cle_cd $80;
    set %do i = 1 %to %sysfunc(countw(&camps)); %let c = %scan(&camps, &i);
          QDD.donnees_&c(in=_in&i keep=donnee_id sensibilite critique note note_avant_degradation note_min
                         statut nb_controles criteres_couverts) %end;;
    %do i = 1 %to %sysfunc(countw(&camps)); if _in&i then campagne = "%scan(&camps, &i)"; %end;
    cle_cd = catx('|', campagne, donnee_id);
  run;
  data work.f_resultat;
    length cle_cd $80;
    set %do i = 1 %to %sysfunc(countw(&camps)); %let c = %scan(&camps, &i);
          QDD.controles_&c(in=_in&i keep=point_id controle donnee_id maille resultat_brut mesure anteriorite
                           resultat seuil statut inclus_note date_derniere_real) %end;;
    %do i = 1 %to %sysfunc(countw(&camps)); if _in&i then cle_cd = catx('|', "%scan(&camps, &i)", donnee_id); %end;
    rename controle = controle_id;
    drop donnee_id;
  run;
  /* indicateurs de toutes les campagnes (méthode + gouvernance), en format long */
  %do i = 1 %to %sysfunc(countw(&camps)); %let c = %scan(&camps, &i);
    data work._ind;
      merge QDD.indicateurs_&c QDD.gouv_couverture_&c QDD.gouv_anomalies_&c;
      by campagne;
    run;
    proc transpose data=work._ind out=work._indl(rename=(_name_=indicateur col1=valeur));
      by campagne; var _numeric_;
    run;
    proc append base=work.f_indicateur data=work._indl(where=(indicateur ne 'date_arrete')) force; run;
  %end;
  data work.f_variation; set QDD.variation; length campagne $8; campagne = "&derniere"; ordre = _n_ - 1; run;
  data work.b_lignage;
    set QDD.couverture_&derniere(keep=donnee_id flux_id ordre couvert controles
                                 rename=(controles=controles_couvrants));
  run;

  %_qlik(in=work.d_campagne,       nom=D_CAMPAGNE,    prefixe=cp,  cles=campagne);
  %_qlik(in=QDD.repertoire_donnees,nom=D_DONNEE,      prefixe=dd,  cles=donnee_id);
  %_qlik(in=QDD.referentiel_controles, nom=D_CONTROLE, prefixe=dc, cles=controle_id);
  %_qlik(in=QDD.lignage_flux,      nom=D_FLUX,        prefixe=fx,  cles=flux_id);
  %_qlik(in=work.b_lignage,        nom=B_LIGNAGE,     prefixe=lg,  cles=donnee_id flux_id);
  %_qlik(in=work.f_note_donnee,    nom=F_NOTE_DONNEE, prefixe=nd,  cles=campagne donnee_id cle_cd);
  %_qlik(in=work.f_resultat,       nom=F_RESULTAT,    prefixe=rs,  cles=cle_cd controle_id);
  %_qlik(in=work.f_indicateur,     nom=F_INDICATEUR,  prefixe=ind, cles=campagne);
  %_qlik(in=QDD.registre_anomalies,nom=F_ANOMALIE,    prefixe=an,  cles=donnee_id);
  %_qlik(in=work.f_variation,      nom=F_VARIATION,   prefixe=vr,  cles=campagne);
%mend;
