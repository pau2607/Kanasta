import streamlit as st

from frontend import tienda as t
from frontend.datos import pagos_de, repo, servicio
from frontend.estilo import chip_estado, emoji, esc, fondo, pasos_html, soles
from marketplace import TransicionInvalida
from marketplace.modelos import METODOS_PAGO

ss = st.session_state
id_cliente = ss["id_cliente"]

aviso = ss.pop("aviso_pedido", None)
if aviso:
    {"ok": st.success, "info": st.info, "error": st.error}[aviso[0]](aviso[1])

# ================================================================== detalle de un pedido
sel = ss.get("pedido_sel")
mios = t.pedidos_cliente(id_cliente)
if sel and sel in set(mios["id_pedido"]):
    if st.button("Mis pedidos", icon=":material/arrow_back:", type="tertiary"):
        ss.pop("pedido_sel")
        st.rerun()
    pedido = repo().pedido(sel)
    info = mios.set_index("id_pedido").loc[sel]
    k = t.checkout_de(sel)
    pagos = pagos_de(sel)
    st.markdown(f"## Pedido #{sel} &nbsp;{chip_estado(pedido.estado)}", unsafe_allow_html=True)
    st.caption(f"Realizado el {pedido.fecha:%d/%m/%Y a las %H:%M}")

    fechas = {"pendiente": f"{pedido.fecha:%d/%m %H:%M}"}
    if (pagos["estado"].isin(["aprobado", "reembolsado"])).any():
        fechas["pagado"] = "✓"
    if pedido.fecha_envio is not None:
        fechas["enviado"] = f"{pedido.fecha_envio:%d/%m %H:%M}"
    if pedido.fecha_entrega is not None:
        fechas["entregado"] = f"{pedido.fecha_entrega:%d/%m %H:%M}"
    with st.container(key="panel_seguimiento"):
        st.markdown(pasos_html(pedido.estado, fechas), unsafe_allow_html=True)
        if pedido.estado == "enviado":
            st.markdown(f"🛵 **{pedido.estrategia_envio.nombre}** lleva tu pedido · llega a más tardar el "
                        f"**{pedido.fecha_estimada:%d/%m/%Y}**")
        elif pedido.estado == "entregado":
            tarde = pedido.entrega_tardia
            st.markdown(f"🏠 Entregado por **{pedido.estrategia_envio.nombre}** el {pedido.fecha_entrega:%d/%m/%Y}"
                        + (" · llegó con retraso, lo sentimos 🙏" if tarde else " · a tiempo ✨"))
        elif pedido.estado == "pagado":
            st.markdown("📦 La tienda está preparando tu pedido." +
                        (f" Lo enviaremos con **{k['courier']}**." if k else ""))
        elif pedido.estado == "pendiente":
            st.markdown("🕓 Tu pedido está esperando el pago." +
                        (f" Código CIP: **{sel:09d}**" if k and k["metodo_pago"] == "PagoEfectivo" else ""))

    izq, der = st.columns([1.4, 1], gap="large")
    with izq:
        st.markdown("#### Productos")
        resenados = t.resenados_por(id_cliente)
        for it in t.items_pedido(sel).itertuples():
            with st.container(key=f"panel_it_{it.id_variante}"):
                a, b = st.columns([0.8, 4], vertical_alignment="center")
                a.markdown(f"<div class='k-tile' style='height:62px;font-size:2rem;background:{fondo(it.raiz)}'>"
                           f"{emoji(it.hoja, it.raiz)}</div>", unsafe_allow_html=True)
                var = "" if it.talla == "Única" else f"Talla {it.talla} · "
                b.markdown(f"**{esc(it.titulo)}**  \n<span class='k-meta'>{var}{it.color} · {it.cantidad} × "
                           f"{soles(it.precio_unit)}</span>", unsafe_allow_html=True)
                if pedido.estado == "entregado":
                    if it.id_producto in resenados:
                        b.caption("✓ Ya calificaste este producto")
                    else:
                        estrellas = b.feedback("stars", key=f"fb_{sel}_{it.id_producto}")
                        if estrellas is not None:
                            com = b.text_input("Cuéntanos más (opcional)", key=f"com_{sel}_{it.id_producto}")
                            if b.button("Enviar opinión", key=f"env_{sel}_{it.id_producto}", type="primary"):
                                t.crear_resena(int(it.id_producto), id_cliente, estrellas + 1, com.strip())
                                st.toast("¡Gracias por tu opinión!", icon="⭐")
                                st.rerun()
    with der, st.container(key="panel_resumen"):
        st.markdown("#### Resumen")
        envio = float(k["costo_envio"]) if k else (float(pedido.costo_envio) if pedido.costo_envio else 0.0)
        filas = [f"<tr><td>Productos</td><td>{soles(info['total'])}</td></tr>"]
        if envio:
            filas.append(f"<tr><td>Envío</td><td>{soles(envio)}</td></tr>")
        filas.append(f"<tr class='k-total'><td>Total</td><td>{soles(info['total'] + envio)}</td></tr>")
        st.markdown("<table class='k-boleta'>" + "".join(filas) + "</table>", unsafe_allow_html=True)
        if k and k["descuentos"]:
            st.caption(f"Promociones: {k['descuentos']}")
        if not pagos.empty:
            ult = pagos.iloc[-1]
            st.caption(f"Pago: {ult['metodo']} · {ult['estado']}")

        # ---------------- acciones del cliente (las valida el State)
        srv = servicio()

        def hacer(fn, ok):
            try:
                fn()
                ss["aviso_pedido"] = ("ok", ok)
            except TransicionInvalida as e:
                ss["aviso_pedido"] = ("error", str(e))
            except Exception as e:  # noqa: BLE001
                ss["aviso_pedido"] = ("error", f"No se pudo completar: {getattr(e, 'msg', e)}")
            st.rerun()

        if pedido.estado == "pendiente":
            m = st.selectbox("Pagar con", METODOS_PAGO, index=2)
            if st.button(f"Pagar {soles(info['total'] + envio)}", type="primary", width="stretch"):
                hacer(lambda: srv.pagar(pedido, m), "¡Pago confirmado! Tu pedido ya se está preparando.")
        if pedido.estado in ("pendiente", "pagado"):
            with st.popover("Cancelar pedido", width="stretch"):
                st.markdown("¿Seguro que quieres cancelarlo?" +
                            (" Te devolveremos el dinero." if pedido.estado == "pagado" else ""))
                if st.button("Sí, cancelar", type="primary"):
                    hacer(lambda: srv.cancelar(pedido), "Pedido cancelado." +
                          (" El reembolso se procesará en 3–5 días." if pedido.estado == "pagado" else ""))
    st.stop()

