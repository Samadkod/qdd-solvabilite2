/* =====================================================================
   98 — VÉRIFICATION AUTOMATIQUE : SAS vs moteur Python de référence
   À lancer après 99_executer.sas. Compare 43 valeurs (indicateurs des
   2 campagnes, gouvernance, 11 étapes de la variation) à donnees_demo/
   valeurs_attendues.csv, produit par le moteur Python testé.
   Résultat : table WORK.VERIFICATION + message dans le log.
   ===================================================================== */

data work._attendu;
  infile "&DEMO./valeurs_attendues.csv" dlm=';' dsd firstobs=2 truncover termstr=lf;
  length campagne $10 indicateur $40;
  input campagne indicateur valeur_attendue;
run;

%macro _long(camp);
  data work._w; merge QDD.indicateurs_&camp QDD.gouv_couverture_&camp QDD.gouv_anomalies_&camp; by campagne; run;
  proc transpose data=work._w out=work._l(rename=(_name_=indicateur col1=valeur_sas)); var _numeric_; run;
  data work._l; length campagne $10 indicateur $40; set work._l; campagne = "&camp"; run;
  proc append base=work._obtenu data=work._l force; run;
%mend;
proc datasets lib=work nolist; delete _obtenu; quit;
%_long(N1);
%_long(N);
data work._v; length campagne $10 indicateur $40; set QDD.variation;
  campagne = 'VARIATION'; indicateur = cats('etape_', _n_ - 1); valeur_sas = note; keep campagne indicateur valeur_sas; run;
proc append base=work._obtenu data=work._v force; run;

proc sql;
  create table work.verification as
  select a.campagne, a.indicateur, a.valeur_attendue, o.valeur_sas,
         abs(a.valeur_attendue - o.valeur_sas) as ecart,
         case when missing(o.valeur_sas) then 'MANQUANT'
              when abs(a.valeur_attendue - o.valeur_sas) < 1e-6 then 'OK'
              else 'ÉCART' end as verdict length=8
  from work._attendu as a
       left join work._obtenu as o
       on upcase(o.campagne) = upcase(a.campagne) and upcase(o.indicateur) = upcase(a.indicateur)
  order by verdict desc, a.campagne, a.indicateur;
  select count(*) into :_nko trimmed from work.verification where verdict ne 'OK';
quit;

title "Vérification SAS vs référence Python — &_nko écart(s)";
proc print data=work.verification noobs; run;
title;
data _null_;
  if &_nko = 0 then put 'NOTE: [QDD] PARITÉ SAS / PYTHON OK sur toutes les valeurs.';
  else put "WARNING: [QDD] &_nko valeur(s) en écart : voir WORK.VERIFICATION.";
run;
