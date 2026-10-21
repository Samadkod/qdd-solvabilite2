"""D'où sortent les chiffres : décorticage du calcul et lecture des graphiques, en langage courant.

Chaque explication est recalculée à partir des éléments affichés (nombre d'erreurs, retard, poids,
sensibilité…) puis comparée au moteur dans tests/test_explications.py : le texte ne peut pas
diverger du calcul réel.
"""
from __future__ import annotations

import pandas as pd

from qdd_s2.campagne import Config

CHOC = Config().choc_sensibilite  # choc appliqué à chaque donnée pour mesurer sa sensibilité (15 %)
PERIODE = {"T": "trimestre", "S": "semestre", "A": "an"}

ETAPES_EN_CLAIR = {
    "Suppression de contrôles": "des contrôles ont été retirés du dispositif",
    "Sortie de données critiques": "des données ne sont plus jugées critiques",
    "QDD mesurée par les contrôles (antériorité intacte)": "les contrôles ont trouvé davantage d'erreurs dans les données",
    "Antériorité des contrôles": "des contrôles n'ont pas été refaits à temps (pénalité de retard)",
    "Coefficient de dégradation": "la pénalité de retard a été modifiée",
    "Pondération des contrôles": "le poids relatif des contrôles a changé",
    "Ajout de contrôles": "de nouveaux contrôles ont été ajoutés",
    "Sensibilités des données critiques": "le poids des données dans le SCR a changé",
    "Entrée de données critiques": "de nouvelles données sont devenues critiques",
}

ETAPES_COURTES = {
    "Suppression de contrôles": "Contrôles retirés",
    "Sortie de données critiques": "Données qui ne sont plus critiques",
    "QDD mesurée par les contrôles (antériorité intacte)": "Plus d'erreurs trouvées",
    "Antériorité des contrôles": "Contrôles en retard",
    "Coefficient de dégradation": "Pénalité de retard modifiée",
    "Pondération des contrôles": "Poids des contrôles modifié",
    "Ajout de contrôles": "Contrôles ajoutés",
    "Sensibilités des données critiques": "Poids des données dans le SCR",
    "Entrée de données critiques": "Nouvelles données critiques",
}
MODALITES = {"RC_DECENNALE": "RC décennale", "DOMMAGES_OUVRAGE": "Dommages-ouvrage", "AUTO_FLOTTE": "Flottes auto",
             "ACTIONS": "Actions", "OBLIGATIONS": "Obligations", "TOUS": "Transverse (tous segments)",
             "E": "Exhaustivité", "X": "Exactitude", "P": "Pertinence"}


def p(x, d=2):
    return "—" if x is None or pd.isna(x) else f"{x * 100:.{d}f} %".replace(".", ",")


def m(x, d=1):
    """Montant en millions d'euros, format français."""
    return f"{x:,.{d}f} M€".replace(",", " ").replace(".", ",")


def pt(x):
    return f"{x * 100:+.2f} point".replace(".", ",")


# ====================================================================== calculs
def facteur_retard(anteriorite: float, coef: float, methode: str) -> float:
    if methode == "simple":
        return max(0.0, 1.0 - coef * anteriorite)
    return (1.0 - coef) ** anteriorite


def decortiquer_donnee(c: dict, donnee_id: str) -> dict:
    """Toutes les étapes du calcul d'une donnée critique, recalculées pas à pas."""
    par = c["params"]
    d = c["donnees"].set_index("donnee_id").loc[donnee_id]
    ctrl = c["controles"]
    cs = ctrl[(ctrl["donnee_id"] == donnee_id) & ctrl["inclus_note"]].copy()
    cs["facteur"] = [facteur_retard(a, par.coef_degradation, par.methode_degradation) for a in cs["anteriorite"]]
    cs["recalcul"] = cs["resultat_brut"] * cs["facteur"]
    note = float((cs["recalcul"] * cs["poids"]).sum() / cs["poids"].sum())
    sens = c["sens"].set_index("donnee_id")["sensibilite"]
    mesurees = sens[sens >= par.seuil_significativite]
    a_dire_expert = donnee_id not in sens.index  # pas de sensibilité calculable (ex. une date)
    s = float(d["sensibilite"])
    note_min = 1 - par.delta_scr_max / s
    statut = "vert" if note >= note_min else ("orange" if note >= note_min - par.marge_alerte else "rouge")
    return {"donnee": d, "controles": cs, "note": note, "note_min": note_min, "statut": statut,
            "sensibilite": s, "a_dire_expert": a_dire_expert, "nb_mesurees": int(len(mesurees)),
            "moyenne_mesurees": float(mesurees.mean()), "scr": float(c["scr"]), "params": par}


