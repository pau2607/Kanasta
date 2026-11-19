"""Estilo común de los gráficos (Altair) y pequeñas utilidades de presentación."""
from __future__ import annotations

import altair as alt
import streamlit as st

AZUL, AZUL_CLARO, NARANJA, AQUA = "#2a78d6", "#9ec5f4", "#eb6834", "#1baf7a"
TEXTO, TEXTO_2, GRILLA, BORDE = "#0b0b0b", "#52514e", "#e6e5e1", "#c3c2b7"
AZULES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

ESTADO_COLOR = {"pendiente": "#8a8984", "pagado": AZUL, "enviado": "#6250d6",
                "entregado": "#0ca30c", "cancelado": "#d03b3b"}
ESTADO_ICONO = {"pendiente": "🕓", "pagado": "💳", "enviado": "🚚", "entregado": "✅", "cancelado": "✖️"}


def mostrar(chart: alt.Chart, alto: int | None = None):
    """Aplica el estilo del proyecto y dibuja el gráfico a todo el ancho."""
    if alto:
        chart = chart.properties(height=alto)
    chart = (chart.configure(background="transparent", font="Inter, Segoe UI, sans-serif")
             .configure_axis(labelColor=TEXTO_2, titleColor=TEXTO_2, gridColor=GRILLA,
                                  domainColor=BORDE, tickColor=BORDE, labelFontSize=11,
                                  titleFontSize=11, titleFontWeight="normal", labelLimit=220)
             .configure_view(stroke=None)
             .configure_title(anchor="start", fontSize=14, color=TEXTO, fontWeight="bold")
             .configure_legend(labelColor=TEXTO_2, titleColor=TEXTO_2, orient="top",
                               labelFontSize=11, titleFontSize=11))
    st.altair_chart(chart, width="stretch", theme=None)


# Etiquetas de fecha en español para ejes temporales de Altair
MES_AXIS = ("['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']"
            "[month(datum.value)] + ' ' + year(datum.value)")


def soles(x: float, decimales: int = 0) -> str:
    if abs(x) >= 1e6:
        return f"S/ {x / 1e6:,.1f} M"
    return f"S/ {x:,.{decimales}f}"


def chip_estado(estado: str) -> str:
    """Etiqueta de color para un estado (HTML)."""
    c = ESTADO_COLOR.get(estado, TEXTO_2)
    return (f"<span style='background:{c}1f;color:{c};border:1px solid {c}55;border-radius:999px;"
            f"padding:2px 10px;font-size:0.85rem;font-weight:600'>{ESTADO_ICONO.get(estado, '')} "
            f"{estado}</span>")


def tarjeta(col, etiqueta: str, valor: str, detalle: str | None = None):
    """Indicador con borde y, opcionalmente, una línea de contexto (sin flechas de variación)."""
    with col.container(border=True):
        st.metric(etiqueta, valor)
        if detalle:
            st.caption(detalle)


def pct100(df, *cols):
    """Copia con columnas 0–1 pasadas a 0–100 (para mostrar con formato '%.1f %%')."""
    df = df.copy()
    for c in cols:
        df[c] = df[c] * 100
    return df


PCT = "%.1f %%"


def nota(texto: str):
    """Recuadro de lectura / conclusión."""
    st.markdown(f"<div class='nota'>{texto}</div>", unsafe_allow_html=True)


CSS = f"""
<style>
.block-container {{ padding-top: 2.2rem; max-width: 1200px; }}
h1 {{ letter-spacing: -0.02em; }}
.nota {{ background:#f3f7fd; border-left:3px solid {AZUL}; padding:0.7rem 0.9rem;
         border-radius:6px; color:{TEXTO}; font-size:0.93rem; margin:0.4rem 0 1rem 0; }}
.patron {{ display:inline-block; background:#f2f1ee; color:{TEXTO_2}; border-radius:6px;
           padding:1px 8px; font-size:0.78rem; font-weight:600; margin-left:6px;
           vertical-align:middle; letter-spacing:0.02em; }}
.boleta td {{ padding: 2px 6px; }}
div[data-testid="stMetricValue"] {{ font-size: 1.6rem; }}
</style>
"""


def patron(nombre: str) -> str:
    """Etiqueta pequeña para indicar qué patrón de diseño se usa en una sección."""
    return f"<span class='patron'>{nombre}</span>"
