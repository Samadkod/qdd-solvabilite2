/* =====================================================================
   99 — EXÉCUTION COMPLÈTE (démo : 2 campagnes + variation + rapport)
   Dans SAS Studio : ouvrir ce fichier, ajuster &RACINE dans 00_config.sas, F3.
   ===================================================================== */
%let RACINE = /home/&sysuserid./qdd-s2;

%include "&RACINE./sas/00_config.sas";
%include "&RACINE./sas/01_import_demo.sas";     /* à retirer en production */
%include "&RACINE./sas/02_controles.sas";
%include "&RACINE./sas/03_campagne.sas";
%include "&RACINE./sas/04_variation.sas";
%include "&RACINE./sas/05_rapport.sas";

/* Campagne N-1 : C07, C08, R05 non réalisés */
%qdd_campagne(camp=N1, arrete=30JUN2026, non_realises=C07 C08 R05);
/* Campagne N : C07, R04, C08, R05 non réalisés */
%qdd_campagne(camp=N,  arrete=30SEP2026, non_realises=C07 R04 C08 R05);

%qdd_variation(prec=N1, cour=N);
%qdd_rapport(camp=N, prec=N1);

/* Valeurs attendues (moteur Python, mêmes données) :
   N-1 : note 98,76 % | objectif 97,10 %
   N   : note 97,45 % | objectif 97,10 % | 2 données hors tolérance (provisions RC décennale rouge, date de survenance orange)
   Variation : -0,72 pt QDD mesurée, -0,59 pt antériorité, -0,01 pt sensibilités */
