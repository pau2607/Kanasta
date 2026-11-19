"""Sistema visual de Kanasta: colores, íconos por categoría, CSS y componentes HTML."""
from __future__ import annotations

import html

import streamlit as st

MARCA = "kanasta"
CORAL, CORAL_OSCURO, CORAL_SUAVE = "#FF5533", "#E5401F", "#FFF0EB"
TINTA, TINTA_2, TINTA_3 = "#1F1F1F", "#5F5F5F", "#9A9A9A"
FONDO_2, BORDE = "#F6F6F7", "#ECECEC"
VERDE, AMARILLO, ROJO = "#00A862", "#FFB800", "#D93B3B"

RAIZ = {  # emoji, color de fondo del ícono
    "Tecnología": ("💻", "#E8F0FE"), "Moda": ("👗", "#FDE8EF"), "Hogar": ("🛋️", "#FFF4E0"),
    "Deportes": ("⚽", "#E6F7EE"), "Belleza": ("💄", "#FCE8F6"), "Juguetes y Bebés": ("🧸", "#FFF0E6"),
    "Herramientas": ("🛠️", "#EEF0F3"), "Electrodomésticos": ("🔌", "#E7F6FA"),
    "Mascotas": ("🐾", "#F3EDE4"), "Libros y Papelería": ("📚", "#EEEAFB"),
}
HOJA = {
    "Smartphones": "📱", "Fundas": "📲", "Cargadores": "🔋", "Laptops": "💻", "Monitores": "🖥️",
    "Teclados": "⌨️", "Audífonos": "🎧", "Parlantes": "🔊", "Micrófonos": "🎙️",
    "Polos": "👕", "Jeans": "👖", "Casacas": "🧥", "Blusas": "👚", "Vestidos": "👗", "Leggings": "🩳",
    "Zapatillas": "👟", "Botines": "🥾", "Sandalias": "🩴",
    "Ollas": "🍲", "Licuadoras": "🥤", "Cafeteras": "☕", "Sillas": "🪑", "Escritorios": "🗄️",
    "Estantes": "📚", "Lámparas": "💡", "Cuadros": "🖼️", "Cortinas": "🪟",
    "Mancuernas": "🏋️", "Colchonetas": "🧘", "Bandas elásticas": "🎽", "Bicicletas": "🚲", "Cascos": "⛑️",
    "Luces LED": "✨", "Carpas": "⛺", "Mochilas trekking": "🎒", "Linternas": "🔦",
    "Cremas": "🧴", "Sérums": "💧", "Protector solar": "☀️", "Labiales": "💄", "Bases": "🪞",
    "Paletas de sombras": "🎨", "Shampoo": "🧼", "Secadoras": "💨", "Planchas": "💇",
    "Peluches": "🧸", "Bloques de construcción": "🧱", "Juegos de mesa": "🎲", "Pañales": "👶",
    "Coches de bebé": "🛒", "Biberones": "🍼",
    "Taladros": "🔩", "Amoladoras": "⚙️", "Sierras": "🪚", "Juegos de llaves": "🔧",
    "Destornilladores": "🪛", "Martillos": "🔨",
    "Refrigeradoras": "🧊", "Lavadoras": "🫧", "Cocinas": "🍳", "Ventiladores": "🌀",
    "Calefactores": "🔥", "Aire acondicionado": "❄️",
    "Alimento para perro": "🦴", "Camas para perro": "🐕", "Correas": "🦮", "Alimento para gato": "🐟",
    "Arena sanitaria": "🐈", "Rascadores": "🧶",
    "Novelas": "📖", "Libros técnicos": "📘", "Libros infantiles": "📗", "Cuadernos": "📓",
    "Lapiceros": "🖊️", "Mochilas escolares": "🎒",
}
ESTADOS = {  # etiqueta para el cliente, color, ícono
    "pendiente": ("Por pagar", "#8A6D00", "#FFF6D6", "🕓"),
    "pagado": ("Preparando", "#1F5FBF", "#E8F0FE", "📦"),
    "enviado": ("En camino", "#6A3FD6", "#F0EBFD", "🛵"),
    "entregado": ("Entregado", "#0A7A48", "#E3F6EC", "✅"),
    "cancelado": ("Cancelado", "#B42318", "#FDECEC", "✖"),
}


def emoji(hoja: str | None, raiz: str | None = None) -> str:
    return HOJA.get(hoja or "", RAIZ.get(raiz or "", ("🛍️", ""))[0])


def fondo(raiz: str | None) -> str:
    return RAIZ.get(raiz or "", ("", FONDO_2))[1]


