import streamlit as st

from frontend.auth import es_admin, iniciar_sesion_admin, verificar

P = st.session_state["_P"]
if es_admin():
    st.switch_page(P["dash"])

_, centro, _ = st.columns([1.2, 1, 1.2])
aviso = st.session_state.pop("aviso_login", None)
with centro, st.container(key="panel_login"):
    if aviso:
        st.success(aviso)
    st.markdown("<div style='text-align:center'><div class='k-logo' style='font-size:2.2rem'>kanasta</div>"
                "<div class='k-muted' style='margin:6px 0 14px 0'>Panel de administración</div></div>",
                unsafe_allow_html=True)
    with st.form("login", border=False):
        usuario = st.text_input("Usuario", placeholder="admin")
        clave = st.text_input("Contraseña", type="password")
        entrar = st.form_submit_button("Ingresar", type="primary", width="stretch",
                                       icon=":material/lock_open:")
    if entrar:
        if verificar(usuario, clave):
            iniciar_sesion_admin()
            st.switch_page(P["dash"])
        else:
            st.error("Usuario o contraseña incorrectos.")
    st.page_link(P["inicio"], label="Volver a la tienda", icon=":material/arrow_back:")