def decortiquer_globale(c: dict) -> dict:
    """Note globale = moyenne des notes des données critiques, pondérée par leur sensibilité."""
    par = c["params"]
    dd = c["donnees"]
    t = dd[dd["critique"] & (dd["nb_controles"] > 0)].sort_values("sensibilite", ascending=False).copy()
    t["part"] = t["poids_donnee"] / t["poids_donnee"].sum()
    t["apport"] = t["note"] * t["part"]
    s_moy = float(t["sensibilite"].mean())
    return {"table": t, "note": float(t["apport"].sum()), "objectif": float((t["note_min"] * t["part"]).sum()),
            "objectif_formule": 1 - par.delta_scr_max / s_moy, "s_moy": s_moy, "params": par}


# ====================================================================== textes
def texte_controle(r, date_campagne=None) -> str:
    """Comment le résultat brut d'un contrôle a été obtenu, en une ou deux phrases."""
    det = str(r.detail) if pd.notna(r.detail) else ""
    ancien = (date_campagne is not None and pd.notna(r.date_derniere_real)
              and pd.Timestamp(r.date_derniere_real) < pd.Timestamp(date_campagne))
    prefixe = (f"*Mesuré lors de la campagne du {pd.Timestamp(r.date_derniere_real):%d/%m/%Y}, pas refait depuis.* "
               if ancien and not det.startswith("Résultat antérieur") else "")
    return prefixe + _texte_mesure(r, det)


def _texte_mesure(r, det: str) -> str:
    if det.startswith("Résultat antérieur"):
        return (f"Ce contrôle **n'a pas été refait** : on reprend son dernier résultat connu "
                f"({p(r.resultat_brut)}, {det.split('(')[-1].rstrip(')')}).")
    if r.famille == "rapprochement" and "|" in det and pd.notna(r.mesure_non_qdd):
        vals = [float(v.replace(",", "")) for v in det.split("|")]
        sources = " ; ".join(m(v / 1e6, 2) for v in vals)
        return (f"On compare le même total dans {len(vals)} outils : {sources}. Le plus grand écart mesuré vaut "
                f"{p(r.mesure_non_qdd, 3)}, donc le résultat est 100 % − {p(r.mesure_non_qdd, 3)} = "
                f"**{p(r.resultat_brut)}**.")
    if " anomalies / " in det:
        n, reste = det.split(" anomalies / ")
        if " ; " in reste:
            tot, montants = reste.split(" ; ")
            ma, mt = [float(x.replace("€", "").replace(",", "").strip()) for x in montants.split("/")]
            return (f"Le contrôle trouve **{n} lignes en erreur sur {tot}**. En montant, elles pèsent "
                    f"{m(ma / 1e6, 2)} sur {m(mt / 1e6, 2)}, soit {p(r.mesure_non_qdd, 3)} : le résultat est "
                    f"100 % − {p(r.mesure_non_qdd, 3)} = **{p(r.resultat_brut)}**.")
        return (f"Le contrôle trouve **{n} lignes en erreur sur {reste}**, soit {p(r.mesure_non_qdd, 3)} : "
                f"résultat **{p(r.resultat_brut)}**.")
    return f"Résultat du contrôle : **{p(r.resultat_brut)}**."


def _majuscule(t: str) -> str:
    return t[:1].upper() + t[1:]