def soles(x: float) -> str:
    return f"S/ {float(x):,.2f}"


def esc(t) -> str:
    return html.escape(str(t))


def estrellas_html(rating, n: int) -> str:
    if rating is None or n == 0 or rating != rating:   # NaN
        return f"<span class='k-muted'>Nuevo</span>"
    return f"<span class='k-star'>★</span> <b>{rating:.1f}</b> <span class='k-muted'>({n})</span>"


def chip_estado(estado: str) -> str:
    et, color, bg, ic = ESTADOS.get(estado, (estado, TINTA_2, FONDO_2, ""))
    return (f"<span class='k-chip' style='color:{color};background:{bg}'>{ic} {et}</span>")


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)


CSS = f"""
<style>
/* ---------- base ---------- */
header[data-testid="stHeader"] {{ display: none; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none; }}
.block-container {{ padding-top: 1.1rem; padding-bottom: 4rem; max-width: 1200px; }}
h1, h2, h3, h4 {{ letter-spacing: -0.02em; }}
.k-muted {{ color: {TINTA_3}; }}
.k-star {{ color: {AMARILLO}; }}
.k-chip {{ display:inline-block; border-radius:999px; padding:3px 12px; font-size:0.82rem; font-weight:600; }}
.k-badge {{ display:inline-block; background:{CORAL_SUAVE}; color:{CORAL_OSCURO}; border-radius:8px;
            padding:2px 8px; font-size:0.75rem; font-weight:600; }}
.k-tag {{ display:inline-block; background:{FONDO_2}; color:{TINTA_2}; border-radius:6px; padding:1px 7px;
          font-size:0.72rem; font-weight:600; letter-spacing:0.03em; }}

/* ---------- encabezado ---------- */
.st-key-hdr_logo [data-testid="stPageLink"] a {{ padding:0 !important; background:transparent !important; }}
.st-key-hdr_logo [data-testid="stPageLink"] a p {{ font-size:1.55rem !important; font-weight:700 !important;
    color:{CORAL} !important; letter-spacing:-0.05em; }}
.k-logo {{ font-weight:700; font-size:1.75rem; color:{CORAL}; letter-spacing:-0.04em; line-height:1; }}
.k-logo small {{ display:block; font-size:0.68rem; color:{TINTA_3}; font-weight:500; letter-spacing:0; margin-top:3px; }}
.k-ubic {{ font-size:0.8rem; color:{TINTA_3}; line-height:1.15; }}
.k-ubic b {{ color:{TINTA}; font-size:0.92rem; }}
.st-key-hdr {{ border-bottom:1px solid {BORDE}; padding:0.5rem 0 0.6rem 0; margin-bottom:0.4rem;
               position:sticky; top:0; z-index:990; background:#FFFFFF; }}
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"]) {{ display:none; }}
.st-key-hdr [data-testid="stPageLink"] a {{ border-radius:999px; padding:0.25rem 0.8rem; }}
.st-key-hdr [data-testid="stPageLink"] a:hover {{ background:{CORAL_SUAVE}; }}
.st-key-hdr_carrito [data-testid="stPageLink"] a {{ background:{CORAL}; }}
.st-key-hdr_carrito [data-testid="stPageLink"] a p {{ color:white !important; font-weight:600; }}
.st-key-hdr_carrito [data-testid="stPageLink"] a:hover {{ background:{CORAL_OSCURO}; }}
.st-key-hdr_admin {{ background:{TINTA}; border-radius:18px; padding:0.6rem 1rem; margin-bottom:0.6rem; }}
.st-key-hdr_admin p, .st-key-hdr_admin span {{ color:#f2f2f2 !important; }}
.st-key-hdr_admin button {{ background:#2E2E2E !important; border:1px solid #4a4a4a !important; }}
.st-key-hdr_admin button:hover {{ background:{CORAL} !important; border-color:{CORAL} !important; }}
.st-key-hdr_admin [data-testid="stPageLink"] p {{ white-space:nowrap; }}
.st-key-hdr [data-testid="stPageLink"] p {{ white-space:nowrap; }}
.st-key-hdr_admin [data-testid="stPageLink"] a {{ border-radius:999px; padding:0.25rem 0.8rem; }}
.st-key-hdr_admin [data-testid="stPageLink"] a:hover {{ background:#333; }}

/* ---------- botones ---------- */
button[kind="primary"] {{ font-weight:600; }}

/* ---------- hero ---------- */
.k-hero {{ background: linear-gradient(115deg, {CORAL} 0%, #FF7A45 55%, #FF9F5A 100%); color:white;
           border-radius:24px; padding:1.6rem 1.8rem; display:flex; justify-content:space-between;
           align-items:center; margin: 0.4rem 0 1.2rem 0; }}
.k-hero h2 {{ color:white; margin:0 0 0.3rem 0; font-size:1.7rem; line-height:1.15; }}
.k-hero p {{ color:#FFEDE6; margin:0; font-size:0.95rem; }}
.k-hero .k-code {{ background:white; color:{CORAL_OSCURO}; font-weight:700; border-radius:10px; padding:4px 10px;
                   letter-spacing:0.05em; display:inline-block; margin-top:0.6rem; }}
.k-hero .k-big {{ font-size:4.2rem; line-height:1; }}

/* ---------- categorías ---------- */
[class*="st-key-cat_"] button {{ height:78px; border-radius:24px; border:none; background:var(--bg, {FONDO_2});
    transition: transform .12s ease; }}
[class*="st-key-cat_"] button:hover {{ transform: translateY(-3px); border:none; background:var(--bg); }}
[class*="st-key-cat_"] button p {{ font-size:2.1rem; line-height:1; }}
.k-catname {{ text-align:center; font-size:0.76rem; font-weight:600; line-height:1.2; color:{TINTA};
              margin-top:-0.35rem; min-height:2.4em; }}

/* ---------- tarjetas de producto ---------- */
[class*="st-key-card_"] {{ background:white; border:1px solid {BORDE}; border-radius:20px; padding:10px 10px 12px 10px;
    transition: box-shadow .15s ease, transform .15s ease; gap:0.45rem; }}
[class*="st-key-card_"]:hover {{ box-shadow:0 10px 28px rgba(0,0,0,0.08); transform: translateY(-2px); }}
.k-tile {{ height:132px; border-radius:15px; display:flex; align-items:center; justify-content:center;
           font-size:3.6rem; position:relative; }}
.k-tile .k-badge {{ position:absolute; top:8px; left:8px; }}
.k-name {{ font-weight:600; font-size:0.9rem; line-height:1.25; height:2.5em; overflow:hidden; color:{TINTA}; }}
.k-price {{ font-weight:700; font-size:1.05rem; color:{TINTA}; }}
.k-card-body {{ padding-bottom:0.55rem; }}
.k-meta {{ font-size:0.76rem; color:{TINTA_2}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}

/* ---------- tiendas ---------- */
[class*="st-key-tienda_"] {{ background:white; border:1px solid {BORDE}; border-radius:18px; padding:12px; }}
.k-avatar {{ width:46px; height:46px; border-radius:50%; display:flex; align-items:center; justify-content:center;
             font-weight:700; color:white; font-size:1rem; }}

/* ---------- secciones / paneles ---------- */
.k-sec {{ display:flex; align-items:baseline; justify-content:space-between; margin:1.6rem 0 0.6rem 0; }}
.k-sec .t {{ margin:0; font-size:1.35rem; font-weight:700; color:{TINTA}; letter-spacing:-0.02em; }}
.k-sec .s {{ color:{TINTA_3}; font-size:0.85rem; }}
[class*="st-key-panel_"] {{ background:white; border:1px solid {BORDE}; border-radius:20px; padding:16px 18px; }}
[class*="st-key-panel_gris"] {{ background:{FONDO_2}; border:none; }}

/* ---------- boleta ---------- */
.k-boleta {{ width:100%; font-size:0.9rem; border-collapse:collapse; }}
.k-boleta, .k-boleta tr, .k-boleta td {{ border:none !important; background:transparent !important; }}
.k-boleta td {{ padding:4px 0; }}
.k-boleta td:last-child {{ text-align:right; white-space:nowrap; }}
.k-boleta .k-desc td {{ color:{VERDE}; }}
.k-boleta .k-total td {{ font-weight:700; font-size:1.1rem; border-top:1px dashed {BORDE}; padding-top:8px; }}

/* ---------- seguimiento ---------- */
.k-steps {{ display:flex; align-items:flex-start; margin:0.8rem 0 0.4rem 0; }}
.k-step {{ flex:1; text-align:center; position:relative; font-size:0.78rem; color:{TINTA_3}; }}
.k-step .k-dot {{ width:38px; height:38px; border-radius:50%; margin:0 auto 6px auto; display:flex;
                  align-items:center; justify-content:center; background:{FONDO_2}; font-size:1.1rem;
                  position:relative; z-index:1; border:2px solid {FONDO_2}; }}
.k-step::before {{ content:""; position:absolute; top:19px; left:-50%; width:100%; height:3px; background:{BORDE}; z-index:0; }}
.k-step:first-child::before {{ display:none; }}
.k-step.hecho {{ color:{TINTA}; font-weight:600; }}
.k-step.hecho .k-dot {{ background:{CORAL}; border-color:{CORAL}; }}
.k-step.hecho::before {{ background:{CORAL}; }}
.k-step.actual .k-dot {{ box-shadow:0 0 0 5px {CORAL_SUAVE}; }}
.k-step.cancel .k-dot {{ background:{ROJO}; border-color:{ROJO}; }}

/* ---------- pedidos (lista) ---------- */
[class*="st-key-ped_"] {{ background:white; border:1px solid {BORDE}; border-radius:18px; padding:12px 16px; }}

/* ---------- admin ---------- */
.k-kpi {{ background:white; border:1px solid {BORDE}; border-radius:18px; padding:14px 16px; }}
.k-kpi .v {{ font-size:1.55rem; font-weight:700; color:{TINTA}; line-height:1.2; }}
.k-kpi .l {{ font-size:0.8rem; color:{TINTA_2}; }}
.k-kpi .d {{ font-size:0.75rem; color:{TINTA_3}; }}
.nota {{ background:#FFF7F4; border-left:3px solid {CORAL}; padding:0.7rem 0.9rem; border-radius:8px;
         color:{TINTA}; font-size:0.9rem; margin:0.4rem 0 1rem 0; }}
.patron {{ display:inline-block; background:{FONDO_2}; color:{TINTA_2}; border-radius:6px; padding:1px 8px;
           font-size:0.72rem; font-weight:600; margin-left:6px; vertical-align:middle; letter-spacing:0.03em; }}
</style>
"""


