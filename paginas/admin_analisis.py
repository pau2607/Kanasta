import altair as alt
import pandas as pd
import streamlit as st

from frontend import analisis as an
from frontend.graficos import (AZUL, AZUL_CLARO, AZULES, NARANJA, PCT, TEXTO_2, mostrar, nota, pct100,
                               soles, tarjeta)

st.markdown("## Análisis con Pandas")
st.caption("Resultados calculados en vivo desde MySQL con pandas (datos hasta el 30/09/2026).")

tabs = st.tabs(["Estacionalidad", "Clientes (RFM)", "Cohortes", "Co-compras", "Entregas",
                "Estrellas y ventas", "Vendedores tardíos"])

# ------------------------------------------------------------------ estacionalidad
with tabs[0]:
    e = an.estacionalidad()
    graf = (alt.Chart(e, title="Pedidos por día de cada mes vs. sus meses vecinos")
            .mark_bar(cornerRadiusEnd=3)
            .encode(x=alt.X("mes:N", sort=list(e["mes"]), title=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("variacion:Q", title=None, axis=alt.Axis(format="%")),
                    color=alt.Color("campaña:N", title=None,
                                    scale=alt.Scale(domain=["Mes de campaña", "Resto"],
                                                    range=[NARANJA, AZUL])),
                    tooltip=[alt.Tooltip("mes:N", title="Mes"),
                             alt.Tooltip("variacion:Q", title="Variación", format="+.1%")]))
    regla = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=TEXTO_2).encode(y="y:Q")
    mostrar(graf + regla, 320)
    nota("Hay picos de demanda en <b>mayo (+6 %), julio (+7 %) y noviembre (+8 %)</b>, y uno menor en "
         "diciembre: Día de la Madre, Fiestas Patrias/Cyber y Black Friday. Octubre es el mes más "
         "flojo (−10 %). Se mide en pedidos por día para que febrero no salga bajo solo por tener menos días.")

# ------------------------------------------------------------------ RFM
with tabs[1]:
    clientes, res = an.rfm()
    largo = res.melt(id_vars="segmento", value_vars=["pct_clientes", "pct_ventas"],
                     var_name="medida", value_name="pct")
    largo["medida"] = largo["medida"].map({"pct_clientes": "% de clientes", "pct_ventas": "% de ventas"})
    graf = (alt.Chart(largo, title="Segmentos RFM: peso en clientes vs. peso en ventas")
            .mark_bar(cornerRadiusEnd=3, height=11)
            .encode(y=alt.Y("segmento:N", sort=list(res["segmento"]), title=None),
                    yOffset=alt.YOffset("medida:N", sort=["% de clientes", "% de ventas"]),
                    x=alt.X("pct:Q", title=None, axis=alt.Axis(format="%")),
                    color=alt.Color("medida:N", title=None,
                                    scale=alt.Scale(domain=["% de clientes", "% de ventas"],
                                                    range=[AZUL_CLARO, AZUL])),
                    tooltip=["segmento:N", "medida:N", alt.Tooltip("pct:Q", format=".1%")]))
    mostrar(graf, 420)
    st.dataframe(pct100(res, "pct_clientes", "pct_ventas"), hide_index=True, column_config={
        "segmento": "Segmento", "clientes": st.column_config.NumberColumn("Clientes", format="%d"),
        "recencia_dias": st.column_config.NumberColumn("Recencia (días)", format="%d"),
        "pedidos_prom": st.column_config.NumberColumn("Pedidos prom.", format="%.1f"),
        "gasto_prom": st.column_config.NumberColumn("Gasto prom.", format="S/ %.0f"),
        "ventas": st.column_config.NumberColumn("Ventas", format="S/ %.0f"),
        "pct_clientes": st.column_config.NumberColumn("% clientes", format=PCT),
        "pct_ventas": st.column_config.NumberColumn("% ventas", format=PCT)})
    nota("<b>Leales y Campeones</b> son el 33 % de los clientes y generan el <b>66 %</b> de las ventas. "
         "Prioridad de reactivación: <b>No se pueden perder</b> (375 clientes, 8 pedidos en promedio, "
         "~200 días sin comprar) y <b>En riesgo</b> (3 173 clientes, 11 % de las ventas).")
    with st.expander("Buscar un cliente"):
        idc = st.number_input("ID de cliente", 1, 45000, 2474, key="rfm_cli")
        fila = clientes[clientes["id_usuario"] == idc]
        if fila.empty:
            st.caption("Ese cliente no tiene compras válidas.")
        else:
            f = fila.iloc[0]
            st.markdown(f"Segmento **{f['segmento']}** · R={f['R_s']} F={f['F_s']} M={f['M_s']} · "
                        f"{f['F']} pedidos · {soles(f['M'], 2)} · última compra hace {f['R']} días")

