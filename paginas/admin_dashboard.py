import altair as alt
import streamlit as st

from frontend import analisis as an
from frontend import tienda as t
from frontend.datos import arbol_categorias, pedidos_recientes
from frontend.estilo import kpi, seccion
from frontend.graficos import AZUL, MES_AXIS, mostrar, nota, soles

P = st.session_state["_P"]
st.markdown("## Dashboard")
st.caption("Histórico: ene-2024 a sep-2026 · Operación: pedidos creados en la app en tiempo real")

k = an.kpis()
c = st.columns(5, gap="small")
kpi(c[0], "Ventas históricas", soles(k["ventas"]), f"{k['vendedores']} tiendas con ventas")
kpi(c[1], "Pedidos válidos", f"{k['pedidos']:,}", "pagados, enviados o entregados")
kpi(c[2], "Clientes", f"{k['clientes']:,}", "con al menos una compra")
kpi(c[3], "Ticket promedio", soles(k["ticket"]), "por pedido")
kpi(c[4], "Entregas a tiempo", f"{k['a_tiempo']:.0%}", "según fecha prometida")

seccion("⚡ Operación en vivo")
estados = t.conteo_estados()
hoy = t.ventas_hoy()
c = st.columns(4, gap="small")
kpi(c[0], "Por pagar", f"{estados.get('pendiente', 0):,}", "esperando pago")
kpi(c[1], "Por despachar", f"{estados.get('pagado', 0):,}", "pagados, sin enviar")
kpi(c[2], "En camino", f"{estados.get('enviado', 0):,}", "con courier")
kpi(c[3], "Ventas en la app", soles(hoy["ventas"]), f"{hoy['pedidos']} pedidos confirmados desde la app")
st.page_link(P["gestion"], label="Ir a gestionar pedidos", icon=":material/local_shipping:")

izq, der = st.columns([3, 2], gap="large")
with izq:
    m = an.ventas_mensuales()
    linea = (alt.Chart(m, title="Ventas mensuales")
             .mark_area(line={"color": AZUL, "strokeWidth": 2}, color=AZUL, opacity=0.12)
             .encode(x=alt.X("fecha:T", title=None, axis=alt.Axis(labelExpr=MES_AXIS, labelAngle=0, tickCount=6)),
                     y=alt.Y("ventas:Q", title="Soles", axis=alt.Axis(format="~s")),
                     tooltip=[alt.Tooltip("fecha:T", title="Mes", format="%m/%Y"),
                              alt.Tooltip("ventas:Q", title="Ventas (S/)", format=",.0f"),
                              alt.Tooltip("pedidos:Q", title="Pedidos", format=",")]))
    mostrar(linea, 300)
with der:
    cat = arbol_categorias()
    raiz = cat[cat["nivel"] == 1]
    barras = (alt.Chart(raiz, title="Ventas por categoría")
              .mark_bar(color=AZUL, cornerRadiusEnd=3, height=14)
              .encode(y=alt.Y("nombre:N", sort="-x", title=None),
                      x=alt.X("ventas:Q", title="Soles", axis=alt.Axis(format="~s")),
                      tooltip=[alt.Tooltip("nombre:N", title="Categoría"),
                               alt.Tooltip("ventas:Q", title="Ventas (S/)", format=",.0f")]))
    mostrar(barras, 300)
nota("Las ventas crecen mes a mes con campañas en <b>mayo, julio y noviembre</b>. 14 de 676 tiendas hacen "
     "el 80 % de las ventas; Juguetes y Bebés y Electrodomésticos concentran casi dos tercios.")

seccion("🧾 Últimos pedidos")
rec = pedidos_recientes(10)
st.dataframe(rec, hide_index=True, column_config={
    "id_pedido": st.column_config.NumberColumn("Pedido", format="%d"),
    "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
    "cliente": "Cliente", "departamento": "Destino", "estado": "Estado",
    "total": st.column_config.NumberColumn("Total", format="S/ %,.2f")})