def seccion(titulo: str, sub: str = ""):
    st.markdown(f"<div class='k-sec'><div class='t'>{titulo}</div><div class='s'>{sub}</div></div>",
                unsafe_allow_html=True)


def kpi(col, etiqueta: str, valor: str, detalle: str = ""):
    col.markdown(f"<div class='k-kpi'><div class='l'>{etiqueta}</div><div class='v'>{valor}</div>"
                 f"<div class='d'>{detalle or '&nbsp;'}</div></div>", unsafe_allow_html=True)


def boleta_html(lineas: list[tuple[str, float]], total: float, envio: tuple[str, float] | None) -> str:
    filas = []
    for i, (et, m) in enumerate(lineas):
        clase = " class='k-desc'" if i > 0 and m < 0 else ""
        if i > 0 and m == 0:
            continue                                   # descuento que no aplica
        filas.append(f"<tr{clase}><td>{esc(et)}</td><td>{'−' if m < 0 else ''}{soles(abs(m))}</td></tr>")
    if envio:
        filas.append(f"<tr><td>Envío · {esc(envio[0])}</td><td>{soles(envio[1])}</td></tr>")
    filas.append(f"<tr class='k-total'><td>Total</td><td>{soles(total)}</td></tr>")
    return "<table class='k-boleta'>" + "".join(filas) + "</table>"