# ------------------------------------------------------------------ cohortes
with tabs[2]:
    co = an.cohortes()
    graf = (alt.Chart(co, title="Retención por cohorte (% que vuelve a comprar k meses después)")
            .mark_rect(stroke="#fcfcfb", strokeWidth=1)
            .encode(x=alt.X("k:O", title="Meses desde la primera compra", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("cohorte:O", title="Cohorte (mes de 1ª compra)"),
                    color=alt.Color("retencion:Q", title="Retención",
                                    scale=alt.Scale(range=AZULES, domain=[0, 0.3], clamp=True),
                                    legend=alt.Legend(format="%", orient="right")),
                    tooltip=[alt.Tooltip("cohorte:O", title="Cohorte"), alt.Tooltip("k:O", title="Mes"),
                             alt.Tooltip("retencion:Q", title="Retención", format=".1%")]))
    mostrar(graf, 620)
    nota("~20 % de cada cohorte vuelve el mes siguiente y luego se mantiene entre 11 % y 15 % mensual. "
         "El <b>68 %</b> vuelve al menos una vez en su primer año. La retención del primer mes mejoró de "
         "~10 % (cohortes 2024) a ~30 % (cohortes 2026): la columna 1 se oscurece hacia abajo.")

# ------------------------------------------------------------------ co-compras
with tabs[3]:
    p = an.pares()
    top = p.nlargest(15, "juntos")
    st.dataframe(pct100(top, "conf_a_b", "conf_b_a")[["producto_a", "producto_b", "juntos", "conf_a_b",
                                                       "conf_b_a", "lift"]],
                 hide_index=True, column_config={
                     "producto_a": "Producto A", "producto_b": "Producto B",
                     "juntos": st.column_config.NumberColumn("Pedidos juntos", format="%d"),
                     "conf_a_b": st.column_config.NumberColumn("A → B", format=PCT),
                     "conf_b_a": st.column_config.NumberColumn("B → A", format=PCT),
                     "lift": st.column_config.NumberColumn("Lift", format="%.0f")})
    nota("El <b>73 %</b> de los pedidos tiene 2+ productos, y cada producto tiene un complemento claro "
         "de la <b>misma tienda</b> (aparece en ~25 % de sus pedidos, lift ~560). Esto alimenta el "
         "recomendador de la página <i>Nueva compra</i>.")
    st.markdown("**Probar el recomendador**")
    frecuentes = pd.concat([top[["id_producto_a", "producto_a"]].set_axis(["id", "t"], axis=1),
                            top[["id_producto_b", "producto_b"]].set_axis(["id", "t"], axis=1)]
                           ).drop_duplicates("id")
    pid = st.selectbox("Producto", frecuentes["id"].tolist(),
                       format_func=dict(zip(frecuentes["id"], frecuentes["t"])).get)
    st.dataframe(pct100(an.recomendar(pid, 5), "conf"), hide_index=True, column_config={
        "id_socio": "ID", "titulo": "También compraron",
        "juntos": st.column_config.NumberColumn("Pedidos juntos", format="%d"),
        "conf": st.column_config.NumberColumn("Probabilidad", format=PCT),
        "lift": st.column_config.NumberColumn("Lift", format="%.0f")})

# ------------------------------------------------------------------ entregas
with tabs[4]:
    en = an.entregas()
    celdas = en["celdas"]
    orden_dep = en["por_dep"].sort_values("dias")["departamento"].tolist()
    orden_cou = celdas.groupby("courier")["dias"].median().sort_values().index.tolist()
    base = alt.Chart(celdas, title="Días totales hasta la entrega (mediana) por courier y departamento")
    rect = base.mark_rect(stroke="#fcfcfb", strokeWidth=1).encode(
        x=alt.X("departamento:N", sort=orden_dep, title=None, axis=alt.Axis(labelAngle=-50)),
        y=alt.Y("courier:N", sort=orden_cou, title=None),
        color=alt.Color("dias:Q", title="Días", scale=alt.Scale(range=AZULES, domain=[1, 11])),
        tooltip=["courier:N", "departamento:N", alt.Tooltip("dias:Q", title="Días", format=".1f"),
                 alt.Tooltip("envios:Q", title="Envíos", format=",")])
    texto = base.mark_text(fontSize=9).encode(
        x=alt.X("departamento:N", sort=orden_dep), y=alt.Y("courier:N", sort=orden_cou),
        text=alt.Text("dias:Q", format=".1f"),
        color=alt.condition("datum.dias > 6", alt.value("white"), alt.value("#0b0b0b")))
    mostrar(rect + texto, 330)
    st.caption("Celdas vacías: el courier no llega a ese departamento (Chazki y 99minutos solo Lima) "
               "o tiene menos de 20 envíos.")
    i, d = st.columns([2, 3], gap="large")
    with i:
        t = en["tardio_courier"]
        graf = (alt.Chart(t, title="% de entregas tardías por courier")
                .mark_bar(cornerRadiusEnd=3, height=16)
                .encode(y=alt.Y("courier:N", sort="x", title=None),
                        x=alt.X("tardios:Q", title=None, axis=alt.Axis(format="%")),
                        color=alt.condition("datum.tardios > 0.5", alt.value(NARANJA), alt.value(AZUL)),
                        tooltip=["courier:N", alt.Tooltip("tardios:Q", title="Tardías", format=".0%")]))
        mostrar(graf, 280)
    with d:
        pc = en["por_courier"]
        st.dataframe(pct100(pc, "tardios"), hide_index=True, height=320, column_config={
            "courier": "Courier", "zona": "Zona",
            "envios": st.column_config.NumberColumn("Envíos", format="%,d"),
            "dias": st.column_config.NumberColumn("Días", format="%.1f", help="Mediana de días totales"),
            "tardios": st.column_config.NumberColumn("% tarde", format=PCT),
            "costo": st.column_config.NumberColumn("Costo", format="S/ %.2f", help="Costo promedio")})
    nota("El <b>destino</b> pesa más que el courier: Lima ~2.5 días, Amazonía ~9.5. "
         "<b>Chazki</b> (Lima) y <b>Shalom</b> (provincia) son los más puntuales; <b>Serpost</b> es el más "
         "barato pero llega tarde el <b>84 %</b> de las veces.")

# ------------------------------------------------------------------ estrellas
with tabs[5]:
    s = an.estrellas()
    m1, m2 = st.columns(2)
    m1.metric("Correlación estrellas ↔ ventas", f"{s['rho_ventas']:+.3f}", help="Spearman, productos con 5+ reseñas",
              border=True)
    m2.metric("Correlación retraso ↔ estrellas", f"{s['rho_retraso']:+.3f}", help="Spearman, 40 071 reseñas",
              border=True)
    i, d = st.columns(2, gap="large")
    with i:
        graf = (alt.Chart(s["prod"], title="Estrellas vs. ventas por producto")
                .mark_circle(size=28, color=AZUL, opacity=0.35)
                .encode(x=alt.X("estrellas:Q", title="Estrellas promedio", scale=alt.Scale(domain=[1.5, 5])),
                        y=alt.Y("ventas:Q", title="Ventas (S/, escala log)", scale=alt.Scale(type="log"),
                                axis=alt.Axis(format="~s", values=[1e3, 1e4, 1e5, 1e6])),
                        tooltip=[alt.Tooltip("estrellas:Q", format=".2f"),
                                 alt.Tooltip("ventas:Q", format=",.0f"), "n_resenas:Q"]))
        mostrar(graf, 340)
    with d:
        tr = s["tramo"]
        barras = (alt.Chart(tr, title="Estrellas promedio según el retraso de la entrega")
                  .mark_bar(color=AZUL, cornerRadiusEnd=3, width=38)
                  .encode(x=alt.X("tramo:N", sort=list(tr["tramo"]), title=None, axis=alt.Axis(labelAngle=0)),
                          y=alt.Y("mean:Q", title="Estrellas", scale=alt.Scale(domain=[0, 5])),
                          tooltip=[alt.Tooltip("tramo:N", title="Retraso"),
                                   alt.Tooltip("mean:Q", title="Estrellas", format=".2f"),
                                   alt.Tooltip("size:Q", title="Reseñas", format=",")]))
        etiquetas = barras.mark_text(dy=-8, color="#0b0b0b", fontSize=11).encode(
            text=alt.Text("mean:Q", format=".2f"))
        mostrar(barras + etiquetas, 340)
    nota("Las estrellas <b>no</b> se relacionan con las ventas (≈ 0). Dependen de la entrega: "
         "4.30 si llega a tiempo, <b>1.77</b> con 8+ días de retraso. La reputación es sobre todo "
         "reputación logística.")

# ------------------------------------------------------------------ vendedores
with tabs[6]:
    v, tasa = an.vendedores_tardios()
    malos = v[v["grupo"] != "Resto de vendedores"]
    resto = v[v["grupo"] == "Resto de vendedores"]
    m1, m2, m3 = st.columns(3)
    tarjeta(m1, "Vendedores detectados", str(len(malos)), f"de {len(v)} con ventas y entregas")
    tarjeta(m2, "Entregas tardías (ellos)", f"{malos['pct_tardios'].mean():.0%}",
            f"el resto: {resto['pct_tardios'].mean():.0%}")
    tarjeta(m3, "Estrellas (ellos)", f"{malos['estrellas'].mean():.2f}",
            f"el resto: {resto['estrellas'].mean():.2f}")
    graf = (alt.Chart(v, title="Ventas vs. puntualidad por vendedor")
            .mark_circle(opacity=0.85, stroke="#fcfcfb", strokeWidth=1)
            .encode(x=alt.X("ventas:Q", title="Ventas (S/, escala log)", scale=alt.Scale(type="log"),
                            axis=alt.Axis(format="~s", values=[1e2, 1e3, 1e4, 1e5, 1e6, 1e7])),
                    y=alt.Y("pct_tardios:Q", title="% de entregas tardías", axis=alt.Axis(format="%")),
                    color=alt.Color("grupo:N", title=None,
                                    scale=alt.Scale(domain=["Resto de vendedores",
                                                            "Buenas ventas + envíos tardíos"],
                                                    range=[AZUL_CLARO, NARANJA])),
                    size=alt.condition("datum.grupo == 'Resto de vendedores'", alt.value(30), alt.value(80)),
                    tooltip=[alt.Tooltip("razon_social:N", title="Vendedor"),
                             alt.Tooltip("ventas:Q", title="Ventas", format=",.0f"),
                             alt.Tooltip("pct_tardios:Q", title="% tarde", format=".0%"),
                             alt.Tooltip("estrellas:Q", title="Estrellas", format=".2f")]))
    mostrar(graf, 380)
    st.dataframe(pct100(malos, "pct_tardios").sort_values("ventas", ascending=False)
                 [["razon_social", "ventas", "entregas", "pct_tardios", "dias", "estrellas", "resenas"]],
                 hide_index=True, column_config={
                     "razon_social": "Vendedor", "ventas": st.column_config.NumberColumn("Ventas", format="S/ %,.0f"),
                     "entregas": st.column_config.NumberColumn("Entregas", format="%d"),
                     "pct_tardios": st.column_config.NumberColumn("% tarde", format="%.0f %%"),
                     "dias": st.column_config.NumberColumn("Días (mediana)", format="%.1f"),
                     "estrellas": st.column_config.NumberColumn("Estrellas", format="%.2f"),
                     "resenas": st.column_config.NumberColumn("Reseñas", format="%d")})
    nota(f"Top 20 % en ventas y tasa de tardanza ≥ 1.5 × el promedio ({1.5 * tasa:.0%}). "
         "Es el mismo resultado que la consulta 5 de <code>03_consultas.sql</code>. "
         "Sus malas reseñas se explican por el retraso: el problema es el <b>despacho</b>, no el producto.")