# ================================================================== lista de pedidos
st.markdown("## Mis pedidos")
if mios.empty:
    st.info("Aún no tienes pedidos.")
    st.page_link(ss["_P"]["explorar"], label="Explorar productos", icon=":material/storefront:")
    st.stop()

filtro = st.segmented_control("Mostrar", ["Todos", "En curso", "Entregados", "Cancelados"], default="Todos",
                              label_visibility="collapsed")
grupos = {"En curso": ["pendiente", "pagado", "enviado"], "Entregados": ["entregado"], "Cancelados": ["cancelado"]}
lista = mios if filtro in (None, "Todos") else mios[mios["estado"].isin(grupos[filtro])]
cat = t.catalogo().set_index("id_producto")
for p in lista.head(30).itertuples():
    prod = cat.loc[p.id_producto_1] if p.id_producto_1 in cat.index else None
    with st.container(key=f"ped_{p.id_pedido}"):
        a, b, c, d = st.columns([0.7, 3.6, 1.4, 1.2], vertical_alignment="center")
        if prod is not None:
            a.markdown(f"<div class='k-tile' style='height:58px;font-size:1.9rem;background:{fondo(prod['raiz'])}'>"
                       f"{emoji(prod['hoja'], prod['raiz'])}</div>", unsafe_allow_html=True)
        nombre = esc(prod["titulo"]) if prod is not None else "Pedido"
        extra = f" y {p.items - 1} más" if p.items > 1 else ""
        b.markdown(f"**{nombre}**{extra}  \n<span class='k-meta'>#{p.id_pedido} · {p.fecha:%d/%m/%Y} · "
                   f"{int(p.unidades)} unidad{'es' if p.unidades != 1 else ''}</span>", unsafe_allow_html=True)
        c.markdown(f"{chip_estado(p.estado)}<br><b>{soles(p.total)}</b>", unsafe_allow_html=True)
        if d.button("Ver detalle", key=f"vd_{p.id_pedido}", width="stretch"):
            ss["pedido_sel"] = int(p.id_pedido)
            st.rerun()
