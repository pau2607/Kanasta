from html import escape
import streamlit as st

from frontend import tienda as t
from frontend.datos import estrategias, leer, pagos_de, repo, servicio, stock_items
from frontend.estilo import chip_estado, soles
from frontend.graficos import AZUL, ESTADO_COLOR, nota, patron
from marketplace import DestinoNoAtendido, TransicionInvalida
from marketplace.modelos import METODOS_PAGO

ss = st.session_state
st.markdown("## Gestión de pedidos " + patron("STATE"), unsafe_allow_html=True)

msg = ss.pop("msg_admin", None)
if msg:
    {"ok": st.success, "state": st.error, "warn": st.warning, "db": st.error}[msg[0]](msg[1])

conteo = t.conteo_estados()
BANDEJAS = [("pendiente", "Por pagar"), ("pagado", "Por despachar"), ("enviado", "En camino"),
            ("entregado", "Entregados"), ("cancelado", "Cancelados")]
# después de una acción, la bandeja salta al nuevo estado del pedido y la tabla se reinicia
if "_bandeja_next" in ss:
    ss["bandeja_sel"] = ss.pop("_bandeja_next")
    ss["tabla_v"] = ss.get("tabla_v", 0) + 1
ss.setdefault("bandeja_sel", "pagado")
bandeja = st.segmented_control(
    "Bandeja", [b[0] for b in BANDEJAS], key="bandeja_sel",
    format_func=lambda e: f"{dict(BANDEJAS)[e]} ({conteo.get(e, 0):,})", label_visibility="collapsed")
bandeja = bandeja or "pagado"

lista = t.pedidos_por_estado(bandeja, 100).fillna({"courier_elegido": "—", "metodo_pago": "—"})
st.caption("Los 100 más recientes · haz clic en una fila para gestionarlo. Los pedidos creados desde la "
           "tienda muestran el courier y el método que eligió el cliente.")
sel = st.dataframe(lista, hide_index=True, height=300, on_select="rerun", selection_mode="single-row",
                   key=f"tabla_{bandeja}_{ss.get('tabla_v', 0)}", column_config={
                       "id_pedido": st.column_config.NumberColumn("Pedido", format="%d"),
                       "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY HH:mm"),
                       "cliente": "Cliente", "destino": "Destino",
                       "total": st.column_config.NumberColumn("Total", format="S/ %,.2f"),
                       "courier_elegido": "Courier elegido", "metodo_pago": "Pago"})
filas = sel.selection.rows if sel else []
if filas:
    ss["admin_pedido"] = int(lista.iloc[filas[0]]["id_pedido"])
id_pedido = ss.get("admin_pedido")
if not id_pedido:
    st.info("Selecciona un pedido de la tabla.")
    st.stop()

try:
    pedido = repo().pedido(id_pedido)
except LookupError:
    st.warning(f"No existe el pedido {id_pedido}.")
    st.stop()
info = leer("""SELECT u.nombre, d.nombre AS distrito, d.departamento FROM pedidos p
               JOIN usuarios u USING (id_usuario) JOIN distritos d USING (id_distrito)
               WHERE p.id_pedido = %s""", (id_pedido,)).iloc[0]
pagos = pagos_de(id_pedido)
k = t.checkout_de(id_pedido)

st.divider()
st.markdown(f"### Pedido #{id_pedido} &nbsp; {chip_estado(pedido.estado)}", unsafe_allow_html=True)
st.caption(f"{info['nombre']} · {info['distrito']}, {info['departamento']} · {pedido.fecha:%d/%m/%Y %H:%M} · "
           f"total {soles(pedido.total_bd)}" + (f" · eligió {k['courier']} y {k['metodo_pago']}" if k else ""))

# ------------------------------------------------------------------ diagrama de estados
estado = pedido.estado
visitados = {"pendiente", estado}
if estado in ("pagado", "enviado", "entregado") or (estado == "cancelado" and (pagos["estado"] == "reembolsado").any()):
    visitados.add("pagado")
if estado in ("enviado", "entregado"):
    visitados.add("enviado")


def nodo(n):
    if n == estado:
        c = ESTADO_COLOR[n]
        return f'{n} [fillcolor="{c}", fontcolor="white", color="{c}", penwidth=2]'
    if n in visitados:
        return f'{n} [fillcolor="#e8f1fc", fontcolor="#0b0b0b", color="{AZUL}"]'
    return f'{n} [fillcolor="#ffffff", fontcolor="#8a8984", color="#d9d8d3"]'


def arista(a, b, et):
    act = a == estado
    col = AZUL if act else "#c3c2b7"
    return f'{a} -> {b} [label="{et}", color="{col}", fontcolor="{col if act else "#8a8984"}", penwidth={2 if act else 1}]'


st.graphviz_chart("\n".join([
    'digraph { rankdir=LR; bgcolor="transparent"; nodesep=0.5; ranksep=0.8;',
    'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=12, width=1.3, height=0.45];',
    'edge [fontname="Helvetica", fontsize=10, arrowsize=0.7];',
    *[nodo(n) for n in ("pendiente", "pagado", "enviado", "entregado", "cancelado")],
    arista("pendiente", "pagado", "pagar"), arista("pagado", "enviado", "enviar"),
    arista("enviado", "entregado", "entregar"), arista("pendiente", "cancelado", "cancelar"),
    arista("pagado", "cancelado", "cancelar + reembolso"), "{rank=same; pagado; cancelado}", "}"]),
    width="stretch")

