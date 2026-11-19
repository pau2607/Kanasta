from datetime import datetime

import streamlit as st

from frontend import analisis as an
from frontend import tienda as t
from frontend.componentes import carrito
from frontend.datos import estrategias, repo, servicio
from frontend.estilo import boleta_html, emoji, esc, fondo, soles
from marketplace import ErrorPedido
from marketplace.envios import dias_prometidos, es_lima

P = st.session_state["_P"]
ss = st.session_state
id_cliente = ss["id_cliente"]
cli = t.cliente(id_cliente)
destino = cli["departamento"]
items = carrito()

st.markdown("## Tu carrito")
if not items:
    st.markdown("<div style='text-align:center;padding:3rem 0'><div style='font-size:4rem'>🛒</div>"
                "<h3>Tu carrito está vacío</h3><p class='k-muted'>Agrega productos para empezar tu pedido.</p></div>",
                unsafe_allow_html=True)
    c = st.columns([2, 1, 2])
    c[1].page_link(P["explorar"], label="Explorar productos", icon=":material/storefront:")
    st.stop()

cat = t.catalogo().set_index("id_producto")
r = repo()
izq, der = st.columns([1.35, 1], gap="large")

# ================================================================== productos
with izq:
    for idv, cant in list(items.items()):
        v = r.variante(idv)
        p = cat.loc[v.id_producto]
        with st.container(key=f"panel_item_{idv}"):
            a, b, c, d = st.columns([0.9, 3.2, 1.3, 0.5], vertical_alignment="center")
            a.markdown(f"<div class='k-tile' style='height:70px;font-size:2.2rem;background:{fondo(p['raiz'])}'>"
                       f"{emoji(p['hoja'], p['raiz'])}</div>", unsafe_allow_html=True)
            variante = "" if v.talla == "Única" else f"Talla {v.talla} · "
            b.markdown(f"**{esc(v.titulo)}**  \n<span class='k-meta'>{variante}{v.color} · "
                       f"{esc(p['razon_social'])}</span>  \n<b>{soles(float(v.precio) * cant)}</b>",
                       unsafe_allow_html=True)
            nueva = c.number_input("Cant.", 1, max(v.stock, cant, 1), cant, key=f"q_{idv}",
                                   label_visibility="collapsed")
            if nueva != cant:
                items[idv] = int(nueva)
                st.rerun()
            if d.button("", key=f"del_{idv}", icon=":material/delete:", help="Quitar"):
                del items[idv]
                st.rerun()
    st.page_link(P["explorar"], label="Seguir comprando", icon=":material/arrow_back:")

