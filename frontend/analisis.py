"""Cálculos del análisis con Pandas (los mismos del notebook), en caché para la app."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from .datos import CORTE, VALIDOS, a_float, leer


def spearman(a: pd.Series, b: pd.Series) -> float:
    """Correlación de Spearman = correlación de Pearson entre los rangos.
    (Así no se necesita scipy, que pandas pide para method="spearman".)"""
    return a.rank().corr(b.rank())


@st.cache_data(ttl=3600, show_spinner="Cargando datos de MySQL…")
def base() -> dict[str, pd.DataFrame]:
    pedidos = a_float(leer(f"""
        SELECT p.id_pedido, p.id_usuario, p.fecha, p.estado, p.total, d.departamento
        FROM pedidos p JOIN usuarios u USING (id_usuario) JOIN distritos d USING (id_distrito)
        WHERE p.fecha <= '{CORTE}'"""), "total")
    detalle = a_float(leer(f"""
        SELECT d.id_pedido, d.cantidad, d.precio_unit, v.id_producto, pr.id_vendedor, pr.titulo
        FROM pedido_detalle d JOIN variantes v USING (id_variante)
        JOIN productos pr USING (id_producto) JOIN pedidos p USING (id_pedido)
        WHERE p.fecha <= '{CORTE}'"""), "precio_unit")
    detalle["importe"] = detalle["cantidad"] * detalle["precio_unit"]
    envios = a_float(leer("""SELECT e.*, c.nombre AS courier FROM envios e
                             JOIN couriers c USING (id_courier)"""), "costo_envio")
    envios["fecha_estimada"] = pd.to_datetime(envios["fecha_estimada"])
    resenas = leer("SELECT id_resena, id_producto, id_usuario, estrellas, fecha FROM resenas")
    vendedores = a_float(leer("SELECT * FROM vendedores"), "reputacion")
    validos = pedidos[pedidos["estado"].isin(VALIDOS)]
    det_validos = detalle[detalle["id_pedido"].isin(validos["id_pedido"])]
    ent = (envios.dropna(subset=["fecha_entrega"])
           .merge(pedidos[["id_pedido", "fecha", "departamento"]], on="id_pedido"))
    ent["dias_total"] = (ent["fecha_entrega"] - ent["fecha"]).dt.total_seconds() / 86400
    ent["tardio"] = ent["fecha_entrega"].dt.normalize() > ent["fecha_estimada"]
    ent["zona"] = np.where(ent["departamento"].isin(["Lima", "Callao"]), "Lima/Callao", "Provincia")
    return dict(pedidos=pedidos, validos=validos, detalle=detalle, det_validos=det_validos,
                ent=ent, resenas=resenas, vendedores=vendedores)


@st.cache_data(ttl=3600, show_spinner=False)
def kpis() -> dict:
    b = base()
    v = b["validos"]
    return dict(ventas=v["total"].sum(), pedidos=len(v), clientes=v["id_usuario"].nunique(),
                ticket=v["total"].mean(), a_tiempo=1 - b["ent"]["tardio"].mean(),
                vendedores=b["det_validos"]["id_vendedor"].nunique())


@st.cache_data(ttl=3600, show_spinner=False)
def ventas_mensuales() -> pd.DataFrame:
    v = base()["validos"].set_index("fecha")
    m = v["total"].resample("MS").sum().rename("ventas").to_frame()
    m["pedidos"] = v["id_pedido"].resample("MS").count()
    return m.reset_index()


@st.cache_data(ttl=3600, show_spinner=False)
def estacionalidad() -> pd.DataFrame:
    m = ventas_mensuales().set_index("fecha")
    diarios = m["pedidos"] / m.index.days_in_month
    indice = diarios / ((diarios.shift(1) + diarios.shift(-1)) / 2)
    picos = (indice.groupby(indice.index.month).mean() - 1).rename("variacion").reset_index()
    picos.columns = ["mes_num", "variacion"]
    picos["mes"] = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    picos["campaña"] = np.where(picos["mes_num"].isin([5, 7, 11, 12]), "Mes de campaña", "Resto")
    return picos


SEGMENTOS = {
    r"[1-2][1-2]": "Hibernando", r"[1-2][3-4]": "En riesgo", r"[1-2]5": "No se pueden perder",
    r"3[1-2]": "A punto de dormirse", r"33": "Necesitan atención", r"[3-4][4-5]": "Leales",
    r"41": "Prometedores", r"51": "Nuevos", r"[4-5][2-3]": "Potenciales leales", r"5[4-5]": "Campeones",
}


@st.cache_data(ttl=3600, show_spinner=False)
def rfm() -> tuple[pd.DataFrame, pd.DataFrame]:
    v = base()["validos"]
    r = v.groupby("id_usuario").agg(ultima=("fecha", "max"), F=("id_pedido", "count"), M=("total", "sum"))
    r["R"] = (pd.Timestamp(CORTE) - r["ultima"]).dt.days
    r["R_s"] = pd.qcut(r["R"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    r["F_s"] = pd.qcut(r["F"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    r["M_s"] = pd.qcut(r["M"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    r["segmento"] = (r["R_s"].astype(str) + r["F_s"].astype(str)).replace(SEGMENTOS, regex=True)
    res = (r.groupby("segmento").agg(clientes=("F", "size"), recencia_dias=("R", "median"),
                                     pedidos_prom=("F", "mean"), gasto_prom=("M", "mean"),
                                     ventas=("M", "sum"))
           .sort_values("ventas", ascending=False))
    res["pct_clientes"] = res["clientes"] / res["clientes"].sum()
    res["pct_ventas"] = res["ventas"] / res["ventas"].sum()
    return r.reset_index(), res.reset_index()


@st.cache_data(ttl=3600, show_spinner=False)
def cohortes(k_max: int = 12) -> pd.DataFrame:
    v = base()["validos"].assign(mes=lambda d: d["fecha"].dt.to_period("M"))
    v["cohorte"] = v.groupby("id_usuario")["mes"].transform("min")
    v["k"] = (v["mes"] - v["cohorte"]).apply(lambda d: d.n)
    act = v.groupby(["cohorte", "k"])["id_usuario"].nunique().unstack()
    ret = act.div(act[0], axis=0)
    ret = ret[(act[0] >= 100) & ret[1].notna()].loc[:, 1:k_max]
    larga = ret.stack().rename("retencion").reset_index()
    larga["cohorte"] = larga["cohorte"].astype(str)
    return larga


@st.cache_data(ttl=3600, show_spinner=False)
def pares() -> pd.DataFrame:
    b = base()
    canasta = b["det_validos"][["id_pedido", "id_producto"]].drop_duplicates()
    n = canasta["id_pedido"].nunique()
    p = canasta.merge(canasta, on="id_pedido", suffixes=("_a", "_b"))
    p = p[p["id_producto_a"] < p["id_producto_b"]]
    p = p.groupby(["id_producto_a", "id_producto_b"]).size().rename("juntos").reset_index()
    frec = canasta.groupby("id_producto").size()
    p["conf_a_b"] = p["juntos"] / p["id_producto_a"].map(frec)
    p["conf_b_a"] = p["juntos"] / p["id_producto_b"].map(frec)
    p["lift"] = p["juntos"] * n / (p["id_producto_a"].map(frec) * p["id_producto_b"].map(frec))
    titulo = b["detalle"].drop_duplicates("id_producto").set_index("id_producto")["titulo"]
    p["producto_a"] = p["id_producto_a"].map(titulo)
    p["producto_b"] = p["id_producto_b"].map(titulo)
    return p


def recomendar(id_producto: int, n: int = 3) -> pd.DataFrame:
    """'Quienes compraron esto también compraron…' (basado en co-compras históricas)."""
    p = pares()
    a = p[p["id_producto_a"] == id_producto].rename(
        columns={"id_producto_b": "id_socio", "producto_b": "titulo", "conf_a_b": "conf"})
    b = p[p["id_producto_b"] == id_producto].rename(
        columns={"id_producto_a": "id_socio", "producto_a": "titulo", "conf_b_a": "conf"})
    r = pd.concat([a, b])[["id_socio", "titulo", "juntos", "conf", "lift"]]
    return r.nlargest(n, "juntos")


@st.cache_data(ttl=3600, show_spinner=False)
def entregas() -> dict[str, pd.DataFrame]:
    e = base()["ent"]
    por_courier = (e.groupby(["courier", "zona"])
                   .agg(envios=("id_envio", "size"), dias=("dias_total", "median"),
                        tardios=("tardio", "mean"), costo=("costo_envio", "mean")).reset_index())
    celdas = (e.groupby(["courier", "departamento"])
              .agg(dias=("dias_total", "median"), envios=("id_envio", "size")).reset_index())
    celdas = celdas[celdas["envios"] >= 20]
    por_dep = (e.groupby("departamento")
               .agg(envios=("id_envio", "size"), dias=("dias_total", "median"),
                    tardios=("tardio", "mean")).reset_index().sort_values("dias", ascending=False))
    tardio_courier = e.groupby("courier")["tardio"].mean()
    return dict(por_courier=por_courier, celdas=celdas, por_dep=por_dep,
                tardio_courier=tardio_courier.rename("tardios").reset_index())


@st.cache_data(ttl=3600, show_spinner=False)
def estrellas() -> dict:
    b = base()
    ventas = b["det_validos"].groupby("id_producto").agg(ventas=("importe", "sum"),
                                                        unidades=("cantidad", "sum"))
    est = b["resenas"].groupby("id_producto").agg(estrellas=("estrellas", "mean"),
                                                 n_resenas=("id_resena", "size"))
    prod = est.join(ventas, how="inner")
    prod = prod[prod["n_resenas"] >= 5].reset_index()
    re = leer("""
        SELECT r.id_resena, r.estrellas, MAX(e.fecha_entrega) AS entrega, MAX(e.fecha_estimada) AS estimada
        FROM resenas r
        JOIN pedidos p ON p.id_usuario = r.id_usuario
        JOIN pedido_detalle d ON d.id_pedido = p.id_pedido
        JOIN variantes v ON v.id_variante = d.id_variante AND v.id_producto = r.id_producto
        JOIN envios e ON e.id_pedido = p.id_pedido
        WHERE e.fecha_entrega IS NOT NULL AND DATE(e.fecha_entrega) <= r.fecha
        GROUP BY r.id_resena, r.estrellas""")
    re["retraso"] = (re["entrega"].dt.normalize() - pd.to_datetime(re["estimada"])).dt.days
    re["tramo"] = pd.cut(re["retraso"], [-99, 0, 2, 4, 7, 99],
                         labels=["A tiempo", "1–2 días", "3–4 días", "5–7 días", "8+ días"])
    tramo = re.groupby("tramo", observed=True)["estrellas"].agg(["mean", "size"]).reset_index()
    return dict(prod=prod, tramo=tramo,
                rho_ventas=spearman(prod["estrellas"], prod["ventas"]),
                rho_retraso=spearman(re["retraso"], re["estrellas"]))


@st.cache_data(ttl=3600, show_spinner=False)
def vendedores_tardios() -> tuple[pd.DataFrame, float]:
    """Pregunta del enunciado: buenas ventas + envíos tardíos (mismo criterio que la consulta SQL 5)."""
    b = base()
    ped_vend = b["det_validos"][["id_pedido", "id_vendedor"]].drop_duplicates()
    ventas = b["det_validos"].groupby("id_vendedor")["importe"].sum().rename("ventas")
    env = (b["ent"].merge(ped_vend, on="id_pedido").groupby("id_vendedor")
           .agg(entregas=("id_envio", "size"), pct_tardios=("tardio", "mean"),
                dias=("dias_total", "median")))
    vend_prod = b["detalle"].drop_duplicates("id_producto")[["id_producto", "id_vendedor"]]
    est = (b["resenas"].merge(vend_prod).groupby("id_vendedor")["estrellas"]
           .agg(estrellas="mean", resenas="size"))
    v = (b["vendedores"].set_index("id_vendedor")[["razon_social"]]
         .join([ventas, env], how="inner").join(est))
    v["percentil"] = (v["ventas"].rank(method="min") - 1) / (len(v) - 1)
    tasa = v["pct_tardios"].mean()
    v["grupo"] = np.where((v["percentil"] >= 0.80) & (v["pct_tardios"] >= 1.5 * tasa),
                          "Buenas ventas + envíos tardíos", "Resto de vendedores")
    return v.reset_index(), tasa


def nivel_cliente(id_usuario: int) -> dict | None:
    """Segmento RFM EN VIVO de un cliente (incluye las compras hechas en la app).

    Los cortes de cada puntaje (1-5) salen de la distribución histórica de los 24 mil clientes
    (la misma del análisis). Las compras hechas en la app, posteriores al fin del dataset,
    cuentan como las más recientes (recencia 0 días).
    Si el cliente no compró nada nuevo, se devuelve exactamente su segmento del análisis.
    """
    from .tienda import pedidos_cliente
    p = pedidos_cliente(id_usuario)
    p = p[p["estado"].isin(VALIDOS)]
    if p.empty:
        return None
    hist, _ = rfm()
    corte = pd.Timestamp(CORTE)
    R = max(0, (corte - p["fecha"].max()).days)
    F, M = len(p), float(p["total"].sum())
    nuevo = (p["fecha"] > corte).any()
    fila = hist[hist["id_usuario"] == id_usuario]
    if not nuevo and len(fila):
        f = fila.iloc[0]
        return dict(R=int(f["R"]), F=int(f["F"]), M=float(f["M"]), R_s=int(f["R_s"]), F_s=int(f["F_s"]),
                    M_s=int(f["M_s"]), segmento=f["segmento"], en_vivo=False)

    def puntaje(serie, x, mayor_es_mejor=True):
        pct = (serie < x).mean() + (serie == x).mean() / 2       # percentil (rango medio en empates)
        if not mayor_es_mejor:
            pct = 1 - pct
        return min(5, int(pct * 5) + 1)

    R_s, F_s, M_s = puntaje(hist["R"], R, False), puntaje(hist["F"], F), puntaje(hist["M"], M)
    segmento = pd.Series([f"{R_s}{F_s}"]).replace(SEGMENTOS, regex=True).iat[0]
    return dict(R=R, F=F, M=M, R_s=R_s, F_s=F_s, M_s=M_s, segmento=segmento, en_vivo=True)