# ------------------------------------------------------------------ pista del reparto (la anima el profe)
if estado in ("enviado", "entregado"):
    courier_env = pedido.estrategia_envio.nombre if pedido.estrategia_envio else "el courier"
    if estado == "enviado":
        texto = f"🛵 <b>En camino</b> con {escape(courier_env)} · prometido para el {pedido.fecha_estimada:%d/%m/%Y}"
    else:
        texto = (f"🏠 <b>Entregado</b> el {pedido.fecha_entrega:%d/%m/%Y %H:%M} · "
                 + ("⚠️ con retraso" if pedido.entrega_tardia else "a tiempo"))
    with st.container(key=f"pista_{id_pedido}"):
        st.markdown(f'<div class="kp-pista-info" data-pedido="{id_pedido}" data-estado="{estado}" '
                    f'data-courier="{escape(courier_env)}">{texto}</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ acciones
posibles = pedido.acciones_posibles()
st.caption(f"Válidas en **{estado}**: {', '.join(posibles) or 'ninguna (estado final)'}. "
           "Los botones siempre están activos: el objeto de estado decide y rechaza lo que no corresponde.")


def ejecutar(fn, ok):
    try:
        fn()
        r = ("ok", ok)
        ss["_bandeja_next"] = pedido.estado        # seguir al mismo pedido en su nueva bandeja
    except TransicionInvalida as e:
        r = ("state", f"TransicionInvalida: {e}")
    except (DestinoNoAtendido, ValueError) as e:
        r = ("warn", f"{type(e).__name__}: {e}")
    except Exception as e:  # noqa: BLE001
        r = ("db", f"MySQL rechazó la operación: {getattr(e, 'msg', e)}")
    ss["msg_admin"] = r
    st.rerun()


srv = servicio()
a1, a2, a3, a4 = st.columns(4, gap="medium")
with a1.container(border=True):
    st.markdown("**💳 Confirmar pago**")
    pref_m = k["metodo_pago"] if k else "Yape"
    metodo = st.selectbox("Método", METODOS_PAGO, index=METODOS_PAGO.index(pref_m), label_visibility="collapsed")
    if st.button("Confirmar pago", type="primary" if "pagar" in posibles else "secondary", width="stretch"):
        ejecutar(lambda: srv.pagar(pedido, metodo), f"Pago confirmado ({metodo}). sp_confirmar_pedido descontó el stock.")
with a2.container(border=True):
    st.markdown("**🛵 Despachar**")
    ests = estrategias()
    nombres = [e.nombre for e in ests]
    pref = k["courier"] if k else next((e.nombre for e in ests if e.atiende(pedido.departamento)), nombres[0])
    etq = {e.nombre: (f"{e.nombre} · {soles(e.costo(pedido.departamento))}" if e.atiende(pedido.departamento)
                      else f"{e.nombre} · no llega") for e in ests}
    courier = st.selectbox("Courier", nombres, index=nombres.index(pref), format_func=etq.get,
                           label_visibility="collapsed")
    est = ests[nombres.index(courier)]
    if st.button("Despachar", type="primary" if "enviar" in posibles else "secondary", width="stretch"):
        ejecutar(lambda: srv.despachar(pedido, est), f"Despachado con {courier} ({type(est).__name__}).")
with a3.container(border=True):
    st.markdown("**🏠 Marcar entregado**")
    st.caption("Registra la entrega con la hora actual.")
    if st.button("Entregado", type="primary" if "entregar" in posibles else "secondary", width="stretch"):
        ejecutar(lambda: srv.entregar(pedido), "Pedido entregado.")
with a4.container(border=True):
    st.markdown("**✖️ Cancelar**")
    st.caption("Si estaba pagado: devuelve stock y reembolsa.")
    if st.button("Cancelar", type="primary" if "cancelar" in posibles else "secondary", width="stretch"):
        ejecutar(lambda: srv.cancelar(pedido), "Pedido cancelado.")

# ------------------------------------------------------------------ detalle
d1, d2 = st.columns([3, 2], gap="large")
with d1:
    st.markdown("**Ítems y stock actual**")
    st.dataframe(stock_items(id_pedido), hide_index=True, column_order=["titulo", "color", "cantidad", "stock_actual"],
                 column_config={"titulo": st.column_config.TextColumn("Producto", width="medium"), "color": "Color",
                                "cantidad": st.column_config.NumberColumn("Cant.", width="small"),
                                "stock_actual": st.column_config.NumberColumn("Stock", width="small")})
    st.markdown("**Pagos**")
    st.dataframe(pagos, hide_index=True, column_config={
        "id_pago": "Pago", "metodo": "Método", "estado": "Estado",
        "monto": st.column_config.NumberColumn("Monto", format="S/ %,.2f")})
with d2:
    st.markdown("**Envío**")
    if pedido.estrategia_envio is None:
        st.caption("Todavía no se despacha.")
    else:
        st.markdown(
            f"- Courier: **{pedido.estrategia_envio.nombre}** ({type(pedido.estrategia_envio).__name__})\n"
            f"- Costo: **{soles(pedido.costo_envio)}**\n"
            f"- Despachado: {pedido.fecha_envio:%d/%m/%Y %H:%M}\n"
            f"- Prometido: {pedido.fecha_estimada:%d/%m/%Y}\n"
            + (f"- Entregado: {pedido.fecha_entrega:%d/%m/%Y %H:%M} · "
               + ("⚠️ tarde" if pedido.entrega_tardia else "a tiempo") if pedido.fecha_entrega else "- En camino"))
nota("Cada botón llama a un método del objeto <code>Pedido</code> (<code>pagar()</code>, <code>enviar()</code>…). "
     "El estado actual acepta o lanza <code>TransicionInvalida</code>; si MySQL rechaza la operación, el objeto "
     "vuelve a su estado anterior.")
