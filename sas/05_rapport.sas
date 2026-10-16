/* =====================================================================
   05 — RAPPORT EXCEL DE CAMPAGNE (ODS EXCEL + PROC REPORT)
   %qdd_rapport(camp=N, prec=N1)
   ===================================================================== */

%macro _feu(var);
  compute &var;
    if &var = 'rouge'       then call define(_col_, 'style', 'style={background=#F8DEDE color=#AD3030 fontweight=bold}');
    else if &var = 'orange' then call define(_col_, 'style', 'style={background=#FBEBCB color=#9C6400 fontweight=bold}');
    else if &var = 'vert'   then call define(_col_, 'style', 'style={background=#DCF1E4 color=#22744A}');
  endcomp;
%mend;

%macro qdd_rapport(camp=, prec=);
  ods excel file="&SORTIE./rapport_qdd_&camp..xlsx" style=htmlblue
      options(sheet_name='Synthèse' embedded_titles='yes' frozen_headers='yes' autofilter='none');

  title "Qualité des données Solvabilité 2 — campagne &camp";
  data work._synth; set QDD.indicateurs_&prec QDD.indicateurs_&camp; run;
  proc report data=work._synth;
    columns campagne date_arrete note note_min ecart_objectif note_avant_degradation degradation_moyenne
            nb_donnees_critiques nb_donnees_hors_tolerance taux_validation taux_conformite_controles;
    define campagne / display 'Campagne';
    define date_arrete / display 'Arrêté';
    define note / display 'Note QDD agrégée';
    define note_min / display 'Objectif (note min)';
    define ecart_objectif / display 'Écart à l''objectif';
    define note_avant_degradation / display 'Note avant dégradation';
    define degradation_moyenne / display 'Dégradation moyenne';
    define nb_donnees_critiques / display 'Données critiques';
    define nb_donnees_hors_tolerance / display 'Hors tolérance';
    define taux_validation / display 'Contrôles à jour';
    define taux_conformite_controles / display 'Contrôles conformes';
  run;

  ods excel options(sheet_name='Variation');
  title "Pourquoi la note a bougé (&prec -> &camp)";
  proc report data=QDD.variation(where=(missing(impact) or abs(impact) > 1e-9));
    columns etape note impact;
    define etape / display 'Étape';
    define note / display 'Note';
    define impact / display 'Impact';
  run;

  ods excel options(sheet_name='Données');
  title "Données — criticité, note, objectif";
  proc report data=QDD.donnees_&camp;
    columns donnee_id libelle proprietaire sensibilite critique note note_min statut criteres_couverts nb_controles non_linearite;
    define donnee_id / display 'Donnée';
    define libelle / display 'Libellé';
    define proprietaire / display 'Propriétaire';
    define sensibilite / display 'Sensibilité SCR';
    define critique / display 'Critique';
    define note / display 'Note QDD';
    define note_min / display 'Note min';
    define statut / display 'Statut';
    define criteres_couverts / display 'E/X/P';
    define nb_controles / display 'Nb contrôles';
    define non_linearite / display 'Non-linéarité';
    %_feu(statut)
  run;

  ods excel options(sheet_name='Contrôles');
  title "Points de contrôle";
  proc report data=QDD.controles_&camp;
    columns point_id libelle donnee_id etape responsable resultat_brut anteriorite resultat seuil statut detail date_derniere_real;
    define point_id / display 'Point';
    define libelle / display 'Libellé';
    define donnee_id / display 'Donnée';
    define etape / display 'Étape';
    define responsable / display 'Responsable';
    define resultat_brut / display 'Résultat brut';
    define anteriorite / display 'Antériorité';
    define resultat / display 'Résultat retenu';
    define seuil / display 'Seuil';
    define statut / display 'Statut';
    define detail / display 'Détail';
    define date_derniere_real / display 'Dernière réalisation';
    %_feu(statut)
  run;

  %qdd_axe(camp=&camp, axe=maille,      out=work._ax_maille);
  %qdd_axe(camp=&camp, axe=etape,       out=work._ax_etape);
  %qdd_axe(camp=&camp, axe=criteres,    out=work._ax_crit);
  %qdd_axe(camp=&camp, axe=responsable, out=work._ax_resp);
  ods excel options(sheet_name='Axes');
  title "Par segment / classe d'actif"; proc print data=work._ax_maille noobs; run;
  title "Par étape de la chaîne";       proc print data=work._ax_etape noobs; run;
  title "Par critère S2";                proc print data=work._ax_crit noobs; run;
  title "Par responsable";               proc print data=work._ax_resp noobs; run;

  ods excel options(sheet_name='Sensibilités');
  title "Sensibilités du SCR et test de linéarité";
  proc print data=QDD.sens_&camp noobs; format sensibilite non_linearite percent10.2; run;

  title;
  ods excel close;
%mend;
