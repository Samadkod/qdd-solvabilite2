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
%include "&RACINE./sas/06_gouvernance.sas";
%include "&RACINE./sas/07_export_qlik.sas";

/* Démo : on repart d'un registre et d'un journal vides */
proc datasets lib=QDD nolist; delete registre_anomalies journal_executions; quit;

/* Campagne N-1 : C07, C08, R05 non réalisés */
%qdd_campagne(camp=N1, arrete=30JUN2026, non_realises=C07 C08 R05);
%qdd_couverture(camp=N1);
%qdd_registre(camp=N1, arrete=30JUN2026);
%qdd_journal(camp=N1, arrete=30JUN2026);

/* Campagne N : C07, R04, C08, R05 non réalisés */
%qdd_campagne(camp=N,  arrete=30SEP2026, non_realises=C07 R04 C08 R05);
%qdd_couverture(camp=N);
%qdd_registre(camp=N, arrete=30SEP2026);
%qdd_journal(camp=N, arrete=30SEP2026);

%qdd_variation(prec=N1, cour=N);
%qdd_rapport(camp=N, prec=N1);
%qdd_export_qlik(camps=N1 N, derniere=N);

/* Vérification automatique contre la référence Python (43 valeurs) */
%include "&RACINE./sas/98_verifier.sas";

/* Repères (moteur Python, mêmes données) :
   N-1 : note 98,76 % | objectif 97,10 %
   N   : note 97,45 % | objectif 97,10 % | 2 données hors tolérance (provisions RC décennale rouge,
         date de survenance orange) | restitutions QRT conformes 10/11 (Q02 dommages-ouvrage en écart)
         | couverture des zones de risque 25/33 | 14 anomalies ouvertes dont 4 hautes
   Variation : -0,72 pt QDD mesurée, -0,59 pt antériorité, -0,01 pt sensibilités */
