"""Kanasta — marketplace multivendedor (frontend del Proyecto P4).

Ejecutar desde esta carpeta:
    python -m streamlit run app.py

Se entra como CLIENTE. El panel de ADMINISTRADOR pide usuario y contraseña
(por defecto: admin / kanasta2026, ver frontend/auth.py).
"""
import streamlit as st

from frontend import tienda as t
from frontend.auth import cerrar_sesion_admin, es_admin
from frontend.componentes import unidades_carrito
from frontend.datos import probar_conexion
from frontend.estilo import aplicar_estilo
from frontend.profe import montar_profe

st.set_page_config(page_title="Kanasta", page_icon="🧺", layout="wide", initial_sidebar_state="collapsed")
aplicar_estilo()

error = probar_conexion()
if error:
    st.markdown("<div class='k-logo'>kanasta</div>", unsafe_allow_html=True)
    st.error("No se pudo conectar a MySQL.")
    st.markdown(f"""
**Revisa:**
1. Que el servicio de MySQL esté encendido (Windows → Servicios → *MySQL84*).
2. Que la contraseña en `config.py` sea la misma que usas en Workbench.
3. Que hayas corrido `01_esquema.sql`, el script de carga y `03_consultas.sql`.

Detalle: `{error}`""")
    st.stop()

t.asegurar_tablas()
montar_profe()                      # mascota animada (vive en el navegador)
st.session_state.setdefault("rol", "cliente")
st.session_state.setdefault("id_cliente", 2474)

P = {
    "inicio": st.Page("paginas/cliente_inicio.py", title="Inicio", default=True),
    "explorar": st.Page("paginas/cliente_explorar.py", title="Explorar"),
    "carrito": st.Page("paginas/cliente_carrito.py", title="Carrito"),
    "pedidos": st.Page("paginas/cliente_pedidos.py", title="Mis pedidos"),
    "cuenta": st.Page("paginas/cliente_cuenta.py", title="Mi cuenta"),
    "login": st.Page("paginas/admin_login.py", title="Acceso administrador"),
    "dash": st.Page("paginas/admin_dashboard.py", title="Dashboard"),
    "gestion": st.Page("paginas/admin_pedidos.py", title="Pedidos"),
    "analisis": st.Page("paginas/admin_analisis.py", title="Análisis"),
    "catalogo": st.Page("paginas/admin_catalogo.py", title="Catálogo y stock"),
}
st.session_state["_P"] = P
ADMIN = ("dash", "gestion", "analisis", "catalogo")
nav = st.navigation(list(P.values()), position="hidden")   # todas registradas; las de admin se protegen
en_admin = nav.url_path in {P[k].url_path for k in ADMIN}
if en_admin and not es_admin():                            # sin sesión de admin → al login
    st.switch_page(P["login"])


# ------------------------------------------------------------------ encabezado cliente
def ir_a_buscar():
    q = st.session_state.get("q_hdr", "").strip()
    if q and q != st.session_state.get("filtro_q"):      # solo si de verdad se buscó algo nuevo
        st.session_state["filtro_q"] = q
        st.session_state["_ir_explorar"] = True


def encabezado_cliente():
    if st.session_state.pop("_limpiar_q", False):
        st.session_state["q_hdr"] = ""
    cli = t.cliente(st.session_state["id_cliente"])
    nombre = cli["nombre"].split()[0]
    with st.container(key="hdr"):
        c = st.columns([1.25, 1.55, 3.3, 1.75, 1.7, 1.3], vertical_alignment="center", gap="small")
        with c[0], st.container(key="hdr_logo"):
            st.page_link(P["inicio"], label="kanasta")
        c[1].markdown(f"<div class='k-ubic'>📍 Entregar en<br><b>{cli['distrito']}, {cli['departamento']}</b></div>",
                      unsafe_allow_html=True)
        c[2].text_input("Buscar", key="q_hdr", placeholder="Buscar productos, marcas o tiendas",
                        label_visibility="collapsed", on_change=ir_a_buscar, icon=":material/search:")
        c[3].page_link(P["pedidos"], label="Mis pedidos", icon=":material/receipt_long:")
        with c[4], st.container(key="hdr_carrito"):
            n = unidades_carrito()
            st.page_link(P["carrito"], label=f"Carrito ({n})" if n else "Carrito",
                         icon=":material/shopping_cart:")
        with c[5].popover(nombre, icon=":material/account_circle:", width="stretch"):
            st.markdown(f"**{cli['nombre']}**  \n{cli['email']}")
            st.page_link(P["cuenta"], label="Mi cuenta y favoritos", icon=":material/person:")
            st.page_link(P["explorar"], label="Explorar la tienda", icon=":material/storefront:")
            st.page_link(P["pedidos"], label="Mis pedidos", icon=":material/receipt_long:")
            st.divider()
            st.page_link(P["dash"] if es_admin() else P["login"], label="Panel de administrador",
                         icon=":material/admin_panel_settings:")
    if es_admin():   # el admin está mirando la tienda: la sesión sigue abierta
        a, b, x = st.columns([5, 1.2, 1.3], vertical_alignment="center")
        a.markdown("<span class='k-chip' style='background:#1F1F1F;color:#fff'>🔐 Sesión de administrador "
                   "abierta</span>", unsafe_allow_html=True)
        b.page_link(P["dash"], label="Volver al panel", icon=":material/monitoring:")
        if x.button("Cerrar sesión", icon=":material/logout:", key="logout_tienda"):
            cerrar_sesion_admin()
            st.session_state["aviso_login"] = "Cerraste sesión. Para volver al panel ingresa de nuevo."
            st.switch_page(P["login"])
    if st.session_state.pop("_ir_explorar", False) and nav.url_path != "cliente_explorar":
        st.switch_page(P["explorar"])


def encabezado_admin():
    with st.container(key="hdr_admin"):
        c = st.columns([1.55, 1.45, 1.2, 1.25, 1.85, 1.45, 1.05], vertical_alignment="center")
        c[0].markdown("<span class='k-logo' style='font-size:1.45rem'>kanasta</span>"
                      "<span style='color:#aaa;font-size:0.85rem'>&nbsp; admin</span>", unsafe_allow_html=True)
        c[1].page_link(P["dash"], label="Dashboard", icon=":material/monitoring:")
        c[2].page_link(P["gestion"], label="Pedidos", icon=":material/local_shipping:")
        c[3].page_link(P["analisis"], label="Análisis", icon=":material/insights:")
        c[4].page_link(P["catalogo"], label="Catálogo y stock", icon=":material/inventory_2:")
        c[5].page_link(P["inicio"], label="Ver tienda", icon=":material/storefront:")
        if c[6].button("Salir", icon=":material/logout:", width="stretch"):
            cerrar_sesion_admin()
            st.session_state["aviso_login"] = "Cerraste sesión. Para volver al panel ingresa de nuevo."
            st.switch_page(P["login"])


if en_admin:
    encabezado_admin()
else:
    encabezado_cliente()
nav.run()
