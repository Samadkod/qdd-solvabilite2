"""Habillage assurance, sans modification du moteur original."""
from pathlib import Path
from html import escape
import streamlit as st
from style_app import CSS
from langue import t

def appliquer_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    habillage = Path(__file__).parent / "assets" / "design.css"
    st.markdown(f"<style>{habillage.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    entreprise = Path(__file__).parent / "assets" / "design_entreprise.css"
    st.markdown(f"<style>{entreprise.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    if theme_sombre():
        sombre = Path(__file__).parent / "assets" / "design_sombre.css"
        st.markdown(f"<style>{sombre.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def theme_sombre() -> bool:
    """Thème choisi par l'utilisateur (menu ⋮ > Settings) ; clair si l'information n'est pas disponible."""
    try:
        return st.context.theme.type == "dark"
    except Exception:  # noqa: BLE001
        return False


def couleur_texte() -> str:
    """Couleur des étiquettes de graphiques, lisible sur le fond du thème."""
    return "#E3EAF0" if theme_sombre() else "#15202A"

def _contexte(campagne: str, date) -> str:
    return (f'<div class="qdd-contexte"><div class="qdd-contexte-ligne">{t("Campagne")} <b>{escape(str(campagne))}</b>'
            f' · {t("Arrêté du")} <b>{date:%d/%m/%Y}</b></div><div class="qdd-badges">'
            f'<span class="qdd-badge">{t("Environnement de démonstration · données fictives")}</span>'
            f'<span class="qdd-badge">{t("Assurance dommages · BTP")}</span></div></div>')


def bandeau(campagne: str, date) -> None:
    """En-tête de la Synthèse : titre, accroche et contexte de campagne, sur une bande compacte."""
    st.markdown(
        f'<div class="qdd-hero"><div class="qdd-surtitre">{t("SOLVABILITÉ II / PILOTAGE DE LA QUALITÉ DES DONNÉES")}'
        f'</div><h1>{t("Pilotage de la qualité des données")}</h1>'
        f'<p>{t("Identifier les écarts. Prioriser la revue. Documenter les contrôles.")}</p>'
        f'{_contexte(campagne, date)}</div>',
        unsafe_allow_html=True,
    )


def entete_page(rubrique: str, titre: str, description: str, contexte: str, campagne: str | None = None,
                date=None) -> None:
    droite = _contexte(campagne, date) if campagne is not None and date is not None else ""
    surtitre = escape(rubrique) if droite else f"{escape(rubrique)} · {escape(contexte)}"
    st.markdown(
        f'<div class="qdd-entete"><div class="qdd-surtitre">{surtitre}</div><h1>{escape(titre)}</h1>'
        f'<p>{escape(description)}</p>{droite}</div>',
        unsafe_allow_html=True,
    )



# Script installé une fois dans la page, qui lit à chaque passage les repères mis à jour par le serveur
# (div .qdd-repere : thème connu du serveur, numéro de la dernière demande de fermeture du menu).
_SCRIPT_INTERFACE = """<script>
(function () {
  if (window.__qddVeille) { return; }
  window.__qddVeille = true;
  const doc = window.document;
  let derniereFermeture = null, derniereRelance = 0;
  function themeAffiche() {
    const app = doc.querySelector(".stApp");
    if (!app) { return null; }
    const m = getComputedStyle(app).backgroundColor.match(/\\d+(\\.\\d+)?/g);
    if (!m) { return null; }
    const [r, g, b] = m.map(Number);
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128 ? "dark" : "light";
  }
  setInterval(function () {
    const repere = doc.querySelector(".qdd-repere");
    if (!repere) { return; }
    // 1. Sur téléphone, le menu latéral se referme après un choix de page (comme une navigation native).
    const n = repere.dataset.fermer;
    if (derniereFermeture === null) { derniereFermeture = n; }
    if (n !== derniereFermeture) {
      derniereFermeture = n;
      if (window.matchMedia("(max-width: 767.98px)").matches) {
        const b = doc.querySelector('[data-testid="stSidebarCollapseButton"] button');
        if (b) { b.click(); }
      }
    }
    // 2. Changement de thème (menu ⋮ > Settings) : Streamlit ne relance pas le script, l'habillage sombre ou
    //    clair n'arrivait qu'au clic suivant. Thème affiché différent de celui du serveur : on relance une fois.
    const affiche = themeAffiche();
    if (affiche && affiche !== repere.dataset.theme && Date.now() - derniereRelance > 2500) {
      const relance = doc.querySelector(".st-key-qdd_relais button");
      if (relance) { derniereRelance = Date.now(); relance.click(); }
    }
  }, 300);
})();
</script>"""


def comportement_interface(fermer_menu: bool) -> None:
    """Menu refermé après un choix de page sur téléphone ; habillage appliqué dès le changement de thème.
    À appeler dans la barre latérale ; le relais est invisible (design_entreprise.css)."""
    if fermer_menu:
        st.session_state["_qdd_fermetures"] = st.session_state.get("_qdd_fermetures", 0) + 1
    theme = "dark" if theme_sombre() else "light"
    with st.container(key="qdd_relais"):
        st.markdown(f'<div class="qdd-repere" data-theme="{theme}" '
                    f'data-fermer="{st.session_state.get("_qdd_fermetures", 0)}"></div>', unsafe_allow_html=True)
        st.button("relance", key="qdd_relance_theme")
        st.html(_SCRIPT_INTERFACE, unsafe_allow_javascript=True)
