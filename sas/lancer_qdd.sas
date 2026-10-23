/* =====================================================================
   LANCER_QDD — POINT D'ENTRÉE UNIQUE DE LA CHAÎNE QDD
   1. Adapter &RACINE (seule ligne à modifier) : dossier qui contient sas/.
   2. Exécuter ce programme (F3).
   Étapes : contrôle de l'installation -> import -> 3 campagnes -> variation
            -> volumétrie -> rapport -> export Qlik -> vérification (59 valeurs).
   Résultat : table WORK.VERIFICATION + message « PARITÉ SAS / PYTHON OK » dans le journal.
   ===================================================================== */
%let RACINE = /home/&sysuserid./qdd-s2;
/* Exemple SAS OnDemand, projet rangé dans un sous-dossier :
   %let RACINE = /home/&sysuserid./sasuser.v94/MON_DOSSIER/qdd-s2; */

options mprint nosymbolgen nomlogic;

/* ---------- 1. Contrôle de l'installation : tous les fichiers à leur place ---------- */
%macro qdd_verifier_installation;
  %local liste i f n_abs;
  %let liste =
  00_config.sas
  01_import_demo.sas
  02_controles.sas
  03_campagne.sas
  04_variation.sas
  05_rapport.sas
  06_gouvernance.sas
  07_export_qlik.sas
  08_chargement.sas
  10_exercices_corriges.sas
  98_verifier.sas
  99_executer.sas
  README_SAS.md
  donnees_demo/actuariat_be.csv
  donnees_demo/actuariat_inputs.csv
  donnees_demo/compta_primes.csv
  donnees_demo/compta_reglements.csv
  donnees_demo/dwh_contrats.csv
  donnees_demo/dwh_sinistres.csv
  donnees_demo/gestion_contrats.csv
  donnees_demo/gestion_sinistres.csv
  donnees_demo/historique_resultats.csv
  donnees_demo/lignage_donnees.csv
  donnees_demo/lignage_flux.csv
  donnees_demo/modele_parametres.csv
  donnees_demo/placements_compta.csv
  donnees_demo/placements_depositaire.csv
  donnees_demo/qrt_s0201.csv
  donnees_demo/qrt_s0501.csv
  donnees_demo/qrt_s0602.csv
  donnees_demo/qrt_s1701.csv
  donnees_demo/qrt_s1901_diagonale.csv
  donnees_demo/reassurance_traites.csv
  donnees_demo/ref_activites_btp.csv
  donnees_demo/referentiel_controles.csv
  donnees_demo/relances_scr.csv
  donnees_demo/repertoire_donnees.csv
  donnees_demo/valeurs_attendues.csv
  ;
  %let n_abs = 0;
  %do i = 1 %to %sysfunc(countw(&liste, %str( )));
    %let f = %scan(&liste, &i, %str( ));
    %if %sysfunc(fileexist(&RACINE./sas/&f)) = 0 %then %do;
      %put ERROR: [QDD] fichier absent : &RACINE./sas/&f;
      %let n_abs = %eval(&n_abs + 1);
    %end;
  %end;
  %if &n_abs > 0 %then %do;
    %put ERROR: [QDD] &n_abs fichier(s) absent(s) : vérifier &RACINE et l arborescence sas/ et sas/donnees_demo/.;
    %abort cancel;
  %end;
  %put NOTE: [QDD] installation complète : %sysfunc(countw(&liste, %str( ))) fichiers trouvés sous &RACINE./sas.;
%mend qdd_verifier_installation;
%qdd_verifier_installation;

/* ---------- 2. Chaîne complète ---------- */
%put NOTE: [QDD] début de la chaîne : %sysfunc(datetime(), datetime20.);
%include "&RACINE./sas/99_executer.sas";
%put NOTE: [QDD] fin de la chaîne : %sysfunc(datetime(), datetime20.);