# ================================================================== checkout
with der, st.container(key="panel_checkout"):
    st.markdown("#### Entrega")
    st.markdown(f"📍 **{cli['distrito']}**, {cli['provincia']} — {destino}  \n"
                f"<span class='k-meta'>Para {esc(cli['nombre'])}</span>", unsafe_allow_html=True)

    # ---------------- envío (Strategy)
    zona = "Lima/Callao" if es_lima(destino) else "Provincia"
    hist = an.entregas()["por_courier"]
    hist = hist[hist["zona"] == zona].set_index("courier")["tardios"]
    opciones = [e for e in estrategias() if e.atiende(destino)]
    puntual = min(opciones, key=lambda e: hist.get(e.nombre, 1))
    barata = min(opciones, key=lambda e: e.costo(destino))

    def etiqueta(e):
        extra = " · ⭐ más puntual" if e is puntual else (" · 💸 más barato" if e is barata else "")
        return (f"{e.nombre} — {soles(e.costo(destino))} · {100 - hist.get(e.nombre, 0) * 100:.0f}% a tiempo"
                f"{extra}")

    st.markdown("#### Envío")
    por_nombre = {e.nombre: e for e in opciones}
    nombre_elegido = st.radio("Courier", list(por_nombre), index=list(por_nombre).index(puntual.nombre),
                              format_func=lambda n: etiqueta(por_nombre[n]), label_visibility="collapsed")
    elegido = por_nombre[nombre_elegido]
    st.caption(f"Llega a más tardar el {elegido.fecha_estimada(datetime.now(), destino):%d/%m} "
               f"({dias_prometidos(destino)} días). "
               + ("Chazki y 99minutos solo reparten en Lima." if not es_lima(destino) else ""))

    # ---------------- pago
    st.markdown("#### Pago")
    METODOS = {"Yape": "📱 Yape", "Plin": "📲 Plin", "Tarjeta de crédito": "💳 Crédito",
               "Tarjeta de débito": "💳 Débito", "PagoEfectivo": "🏦 PagoEfectivo",
               "Transferencia": "🔁 Transferencia"}
    metodo = st.pills("Método de pago", list(METODOS), default="Yape", format_func=METODOS.get,
                      label_visibility="collapsed") or "Yape"
    if metodo == "Yape":
        st.caption("🎉 Promo: 3% de descuento pagando con Yape.")
    if metodo == "PagoEfectivo":
        st.caption("Te daremos un código para pagar en agentes o banca móvil. El pedido se confirma al pagar.")

    # ---------------- cupón
    with st.expander("¿Tienes un cupón?", expanded=bool(ss.get("cupon_codigo"))):
        cc = st.columns([3, 1.3], vertical_alignment="bottom")
        codigo = cc[0].text_input("Código", value=ss.get("cupon_codigo", ""), placeholder="Ej. INVIERNO981")
        if cc[1].button("Aplicar", width="stretch"):
            ss["cupon_codigo"] = codigo.strip().upper()
            st.rerun()
    cupon = None
    if ss.get("cupon_codigo"):
        cupon = r.cupon(ss["cupon_codigo"])
        if cupon is None:
            st.error(f"El cupón {ss['cupon_codigo']} no existe.")
        elif not cupon.vigente(datetime.now().date()):
            st.error(f"El cupón {cupon.codigo} venció el {cupon.vence:%d/%m/%Y}.")
            cupon = None
        else:
            st.success(f"Cupón {cupon.codigo} aplicado: −{cupon.descuento_pct}%")

    # ---------------- Builder + Decorator
    primera = t.compras_validas(id_cliente) == 0
    b = servicio().nuevo_pedido(id_cliente)
    for idv, cant in items.items():
        b.agregar(r.variante(idv), cant)
    if cupon:
        b.con_cupon(cupon)
    b.con_descuento_volumen(min_unidades=6, pct=5)
    if metodo == "Yape":
        b.con_descuento_medio_pago("Yape", 3)
    if primera:
        b.con_descuento_fijo(10, "Primera compra")
    b.enviar_con(elegido)
    try:
        pedido = b.build()
    except ErrorPedido as e:
        st.error(str(e))
        st.stop()
    envio = float(elegido.cotizar(destino))
    total = float(pedido.total) + envio

    st.markdown("#### Resumen")
    lineas = [(et, float(m)) for et, m in pedido.precio.lineas()]
    st.markdown(boleta_html(lineas, total, (elegido.nombre, envio)), unsafe_allow_html=True)
    if pedido.descuento > 0:
        st.markdown(f"<div style='color:#00A862;font-weight:600;font-size:0.9rem;margin-top:6px'>"
                    f"Ahorras {soles(float(pedido.descuento))} 🎉</div>", unsafe_allow_html=True)

    texto_boton = (f"Generar código de pago · {soles(total)}" if metodo == "PagoEfectivo"
                   else f"Pagar {soles(total)}")
    if st.button(texto_boton, type="primary", width="stretch", icon=":material/lock:"):
        srv = servicio()
        srv.registrar(pedido)
        promos = "; ".join(et for et, m in lineas[1:] if m < 0)
        t.guardar_checkout(pedido.id_pedido, elegido.courier.id_courier, envio, metodo, promos)
        if metodo == "PagoEfectivo":
            t.registrar_pago_pendiente(pedido.id_pedido, metodo, float(pedido.total))
            ss["aviso_pedido"] = ("info", f"Pedido #{pedido.id_pedido} creado. Paga con el código CIP "
                                          f"**{pedido.id_pedido:09d}** en agentes o banca móvil.")
        else:
            try:
                srv.pagar(pedido, metodo)       # State: pendiente → pagado (sp_confirmar_pedido)
                ss["aviso_pedido"] = ("ok", f"¡Listo! Pago confirmado. Tu pedido #{pedido.id_pedido} "
                                            f"ya se está preparando.")
            except Exception as e:  # noqa: BLE001 — p. ej. otro cliente compró el último stock
                ss["aviso_pedido"] = ("error", f"El pedido #{pedido.id_pedido} quedó pendiente: "
                                               f"{getattr(e, 'msg', e)}")
        items.clear()
        ss.pop("cupon_codigo", None)
        ss["pedido_sel"] = pedido.id_pedido
        st.switch_page(P["pedidos"])
    st.caption("🔒 Pago seguro · Puedes cancelar mientras no haya sido despachado.")

with st.expander("Ver cómo funciona por dentro (patrones de diseño)"):
    st.markdown(f"""
- **Builder** — `PedidoBuilder` juntó {pedido.unidades} unidades, validó stock, cupón y que *{elegido.nombre}*
  llegue a {destino}.
- **Decorator** — precio: {' → '.join(et for et, m in lineas if m != 0 or et == 'Subtotal')}.
- **Strategy** — `{type(elegido).__name__}` calcula el envío de {elegido.nombre}: {soles(envio)}.
- **State** — al pagar, el pedido pasa de *pendiente* a *pagado* llamando a `sp_confirmar_pedido`.""")
