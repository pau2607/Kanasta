"""Componentes de la tienda: tarjeta de producto, grilla, detalle (modal) y carrito."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import tienda as t
from .estilo import esc, estrellas_html, emoji, fondo, soles


# ------------------------------------------------------------------ carrito (sesión)
def carrito() -> dict[int, int]:
    return st.session_state.setdefault("carrito", {})


def unidades_carrito() -> int:
    return sum(carrito().values())


def agregar(id_variante: int, cantidad: int = 1):
    c = carrito()
    c[id_variante] = c.get(id_variante, 0) + cantidad


def agregar_rapido(id_producto: int) -> bool:
    """Botón 'Agregar' de la tarjeta: toma la variante con más stock."""
    v = t.variantes_producto(id_producto)
    v = v[v["stock"] > 0].sort_values("stock", ascending=False)
    if v.empty:
        return False
    agregar(int(v.iloc[0]["id_variante"]))
    return True


# ------------------------------------------------------------------ tarjeta
def _badge(p) -> str:
    if p["stock_total"] == 0:
        return "<span class='k-badge' style='background:#EEE;color:#777'>Agotado</span>"
    if p["stock_total"] <= 5:
        return "<span class='k-badge'>Últimas unidades</span>"
    if p["vendidos"] >= 500:
        return "<span class='k-badge' style='background:#FFF6D6;color:#8A6D00'>🔥 Más vendido</span>"
    return ""


def tarjeta(p, prefijo: str):
    pid = int(p["id_producto"])
    with st.container(key=f"card_{prefijo}_{pid}"):
        st.markdown(
            f"<div class='k-card-body'><div class='k-tile' style='background:{fondo(p['raiz'])}'>{_badge(p)}"
            f"{emoji(p['hoja'], p['raiz'])}</div>"
            f"<div class='k-name'>{esc(p['titulo'])}</div>"
            f"<div class='k-meta'>{estrellas_html(p['rating'], p['n_resenas'])} · {p['vendidos']:,} vendidos</div>"
            f"<div class='k-price'>{soles(p['precio'])}</div>"
            f"<div class='k-meta'>🏪 {esc(p['razon_social'])}</div></div>",
            unsafe_allow_html=True)
        b1, b2 = st.columns(2, gap="small")
        if b1.button("Ver", key=f"ver_{prefijo}_{pid}", width="stretch"):
            detalle_producto(pid)
        if b2.button("Agregar", key=f"add_{prefijo}_{pid}", type="primary", width="stretch",
                     disabled=p["stock_total"] == 0):
            if agregar_rapido(pid):
                st.toast(f"Agregado: {p['titulo']}", icon="🛒")
                st.rerun()


def grilla(df: pd.DataFrame, prefijo: str, columnas: int = 4):
    filas = [df.iloc[i:i + columnas] for i in range(0, len(df), columnas)]
    for fila in filas:
        cols = st.columns(columnas, gap="medium")
        for col, (_, p) in zip(cols, fila.iterrows()):
            with col:
                tarjeta(p, prefijo)


# ------------------------------------------------------------------ detalle (modal)
@st.dialog("Detalle del producto", width="large")
def detalle_producto(id_producto: int):
    cat = t.catalogo()
    p = cat[cat["id_producto"] == id_producto].iloc[0]
    id_usuario = st.session_state.get("id_cliente", 2474)
    izq, der = st.columns([2, 3], gap="large")
    with izq:
        st.markdown(f"<div class='k-tile' style='height:240px;font-size:6rem;background:{fondo(p['raiz'])}'>"
                    f"{emoji(p['hoja'], p['raiz'])}</div>", unsafe_allow_html=True)
        st.caption(f"{p['raiz']} › {p['sub']} › {p['hoja']}")
    with der:
        st.markdown(f"### {esc(p['titulo'])}")
        st.markdown(f"{estrellas_html(p['rating'], p['n_resenas'])} &nbsp;·&nbsp; {p['vendidos']:,} vendidos",
                    unsafe_allow_html=True)
        st.markdown(f"<div class='k-price' style='font-size:1.6rem'>{soles(p['precio'])}</div>",
                    unsafe_allow_html=True)
        st.markdown(f"<span class='k-meta'>Vendido por <b>{esc(p['razon_social'])}</b> · "
                    f"<span class='k-star'>★</span> {p['reputacion']:.1f} reputación</span>",
                    unsafe_allow_html=True)

        var = t.variantes_producto(id_producto)
        tallas = sorted(var["talla"].unique().tolist())
        talla = tallas[0]
        if len(tallas) > 1 or tallas[0] != "Única":
            talla = st.pills("Talla", tallas, default=tallas[0], key=f"talla_{id_producto}") or tallas[0]
        por_talla = var[var["talla"] == talla]
        colores = por_talla["color"].tolist()
        con_stock = por_talla[por_talla["stock"] > 0]["color"].tolist()
        color = st.pills("Color", colores, default=(con_stock or colores)[0], key=f"color_{id_producto}") \
            or (con_stock or colores)[0]
        v = por_talla[por_talla["color"] == color].iloc[0]
        stock = int(v["stock"])
        if stock == 0:
            st.markdown("<span class='k-chip' style='background:#FDECEC;color:#B42318'>Agotado</span>",
                        unsafe_allow_html=True)
        elif stock <= 5:
            st.markdown(f"<span class='k-badge'>¡Solo quedan {stock}!</span>", unsafe_allow_html=True)
        else:
            st.caption(f"{stock} disponibles")
        c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
        cant = c1.number_input("Cantidad", 1, max(stock, 1), 1, key=f"cant_{id_producto}", disabled=stock == 0)
        if c2.button(f"Agregar · {soles(p['precio'] * cant)}", type="primary", width="stretch",
                     disabled=stock == 0, icon=":material/add_shopping_cart:"):
            agregar(int(v["id_variante"]), int(cant))
            st.toast(f"Agregado al carrito: {p['titulo']}", icon="🛒")
            st.rerun()
        es_fav = id_producto in t.favoritos_de(id_usuario)
        if st.button("❤️ En favoritos" if es_fav else "🤍 Guardar en favoritos", key=f"fav_{id_producto}"):
            t.alternar_favorito(id_usuario, id_producto)
            st.rerun(scope="fragment")

    tab1, tab2, tab3 = st.tabs(["Opiniones", "Preguntas", "Se compra junto con"])
    with tab1:
        r = t.resenas_producto(id_producto)
        if r.empty:
            st.caption("Todavía no hay opiniones con comentario.")
        for x in r.itertuples():
            st.markdown(f"<span class='k-star'>{'★' * int(x.estrellas)}</span>"
                        f"<span class='k-muted'>{'★' * (5 - int(x.estrellas))}</span> "
                        f"&nbsp;<b>{esc(x.nombre.split()[0])}</b> "
                        f"<span class='k-muted'>· {x.fecha:%d/%m/%Y}</span><br>{esc(x.comentario)}",
                        unsafe_allow_html=True)
    with tab2:
        q = t.preguntas_producto(id_producto)
        for x in q.itertuples():
            resp = x.respuesta if isinstance(x.respuesta, str) else "Esperando respuesta del vendedor…"
            st.markdown(f"**{esc(x.texto)}**  \n<span class='k-meta'>↳ {esc(resp)}</span>",
                        unsafe_allow_html=True)
        with st.form(f"preg_{id_producto}", clear_on_submit=True, border=False):
            txt = st.text_input("Pregúntale al vendedor", placeholder="¿Tiene garantía?")
            if st.form_submit_button("Preguntar") and txt.strip():
                t.crear_pregunta(id_producto, id_usuario, txt.strip())
                st.success("Pregunta enviada al vendedor.")
    with tab3:
        from .analisis import recomendar
        rec = recomendar(id_producto, 3)
        if rec.empty:
            st.caption("Sin datos de compras conjuntas.")
        for x in rec.itertuples():
            st.markdown(f"• **{esc(x.titulo)}** — lo lleva el {x.conf:.0%} de quienes compran este producto")
