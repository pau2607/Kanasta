"""El profe en pixel art: monta la mascota animada en la página.

Los sprites y el motor (static/profe/profe.js) se sirven como archivos estáticos.
El script se carga una sola vez por pestaña: después vive en el navegador y sigue
caminando aunque Streamlit vuelva a dibujar la página.
"""
import streamlit as st

VERSION = "8"

_BOOT = f"""<script>
(function () {{
  if (window.KanastaProfe || document.getElementById("kp-js")) return;
  var s = document.createElement("script");
  s.id = "kp-js";
  s.src = "/app/static/profe/profe.js?v={VERSION}";
  document.head.appendChild(s);
}})();
</script>"""


def montar_profe():
    st.html(_BOOT, unsafe_allow_javascript=True)
