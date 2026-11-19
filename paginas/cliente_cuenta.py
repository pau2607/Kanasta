import streamlit as st

from frontend import analisis as an
from frontend import tienda as t
from frontend.componentes import grilla
from frontend.estilo import color_avatar, esc, kpi, seccion, soles

ss = st.session_state
P = ss["_P"]
id_cliente = ss["id_cliente"]
cli = t.cliente(id_cliente)
mios = t.pedidos_cliente(id_cliente)
validos = mios[mios["estado"].isin(["pagado", "enviado", "entregado"])]

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
iniciales = "".join(w[0] for w in cli["nombre"].split()[:2]).upper()
a, b = st.columns([0.7, 6], vertical_alignment="center")
a.markdown(f"<div class='k-avatar' style='width:72px;height:72px;font-size:1.6rem;"
           f"background:{color_avatar(cli['nombre'])}'>{iniciales}</div>", unsafe_allow_html=True)
b.markdown(f"## {esc(cli['nombre'])}\n<span class='k-meta'>{esc(cli['email'])} · 📍 {cli['distrito']}, "
           f"{cli['departamento']} · cliente desde {MESES[cli['fecha_registro'].month - 1]} "
           f"{cli['fecha_registro'].year}</span>", unsafe_allow_html=True)

# segmento RFM en vivo (incluye las compras hechas en la app)
nivel = an.nivel_cliente(id_cliente)
NIVEL = {"Campeones": "🏆 Cliente Campeón", "Leales": "💎 Cliente Leal", "Potenciales leales": "🌱 Potencial leal",
         "Nuevos": "👋 Cliente nuevo", "Prometedores": "✨ Prometedor", "Necesitan atención": "👀 Te extrañamos",
         "A punto de dormirse": "😴 Hace tiempo no vienes", "En riesgo": "⚠️ Te extrañamos",
         "No se pueden perder": "💌 ¡Vuelve!", "Hibernando": "💤 Hace mucho no vienes"}
segmento = nivel["segmento"] if nivel else None

c = st.columns(4, gap="medium")
kpi(c[0], "Pedidos", f"{len(validos)}", f"{len(mios)} en total")
kpi(c[1], "Gastado", soles(validos["total"].sum()), "en compras confirmadas")
kpi(c[2], "Favoritos", f"{len(t.favoritos_de(id_cliente))}", "productos guardados")
kpi(c[3], "Tu nivel", NIVEL.get(segmento, "👋 Cliente nuevo"),
    f"segmento RFM: {segmento}" if segmento else "aún sin compras confirmadas")

if nivel:
    with st.expander("¿Cómo se calcula tu nivel?"):
        hace = "hoy (compra en la app)" if nivel["R"] == 0 else f"hace {nivel['R']} días"
        st.markdown(
            f"Tu nivel sale de la **segmentación RFM**: comparamos tus compras con las de los 24 286 clientes "
            f"y te damos un puntaje de 1 a 5 en cada dimensión.\n\n"
            f"| | Tu dato | Puntaje |\n|---|---|---|\n"
            f"| **R**ecencia · última compra | {hace} | {'★' * nivel['R_s']}{'☆' * (5 - nivel['R_s'])} |\n"
            f"| **F**recuencia · pedidos | {nivel['F']} | {'★' * nivel['F_s']}{'☆' * (5 - nivel['F_s'])} |\n"
            f"| **M**onto · gastado | {soles(nivel['M'])} | {'★' * nivel['M_s']}{'☆' * (5 - nivel['M_s'])} |\n\n"
            "Se actualiza cuando un pedido queda **pagado** (los pedidos por pagar o cancelados no cuentan).")

seccion("❤️ Tus favoritos")
fav = t.favoritos_de(id_cliente)
cat = t.catalogo()
if fav:
    grilla(cat[cat["id_producto"].isin(fav)].sort_values("vendidos", ascending=False).head(8), "fav")
else:
    st.caption("Todavía no guardas favoritos. Toca 🤍 en el detalle de un producto.")

seccion("⚙️ Opciones")
with st.container(key="panel_demo"):
    st.markdown("**Cambiar de cliente (modo demostración)**  \n"
                "<span class='k-meta'>Para probar la tienda como otro de los 45 000 clientes.</span>",
                unsafe_allow_html=True)
    x, y, _ = st.columns([1.2, 1.6, 2.4], vertical_alignment="bottom")
    nuevo = x.number_input("ID de cliente", 1, 45000, id_cliente)
    if y.button("Entrar como este cliente", width="stretch"):
        ss["id_cliente"] = int(nuevo)
        ss["carrito"] = {}
        ss.pop("pedido_sel", None)
        ss.pop("cupon_codigo", None)
        st.rerun()
    st.caption("Sugerencias: 2474 Iván (Lima) · 2290 Camila (Iquitos, cliente frecuente: otros couriers y "
               "envío más caro) · 27625 Joaquín (Cusco)")
st.page_link(P["login"], label="Panel de administrador", icon=":material/admin_panel_settings:")