def lire_variation(var: pd.DataFrame) -> str:
    debut, fin = var["note"].iloc[0], var["note"].iloc[-1]
    lignes = [f"**Comment lire ce graphique.** On part de la note du trimestre précédent ({p(debut)}) et on "
              f"change **une seule chose à la fois** pour mesurer son effet. Chaque barre est une cause : vers la "
              f"gauche (rouge), elle a fait baisser la note ; vers la droite (vert), elle l'a fait monter. "
              f"Additionnées, les barres donnent la variation totale jusqu'à la note d'arrivée ({p(fin)})."]
    effets = var[var["impact"].notna() & (var["impact"].abs() > 1e-6)].sort_values("impact")
    if effets.empty:
        lignes.append("**Ici :** rien n'a bougé entre les deux campagnes.")
    else:
        lignes.append(f"**Ici :** la note {'baisse' if fin < debut else 'monte'} de {pt(fin - debut)[1:]}. "
                      + " ".join(f"{_majuscule(ETAPES_EN_CLAIR.get(r.etape, r.etape))} : {pt(r.impact)}."
                                 for r in effets.itertuples()))
    return "\n\n".join(lignes)


AXES = {"maille": "segment ou classe d'actif", "etape": "étape de la chaîne", "criteres": "critère de qualité",
        "responsable": "responsable"}
CRITERES = {"E": "Exhaustivité (rien ne manque)", "X": "Exactitude (pas d'erreur)", "P": "Pertinence",
            "TOUS": "Tous segments (contrôles transverses)"}


def lire_axe(a: pd.DataFrame, axe: str) -> str:
    lignes = [f"**Comment lire ce graphique.** Une barre par {AXES[axe]}. Elle montre de combien de points la "
              "note du groupe est **au-dessus** (à droite du zéro, vert) ou **en dessous** (à gauche, orange ou "
              "rouge) de la note minimum exigée pour ce groupe. Zéro = pile au minimum."]
    sous = a[a["note"] < a["note_min"]].sort_values("ecart_objectif")
    if sous.empty:
        lignes.append("**Ici :** tous les groupes atteignent leur minimum.")
    else:
        lignes.append("**Ici :** " + " ; ".join(
            f"« {MODALITES.get(r.modalite, r.modalite)} » est sous son minimum de {pt(-r.ecart_objectif)[1:]} "
            f"({p(r.note)} pour {p(r.note_min)})" for r in sous.itertuples()) + ".")
    return "\n\n".join(lignes)


AIDE_COMPTEURS = {
    "note": "Moyenne des notes des données critiques, chacune pesant selon son importance dans le SCR. "
            "Le calcul détaillé est dans Documentation → « D'où sortent les chiffres ».",
    "objectif": "Note minimum exigée pour l'ensemble. Plus les données pèsent lourd dans le SCR, plus "
                "l'objectif est haut.",
    "ecart": "Note globale moins objectif. Positif : objectif atteint.",
    "hors_tol": "Nombre de données critiques dont la note est sous leur propre minimum. "
                "La note globale peut passer alors que certaines données échouent.",
    "a_jour": "Part des contrôles refaits à temps. Un contrôle en retard reprend son ancien résultat, "
              "avec une pénalité.",
    "conformes": "Part des contrôles dont le résultat atteint leur seuil.",
    "qrt": "Part des vérifications « état réglementaire = outil interne » réussies. Jugées en oui / non, hors note.",
    "zones": "Part des étapes à risque du trajet des données qui ont au moins un contrôle.",
    "ouvertes": "Problèmes détectés et pas encore réglés.",
    "haute": "Parmi les anomalies ouvertes, les plus graves.",
    "retard": "Anomalies dont la date limite de correction est dépassée.",
    "cloturees": "Anomalies réglées depuis la première campagne du registre : contrôle refait et revenu au vert "
                 "(la date de clôture figure dans le registre).",
}

LEGENDE_DONNEES = (
    "**Lire le tableau.** *Sensibilité SCR* : de combien le SCR bouge quand la donnée bouge (plus c'est haut, "
    "plus la donnée compte). *Note QDD* : la moyenne des résultats de ses contrôles, après pénalité de retard. "
    "*Note min* : le minimum exigé, d'autant plus haut que la sensibilité est forte. *Statut* : vert si la note "
    "atteint le minimum, orange si elle est à moins de 2 points en dessous, rouge au-delà. *E/X/P* : critères "
    "couverts (Exhaustivité, eXactitude, Pertinence). Les données non critiques n'ont ni minimum ni statut.")

