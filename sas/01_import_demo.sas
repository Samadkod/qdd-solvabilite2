/* =====================================================================
   01 — IMPORT DES DONNÉES DE DÉMONSTRATION (assureur BTP FICTIF)
   En production, ce programme est remplacé par les libname réels.
   Imports en DATA step avec formats explicites (plus robuste que PROC IMPORT).
   ===================================================================== */

%macro imp(table, lib, longueurs, input);
  data &lib..&table;
    infile "&DEMO./&table..csv" dlm=';' dsd firstobs=2 truncover encoding="utf-8" termstr=lf;
    length &longueurs;
    input &input;
    format _numeric_ best12.;
    %if %index(&input, arrete) %then %do; format arrete date9.; %end;
  run;
%mend;

/* ---------- Système d'information (source) ---------- */
%imp(gestion_contrats, SI, contrat_id $12 segment $20 code_activite $8,
     arrete :yymmdd10. contrat_id segment code_activite date_effet :yymmdd10. prime_emise prime_acquise);
%imp(dwh_contrats, SI, contrat_id $12 segment $20,
     arrete :yymmdd10. contrat_id segment prime_acquise);
%imp(compta_primes, SI, segment $20, arrete :yymmdd10. segment prime_acquise);
%imp(gestion_sinistres, SI, sinistre_id $12 contrat_id $12 segment $20,
     arrete :yymmdd10. sinistre_id contrat_id segment date_survenance :yymmdd10. date_declaration :yymmdd10.
     reglements_cumules provision_dossier);
%imp(dwh_sinistres, SI, sinistre_id $12 segment $20,
     arrete :yymmdd10. sinistre_id segment provision_dossier reglements_cumules);
%imp(actuariat_inputs, SI, segment $20, arrete :yymmdd10. segment provision_dossier_total reglements_total);
%imp(compta_reglements, SI, segment $20, arrete :yymmdd10. segment reglements);
%imp(reassurance_traites, SI, segment $20, arrete :yymmdd10. segment taux_cession);
%imp(modele_parametres, SI, segment $20, arrete :yymmdd10. segment taux_cession);
%imp(placements_depositaire, SI, actif_id $8 classe $12 isin $14 cic $4,
     arrete :yymmdd10. actif_id classe isin cic valeur_marche);
%imp(placements_compta, SI, actif_id $8, arrete :yymmdd10. actif_id valeur_marche);
%imp(ref_activites_btp, SI, code_activite $8, code_activite);

data SI.gestion_contrats;  set SI.gestion_contrats;  format date_effet date9.; run;
data SI.gestion_sinistres; set SI.gestion_sinistres; format date_survenance date_declaration date9.; run;

/* ---------- Référentiels QDD ---------- */
%imp(repertoire_donnees, QDD,
     donnee_id $60 libelle $80 description $200 localisation $120 source $80 usage $120
     proprietaire $60 modalites $40 frequence_maj $20 critique_expert $5,
     donnee_id libelle description localisation source usage proprietaire modalites frequence_maj critique_expert);
%imp(referentiel_controles, QDD,
     controle_id $8 libelle $80 famille $15 donnee_id $60 criteres $8 frequence $1 etape $60
     responsable $60 fichier_sql $80,
     controle_id libelle famille donnee_id criteres frequence poids etape responsable fichier_sql);

/* Relances du moteur SCR fournies par l'actuariat : 1 ligne par (arrêté, donnée, choc) ; choc 0 = SCR de référence */
%imp(relances_scr, QDD, donnee_id $60, arrete :yymmdd10. donnee_id choc valeur scr);

/* Historique initial des résultats (campagnes antérieures saisies) */
data QDD.hist_resultats;
  infile "&DEMO./historique_resultats.csv" dlm=';' dsd firstobs=2 truncover encoding="utf-8" termstr=lf;
  length point_id $40 controle $8 maille $32 detail $120;
  input point_id date_realisation :yymmdd10. resultat_brut detail;
  controle = scan(point_id, 1, '|');
  maille   = scan(point_id, 2, '|');
  mesure   = 1 - resultat_brut;
  format date_realisation date9.;
run;
