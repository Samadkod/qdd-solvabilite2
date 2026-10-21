/* =====================================================================
   08 — CONTRÔLES DE CHARGEMENT (niveau 0) : volumétrie des tables sources
   Miroir de chargement.py (même règle, mêmes seuils).
   %qdd_volumetrie(prec=30JUN2026, cour=30SEP2026)  -> QDD.volumetrie
   Règle :
     table vide à l'arrêté                                   -> Bloquant
     moins de &PETITE lignes au trimestre précédent : nombre
       de lignes différent                                   -> À expliquer
     sinon |lignes / lignes précédentes - 1| > &SEUIL_VOL    -> À expliquer
     sinon                                                   -> Normal
   Seuil de 10 % : variation trimestrielle normale <= 1,2 % sur le SI
   fictif ; à recalibrer sur l'historique réel (max observé + marge).
   ===================================================================== */
%let SEUIL_VOL = 0.10;
%let PETITE    = 50;

%macro qdd_volumetrie(prec=, cour=);
  %local n i;
  proc sql noprint;
    select memname into :tv1- from dictionary.columns
    where libname = 'SI' and upcase(name) = 'ARRETE';
    %let n = &sqlobs;
  quit;
  proc datasets lib=work nolist nowarn; delete _vol; quit;
  %do i = 1 %to &n;
    proc sql;
      create table work._v as
      select "%lowcase(&&tv&i)" as table_source length=32,
             sum(arrete = "&prec"d) as lignes_prec,
             sum(arrete = "&cour"d) as lignes
      from SI.&&tv&i;
    quit;
    proc append base=work._vol data=work._v force; run;
  %end;
  data QDD.volumetrie;
    set work._vol;
    length statut $16;
    if lignes_prec > 0 then variation = lignes / lignes_prec - 1;
    if lignes = 0 then statut = "Bloquant";
    else if lignes_prec = 0 then statut = "Sans référence";
    else if lignes_prec < &PETITE then do;
      if lignes ne lignes_prec then statut = "À expliquer";
      else statut = "Normal";
    end;
    else if abs(round(variation, 1e-10)) > &SEUIL_VOL then statut = "À expliquer";
    else statut = "Normal";
    format variation percent9.1;
  run;
%mend;
