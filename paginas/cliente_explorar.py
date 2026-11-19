import streamlit as st

from frontend import tienda as t
from frontend.componentes import grilla
from frontend.estilo import RAIZ, esc

cat = t.catalogo()
ss = st.session_state
ss.setdefault("filtro_raiz", "Todas")
ss.setdefault("filtro_q", "")
ss.setdefault("ver_n", 24)

filtros, res = st.columns([1, 3.4], gap="large")

with filtros, st.container(key="panel_gris_filtros"):
    st.markdown("#### Filtros")
    raices = ["Todas"] + list(RAIZ)
    raiz = st.selectbox("Categoría", raices, index=raices.index(ss["filtro_raiz"]),
                        format_func=lambda r: r if r == "Todas" else f"{RAIZ[r][0]} {r}")
    ss["filtro_raiz"] = raiz
    sub = hoja = None
    if raiz != "Todas":
        subs = sorted(cat.loc[cat["raiz"] == raiz, "sub"].unique())
        sub = st.pills("Subcategoría", subs, key=f"sub_{raiz}")
        if sub:
            hojas = sorted(cat.loc[cat["sub"] == sub, "hoja"].unique())
            hoja = st.pills("Tipo", hojas, key=f"hoja_{sub}")
    pmax = float(cat["precio"].max())
    tope = float(round(pmax + 50, -2))
    rango = st.slider("Precio", 0.0, tope, (0.0, tope), step=10.0, format="S/ %d")
    min_est = st.select_slider("Calificación mínima", [0, 3, 3.5, 4, 4.5], value=0,
                               format_func=lambda x: "Todas" if x == 0 else f"{x}★ o más")
    solo_stock = st.toggle("Solo con stock", value=True)
    orden = st.selectbox("Ordenar por", ["Más vendidos", "Mejor calificados", "Menor precio", "Mayor precio"])

df = cat
if raiz != "Todas":
    df = df[df["raiz"] == raiz]
if sub:
    df = df[df["sub"] == sub]
if hoja:
    df = df[df["hoja"] == hoja]
q = ss.get("filtro_q", "")
if q:
    m = (df["titulo"].str.contains(q, case=False, regex=False)
         | df["hoja"].str.contains(q, case=False, regex=False)
         | df["razon_social"].str.contains(q, case=False, regex=False))
    df = df[m]
vend = ss.get("filtro_vendedor")
if vend:
    df = df[df["id_vendedor"] == vend]
df = df[df["precio"].between(*rango)]
if min_est:
    df = df[df["rating"].fillna(0) >= min_est]
if solo_stock:
    df = df[df["stock_total"] > 0]
df = {"Más vendidos": df.sort_values("vendidos", ascending=False),
      "Mejor calificados": df.assign(_r=df["rating"].fillna(0)).sort_values(["_r", "n_resenas"], ascending=False),
      "Menor precio": df.sort_values("precio"),
      "Mayor precio": df.sort_values("precio", ascending=False)}[orden]

with res:
    titulo = hoja or sub or (raiz if raiz != "Todas" else "Todos los productos")
    st.markdown(f"## {esc(titulo)}")
    chips = []
    if q:
        chips.append(("q", f"🔎 “{q}”"))
    if vend:
        chips.append(("v", "🏪 " + cat.loc[cat["id_vendedor"] == vend, "razon_social"].iat[0]))
    if chips:
        cols = st.columns(len(chips) + 3)
        for col, (k, et) in zip(cols, chips):
            if col.button(f"{et}  ✕", key=f"quitar_{k}"):
                if k == "q":
                    ss["filtro_q"] = ""
                    ss["_limpiar_q"] = True
                else:
                    ss.pop("filtro_vendedor", None)
                st.rerun()
    st.caption(f"{len(df):,} productos")
    if df.empty:
        st.info("No encontramos productos con esos filtros. Prueba con otra búsqueda o categoría.")
    else:
        grilla(df.head(ss["ver_n"]), "exp", columnas=3)
        if len(df) > ss["ver_n"]:
            if st.button("Mostrar más productos", width="stretch"):
                ss["ver_n"] += 24
                st.rerun()
