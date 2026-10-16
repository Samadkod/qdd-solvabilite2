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

/* ---------- États QRT simplifiés et sortie de l'outil de provisionnement ---------- */
%imp(actuariat_be, SI, segment $20, arrete :yymmdd10. segment be_sinistres_brut);
%imp(qrt_s0501, SI, segment $20, arrete :yymmdd10. segment primes_acquises_brutes);
%imp(qrt_s1701, SI, segment $20, arrete :yymmdd10. segment be_sinistres_brut);
%imp(qrt_s1901_diagonale, SI, segment $20, arrete :yymmdd10. segment annee_survenance paiements_cumules);
%imp(qrt_s0602, SI, actif_id $8 classe $12 isin $14 cic $4, arrete :yymmdd10. actif_id classe isin cic valeur_marche);
%imp(qrt_s0201, SI, poste $40, arrete :yymmdd10. poste montant);

data SI.gestion_contrats;  set SI.gestion_contrats;  format date_effet date9.; run;
data SI.gestion_sinistres; set SI.gestion_sinistres; format date_survenance date_declaration date9.; run;

/* ---------- Référentiels QDD ---------- */
/* Dictionnaire des données (répertoire ACPR points 47-48 + règle de gestion, format, états QRT) */
%imp(repertoire_donnees, QDD,
     donnee_id $60 libelle $80 description $200 localisation $120 source $80 usage $120
     proprietaire $60 modalites $40 frequence_maj $20 critique_expert $5
     regle_gestion $200 format_attendu $40 etats_qrt $80,
     donnee_id libelle description localisation source usage proprietaire modalites frequence_maj critique_expert
     regle_gestion format_attendu etats_qrt);
/* Référentiel des contrôles : flux sécurisés, seuil fixe (restitution), inclusion dans la note */
%imp(referentiel_controles, QDD,
     controle_id $8 libelle $80 famille $15 donnee_id $60 criteres $8 frequence $1 etape $60
     responsable $60 fichier_sql $80 flux $40,
     controle_id libelle famille donnee_id criteres frequence poids etape responsable fichier_sql
     flux seuil_fixe inclus_note);
data QDD.referentiel_controles; set QDD.referentiel_controles; if missing(inclus_note) then inclus_note = 1; run;

/* Lignage : catalogue des flux et chemin de chaque donnée */
%imp(lignage_flux, QDD, flux_id $8 systeme_source $60 systeme_cible $60 traitement $120 mode $20 zr $5,
     flux_id systeme_source systeme_cible traitement mode zr);
data QDD.lignage_flux; set QDD.lignage_flux; zone_risque = (upcase(zr) = 'TRUE'); drop zr; run;
%imp(lignage_donnees, QDD, donnee_id $60 flux_id $8, donnee_id flux_id ordre);

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