def pasos_html(estado: str, fechas: dict[str, str]) -> str:
    """Seguimiento tipo app de delivery: recibido → pagado → en camino → entregado."""
    orden = [("pendiente", "Pedido recibido", "🧾"), ("pagado", "Pago confirmado", "💳"),
             ("enviado", "En camino", "🛵"), ("entregado", "Entregado", "🏠")]
    if estado == "cancelado":
        hechos = {"pendiente"} | ({"pagado"} if fechas.get("pagado") else set())
        orden = [o for o in orden if o[0] in hechos] + [("cancelado", "Cancelado", "✖")]
        actual = "cancelado"
    else:
        idx = [o[0] for o in orden].index(estado)
        hechos = {o[0] for o in orden[: idx + 1]}
        actual = estado
    partes = []
    for clave, et, ic in orden:
        clases = ["k-step"]
        if clave in hechos or clave == "cancelado":
            clases.append("hecho")
        if clave == actual:
            clases.append("actual")
        if clave == "cancelado":
            clases.append("cancel")
        partes.append(f"<div class='{' '.join(clases)}'><div class='k-dot'>{ic}</div>{et}"
                      f"<div class='k-muted' style='font-weight:400'>{fechas.get(clave, '')}</div></div>")
    return "<div class='k-steps'>" + "".join(partes) + "</div>"


def color_avatar(texto: str) -> str:
    paleta = ["#FF5533", "#2A78D6", "#1BAF7A", "#6250D6", "#E87BA4", "#EDA100", "#008300", "#E34948"]
    return paleta[sum(map(ord, texto)) % len(paleta)]