LEGENDE_CONTROLES = (
    "**Lire le tableau.** *resultat_brut* : ce que le contrôle a mesuré (100 % = aucune erreur). *anteriorite* : "
    "nombre de périodes de retard (0 = refait à temps). *resultat* : le résultat brut après pénalité de retard. "
    "*seuil* : le minimum attendu. *detail* : ce que le contrôle a compté (lignes en erreur, montants, ou totaux "
    "comparés). Les contrôles QRT (Q01 à Q04) ont un seuil fixe de 99,90 %.")


# ====================================================================== affichage
def afficher_d_ou_sortent(c: dict) -> None:
    import streamlit as st

    par = c["params"]
    st.markdown(
        "Pas besoin de lire le mémoire : tout le calcul tient en **5 étapes**, montrées ici sur les vrais "
        "chiffres de la campagne. Chaque nombre de cette page est recalculé devant vous à partir des précédents.")
    retard = (f"On retire **{p(par.coef_degradation, 0)} par période de retard**" if par.methode_degradation == "simple"
              else f"On garde **{p(1 - par.coef_degradation, 0)} du résultat par période de retard** (pénalité composée)")
    st.markdown(
        "| Étape | Question | Réponse en une ligne |\n|---|---|---|\n"
        "| 1 | Que mesure un contrôle ? | La part des données **sans erreur** (100 % = parfait) |\n"
        f"| 2 | Et si le contrôle est ancien ? | {retard} |\n"
        "| 3 | Quelle note pour une donnée ? | La **moyenne** des résultats de ses contrôles |\n"
        "| 4 | Quelle note exiger ? | D'autant plus haute que la donnée **pèse lourd** dans le SCR |\n"
        "| 5 | Quelle note globale ? | La moyenne des notes des données, **pondérée par leur poids** |\n")

    dd = c["donnees"]
    crit = dd[dd["critique"] & (dd["nb_controles"] > 0)].sort_values("sensibilite", ascending=False)
    libelles = dict(zip(crit["donnee_id"], crit["libelle"]))
    defaut = "date_survenance" if "date_survenance" in libelles else crit["donnee_id"].iloc[0]
    choix = st.selectbox("Donnée à décortiquer", list(libelles), index=list(libelles).index(defaut),
                         format_func=libelles.get)
    x = decortiquer_donnee(c, choix)
    cs = x["controles"]

    st.subheader("Étape 1 — Ce que chaque contrôle a trouvé")
    if cs["controle"].duplicated().any():
        st.caption("Un même contrôle peut apparaître plusieurs fois : il est mesuré séparément pour chaque segment "
                   "(ou classe d'actifs), et chaque mesure compte dans la note de la donnée.")
    for r in cs.itertuples():
        with st.container(border=True):
            maille = r.controle_id.split("|")[1] if "|" in r.controle_id else "TOUS"
            suffixe = "" if maille == "TOUS" else f" — {MODALITES.get(maille, maille)}"
            st.markdown(f"**{r.controle_id.split('|')[0]} · {r.libelle}{suffixe}**")
            st.markdown(texte_controle(r, c["date"]))

    st.subheader("Étape 2 — La pénalité de retard")
    lignes = []
    for r in cs.itertuples():
        code = r.controle_id.split("|")[0]
        if r.anteriorite > 0:
            per = PERIODE.get(r.frequence, "période")
            regle = (f"1 − {p(par.coef_degradation, 0)} × {int(r.anteriorite)}" if par.methode_degradation == "simple"
                     else f"(1 − {p(par.coef_degradation, 0)}) puissance {int(r.anteriorite)}")
            lignes.append(f"- **{code}** se fait chaque {per} et a **{int(r.anteriorite)} {per}(s) de retard** : "
                          f"on garde {regle} = {p(r.facteur, 0)} de son résultat. {p(r.resultat_brut)} × "
                          f"{p(r.facteur, 0)} = **{p(r.recalcul)}**.")
        else:
            lignes.append(f"- **{code}** a été refait à temps : pas de pénalité, **{p(r.recalcul)}**.")
    st.markdown("\n".join(lignes))
    st.caption("Pourquoi ? Un contrôle ancien ne garantit plus que la donnée est juste aujourd'hui.")

    st.subheader("Étape 3 — La note de la donnée")
    if (cs["poids"] == cs["poids"].iloc[0]).all():
        calc = " + ".join(p(v) for v in cs["recalcul"])
        st.markdown(f"Moyenne des résultats : ({calc}) ÷ {len(cs)} = **{p(x['note'])}**.")
    else:
        calc = " + ".join(f"{p(v)} × {w:g}" for v, w in zip(cs["recalcul"], cs["poids"]))
        st.markdown(f"Moyenne **pondérée** (certains contrôles comptent plus que d'autres, selon leur poids) : "
                    f"({calc}) ÷ {cs['poids'].sum():g} = **{p(x['note'])}**.")

    st.subheader("Étape 4 — La note minimum exigée")
    s = x["sensibilite"]
    if x["a_dire_expert"]:
        poids = (f"- **Le poids de la donnée.** On ne peut pas « augmenter de {p(CHOC, 0)} » cette donnée pour voir "
                 f"le SCR bouger (une date ne se multiplie pas). Elle est jugée critique **à dire d'expert**, et "
                 f"reçoit le poids moyen des {x['nb_mesurees']} données dont on a pu mesurer la sensibilité : "
                 f"**{p(s, 2)}**.\n")
    else:
        poids = (f"- **Le poids de la donnée (sa sensibilité).** On augmente artificiellement la donnée de "
                 f"{p(CHOC, 0)} et on regarde de combien le SCR bouge. Ici, le SCR ({m(x['scr'])}) bouge de "
                 f"{p(s * CHOC)} (≈ {m(x['scr'] * s * CHOC)}). Sensibilité = {p(s * CHOC)} ÷ {p(CHOC, 0)} = "
                 f"**{p(s, 2)}**.\n")
    st.markdown(
        poids +
        f"- **L'erreur tolérée.** On accepte qu'une donnée fausse le SCR d'au plus **{p(par.delta_scr_max)}**. "
        f"Une sensibilité de {p(s, 2)} veut dire : si la donnée est fausse de 10 %, le SCR est faux de "
        f"{p(s, 2)} × 10 % = {p(s * 0.10, 3)}. Pour ne pas dépasser {p(par.delta_scr_max)} d'erreur sur le SCR, "
        f"la donnée peut donc être fausse d'au plus {p(par.delta_scr_max)} ÷ {p(s, 2)} = "
        f"**{p(par.delta_scr_max / s)}**.\n"
        f"- **Note minimum** = 100 % − {p(par.delta_scr_max / s)} = **{p(x['note_min'])}**.")
    st.caption("Conséquence : une donnée qui pèse lourd doit être presque parfaite ; une donnée qui pèse peu "
               "peut se permettre plus d'erreurs.")

    st.subheader("Étape 5 — Le verdict pour cette donnée")
    verdict = {"vert": ":green[:material/check_circle:] **Vert** : la note atteint le minimum.",
               "orange": f":orange[:material/error:] **Orange** : la note est sous le minimum, mais de moins de {par.marge_alerte * 100:g} points.",
               "rouge": f":red[:material/cancel:] **Rouge** : la note est sous le minimum de plus de {par.marge_alerte * 100:g} points."}
    st.markdown(f"{p(x['note'])} contre {p(x['note_min'])} exigés → {verdict[x['statut']]}")

    st.header("Et la note globale ?")
    gl = decortiquer_globale(c)
    t = gl["table"]
    st.markdown(
        "On fait la moyenne des notes des données critiques, mais chaque donnée **pèse selon sa sensibilité** : "
        "une donnée qui compte beaucoup dans le SCR compte aussi beaucoup dans la note.")
    st.dataframe(pd.DataFrame({
        "Donnée": t["libelle"], "Note": t["note"].map(p), "Sensibilité": t["sensibilite"].map(lambda v: p(v, 1)),
        "Part dans la note": t["part"].map(lambda v: p(v, 1)), "Apport = note × part": t["apport"].map(p)}),
        hide_index=True, width="stretch")
    lourd = t.iloc[0]
    st.markdown(
        f"Somme des apports = **{p(gl['note'])}** : c'est la note globale. À elle seule, "
        f"« {lourd['libelle']} » représente **{p(lourd['part'], 0)}** de la note : son résultat décide presque "
        f"de tout.\n\n"
        f"**L'objectif** se calcule de la même façon avec les notes minimum : **{p(gl['objectif'])}** "
        f"(c'est aussi 100 % − {p(par.delta_scr_max)} ÷ sensibilité moyenne de {p(gl['s_moy'])}).")
