from datetime import datetime

import pandas as pd
import streamlit as st

from frontend import tienda as t
from frontend.analisis import pares
from frontend.componentes import grilla
from frontend.datos import repo
from frontend.estilo import RAIZ, color_avatar, esc, seccion

P = st.session_state["_P"]
id_cliente = st.session_state["id_cliente"]
cat = t.catalogo()

# ------------------------------------------------------------------ banner con el mejor cupón vigente
cupones = repo().cupones_vigentes(datetime.now())
if cupones:
    c = cupones[0]
    st.markdown(f"""
<div class='k-hero'>
  <div>
    <h2>Hasta {c.descuento_pct}% de descuento<br>en toda la tienda</h2>
    <p>Más de 9 000 productos de 700 tiendas de todo el Perú. Usa el cupón al pagar:</p>
    <span class='k-code'>{esc(c.codigo)}</span>
    <span style='color:#FFEDE6;font-size:0.8rem'>&nbsp; válido hasta el {c.vence:%d/%m/%Y}</span>
  </div>
  <div class='k-big'>🧺</div>
</div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ categorías


def ir_categoria(raiz: str):
    st.session_state["filtro_raiz"] = raiz
    st.session_state["filtro_q"] = ""
    st.session_state.pop("filtro_vendedor", None)


cols = st.columns(len(RAIZ), gap="small")
for i, (col, (nombre, (ic, bg))) in enumerate(zip(cols, RAIZ.items())):
    with col:
        st.markdown(f"<style>.st-key-cat_{i} button {{ --bg: {bg}; }}</style>", unsafe_allow_html=True)
        if st.button(ic, key=f"cat_{i}", width="stretch", on_click=ir_categoria, args=(nombre,),
                     help=f"Ver {nombre}"):
            st.switch_page(P["explorar"])
        st.markdown(f"<div class='k-catname'>{nombre.replace('Electrodomésticos', 'Electro&shy;domésticos')}</div>",
                    unsafe_allow_html=True)

# ------------------------------------------------------------------ más vendidos
seccion("🔥 Más vendidos", "los favoritos de la comunidad")
top = cat[cat["stock_total"] > 0].nlargest(8, "vendidos")
grilla(top, "top")

# ------------------------------------------------------------------ para ti (co-compras)
comprados = t.productos_comprados(id_cliente)
if comprados:
    p = pares()
    socios = (p[p["id_producto_a"].isin(comprados)][["id_producto_b", "juntos"]]
              .rename(columns={"id_producto_b": "id"}))
    socios = (pd.concat([socios, p[p["id_producto_b"].isin(comprados)][["id_producto_a", "juntos"]]
                         .rename(columns={"id_producto_a": "id"})])
              .groupby("id")["juntos"].sum().sort_values(ascending=False))
    socios = socios[~socios.index.isin(comprados) & ~socios.index.isin(top["id_producto"])]
    socios = socios.rename("afinidad").reset_index()
    para_ti = (socios.merge(cat, left_on="id", right_on="id_producto")
               .query("stock_total > 0").sort_values("afinidad", ascending=False).head(4))
    if len(para_ti):
        seccion("✨ Para ti", "porque otros clientes los compran junto con lo que tú ya compraste")
        grilla(para_ti, "parati")

# ------------------------------------------------------------------ tiendas destacadas
seccion("🏪 Tiendas destacadas", "las que más venden")


def ir_tienda(idv: int):
    st.session_state["filtro_vendedor"] = idv
    st.session_state["filtro_raiz"] = "Todas"
    st.session_state["filtro_q"] = ""


tiendas = t.tiendas_top(6)
cols = st.columns(3, gap="medium")
for i, tr in enumerate(tiendas.itertuples()):
    with cols[i % 3], st.container(key=f"tienda_{tr.id_vendedor}"):
        iniciales = "".join(w[0] for w in tr.razon_social.split()[:2]).upper()
        a, b = st.columns([1, 4], vertical_alignment="center")
        a.markdown(f"<div class='k-avatar' style='background:{color_avatar(tr.razon_social)}'>{iniciales}</div>",
                   unsafe_allow_html=True)
        b.markdown(f"**{esc(tr.razon_social)}**  \n<span class='k-meta'><span class='k-star'>★</span> "
                   f"{tr.reputacion:.1f} · {tr.productos:,} productos · {RAIZ[tr.raiz][0]} {tr.raiz}</span>",
                   unsafe_allow_html=True)
        if st.button("Ver tienda", key=f"vt_{tr.id_vendedor}", width="stretch",
                     on_click=ir_tienda, args=(int(tr.id_vendedor),)):
            st.switch_page(P["explorar"])
