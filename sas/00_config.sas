/* =====================================================================
   QDD SOLVABILITÉ 2 — CONFIGURATION
   Méthode : mémoire C. Motard (ISFA 2024), version corrigée.
   Portage SAS du prototype Python qdd_s2 (mêmes formules, mêmes noms).
   ---------------------------------------------------------------------
   À ADAPTER EN PRODUCTION :
     - &RACINE : dossier du projet
     - libname SI : bibliothèque des tables source (gestion, entrepôt,
       comptabilité, actuariat, placements). En prod, remplacer par
       les libname existants (Oracle, SAS datasets...) ou des vues.
     - libname QDD : bibliothèque de travail QDD (référentiels,
       historique des résultats, sorties).
   ===================================================================== */

/* &RACINE est défini dans 99_executer.sas (dossier du projet, ex. /home/<user>/qdd-s2) */
%let DEMO   = &RACINE./sas/donnees_demo;      /* CSV de démonstration           */
%let SORTIE = &RACINE./sas/sorties;           /* rapports Excel                 */

options dlcreatedir;                          /* crée les dossiers si besoin    */
libname SI  "&RACINE./sas/lib_si";            /* tables source (démo)           */

/* ---------- PRODUCTION : bases distantes via ODBC (gabarit, à adapter avec la DSI) ----------
   Les noms de DSN, schémas et comptes ci-dessous sont des EXEMPLES. Ne jamais écrire de mot de
   passe en clair : utiliser un DSN système, un authdomain SAS ou un fichier de paramètres protégé.

   libname GEST odbc dsn="DSN_GESTION" schema="PROD" readbuff=10000;      -- outil de gestion
   libname DWH  odbc dsn="DSN_ENTREPOT" schema="DWH" readbuff=10000;      -- entrepôt

   Requête passée directement au SGBD (pass-through) pour filtrer à la source :
   proc sql;
     connect to odbc as cx (dsn="DSN_ENTREPOT" authdomain="QDD_AUTH");
     create table SI.dwh_sinistres as
     select * from connection to cx
       (select arrete, sinistre_id, segment, provision_dossier, reglements_cumules
        from dwh.sinistres where arrete = '2026-09-30');
     disconnect from cx;
   quit;
   Les contrôles de 02_controles.sas lisent ensuite SI.<table> sans modification. */
libname QDD "&RACINE./sas/lib_qdd";           /* référentiels + résultats QDD   */
libname _tmp "&SORTIE."; libname _tmp clear;  /* crée le dossier des rapports */

/* ---------- Paramètres de la méthode (à justifier dans la politique QDD) ---------- */
%let SEUIL        = 0.01;     /* seuil de significativité : critique si s_d >= seuil (éq. 5)      */
%let MODE_TOL     = DONNEE;   /* DONNEE : ΔSCR max par donnée (éq. 10) | GLOBALE (éq. 21)          */
%let DSCR         = 0.005;    /* ΔSCR max : variation acceptable du SCR due à une donnée           */
%let TOL_GLOBALE  = 0.05;     /* tolérance globale de non-QDD (si MODE_TOL = GLOBALE)              */
%let COEF         = 0.05;     /* coefficient de dégradation des contrôles non réalisés (éq. 36)    */
%let DEGRADATION  = SIMPLE;   /* SIMPLE (retenue par le mémoire) | COMPOSEE (éq. 37)               */
%let MARGE        = 0.02;     /* zone orange : note entre min - marge et min                      */
%let METHODE_ECART= MEMOIRE;  /* MEMOIRE : max |b_j/b_k - 1| | SYMETRIQUE : min(1,|a-b|/max(|a|,|b|)) */
%let POND_MONTANT = 1;        /* 1 : ratio d'anomalie pondéré en montant si disponible ; 0 : en nombre */
%let CHOC_REF     = 0.15;     /* choc de référence pour la sensibilité                             */
%let SEUIL_NL     = 0.10;     /* alerte non-linéarité au-delà de 10 %                              */
