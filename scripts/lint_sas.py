"""Vérification statique du code SAS (faute de SAS dans l'environnement de développement).

Contrôles :
  1. %macro / %mend équilibrés ; pas de macro imbriquée ;
  2. %do / %end équilibrés dans chaque macro ;
  3. %if / %do / %let... : pas de %if en code ouvert (non supporté avant SAS 9.4M5) ;
  4. guillemets et parenthèses équilibrés (commentaires retirés) ;
  5. toute macro appelée (%nom) est définie dans le projet ou est une fonction macro SAS ;
  6. tout bloc DATA / PROC se termine par RUN; ou QUIT; avant le bloc suivant ;
  7. tout %include pointe vers un fichier existant.
Usage : python scripts/lint_sas.py [dossier_sas]  -> code retour 1 si erreur.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

FONCTIONS_MACRO = {
    "macro", "mend", "let", "local", "global", "if", "then", "else", "do", "to", "end", "put", "include",
    "eval", "sysevalf", "sysfunc", "str", "nrstr", "quote", "bquote", "superq", "upcase", "lowcase", "scan",
    "substr", "index", "length", "return", "abort", "sysget", "symexist", "unquote", "qscan", "cmpres",
}


def sans_commentaires(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group()), t, flags=re.S)
    # commentaires « * ... ; » en début d'instruction
    t = re.sub(r"(^|;)\s*\*[^;]*;", lambda m: m.group(1) + " ", t, flags=re.M)
    return t


def sans_chaines(t: str) -> str:
    return re.sub(r"'[^']*'|\"[^\"]*\"", lambda m: m.group()[0] + "x" * (len(m.group()) - 2) + m.group()[0], t)


def verifier(dossier: Path) -> list[str]:
    erreurs = []
    fichiers = sorted(dossier.glob("*.sas"))
    definies = set()
    for f in fichiers:
        definies |= {m.lower() for m in re.findall(r"%macro\s+(\w+)", sans_commentaires(f.read_text("utf-8")), re.I)}
    for f in fichiers:
        brut = f.read_text("utf-8")
        t = sans_commentaires(brut)
        tn = sans_chaines(t)
        nom = f.name
        # 4. guillemets / parenthèses
        if t.count('"') % 2:
            erreurs.append(f"{nom}: nombre impair de guillemets doubles")
        sq = re.sub(r'"[^"]*"', "", t)
        if sq.count("'") % 2:
            erreurs.append(f"{nom}: nombre impair d'apostrophes hors chaînes doubles")
        if tn.count("(") != tn.count(")"):
            erreurs.append(f"{nom}: parenthèses déséquilibrées ({tn.count('(')} / {tn.count(')')})")
        # 1-3. structure macro
        prof_macro, pile_do = 0, []
        for n, ligne in enumerate(tn.splitlines(), 1):
            for tok in re.findall(r"%(macro|mend|do|end|if)\b", ligne, re.I):
                tok = tok.lower()
                if tok == "macro":
                    if prof_macro:
                        erreurs.append(f"{nom}:{n}: %macro imbriquée")
                    prof_macro += 1
                elif tok == "mend":
                    if pile_do:
                        erreurs.append(f"{nom}:{n}: %mend avec {len(pile_do)} %do non fermé(s)")
                        pile_do = []
                    prof_macro -= 1
                elif tok == "do":
                    pile_do.append(n)
                elif tok == "end":
                    if not pile_do:
                        erreurs.append(f"{nom}:{n}: %end sans %do")
                    else:
                        pile_do.pop()
                elif tok == "if" and prof_macro == 0:
                    erreurs.append(f"{nom}:{n}: %if en code ouvert")
        if prof_macro != 0:
            erreurs.append(f"{nom}: %macro/%mend déséquilibrés")
        # 5. macros appelées
        for m in re.finditer(r"%(\w+)", tn):
            nm = m.group(1).lower()
            if nm not in FONCTIONS_MACRO and nm not in definies:
                erreurs.append(f"{nom}: appel à %{m.group(1)} non défini")
        # 6. blocs DATA / PROC
        etapes = re.finditer(r"(?:^|;)\s*(data|proc)\b(?!\s*=)", tn, re.I | re.M)
        positions = [(m.start(1), m.group(1).lower()) for m in etapes]
        fins = [m.start() for m in re.finditer(r"\b(run|quit)\s*;", tn, re.I)]
        for i, (pos, kind) in enumerate(positions):
            suivant = positions[i + 1][0] if i + 1 < len(positions) else len(tn)
            if not any(pos < e < suivant for e in fins):
                ln = tn[:pos].count("\n") + 1
                erreurs.append(f"{nom}:{ln}: bloc {kind.upper()} sans RUN/QUIT avant le bloc suivant")
        # 7. %include
        for inc in re.findall(r'%include\s+"&RACINE\./([^"]+)"', t):
            if not (dossier.parent / inc).exists():
                erreurs.append(f"{nom}: %include introuvable {inc}")
    return erreurs


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "sas"
    e = verifier(d)
    print("\n".join(e) if e else f"Lint SAS OK ({len(list(d.glob('*.sas')))} fichiers)")
    sys.exit(1 if e else 0)
