import altair as alt
import streamlit as st

from frontend.datos import arbol_categorias, niveles_stock, stock_critico
from frontend.graficos import mostrar, nota, tarjeta

st.markdown("## Catálogo y stock")
tab_cat, tab_stock = st.tabs(["Categorías (WITH RECURSIVE)", "Stock crítico"])

with tab_cat:
    arbol = arbol_categorias()
    raices = arbol[arbol["nivel"] == 1].sort_values("ventas", ascending=False)
    raiz = st.selectbox("Categoría principal", raices["id_categoria"].tolist(),
                        format_func=dict(zip(raices["id_categoria"], raices["nombre"])).get)
    nombre_raiz = raices.set_index("id_categoria").loc[raiz, "nombre"]
    rama = arbol[arbol["ruta"].str.startswith(nombre_raiz + " >") | (arbol["id_categoria"] == raiz)]
    hojas = rama[rama["nivel"] == 3].copy()
    hojas["subcategoria"] = hojas["ruta"].str.split(" > ").str[1]

    i, d = st.columns([1, 1], gap="large")
    with i:
        graf = (alt.Chart(hojas, title=f"{nombre_raiz}: ventas por subcategoría y hoja")
                .mark_bar(cornerRadiusEnd=3, height=12)
                .encode(y=alt.Y("nombre:N", sort="-x", title=None),
                        x=alt.X("ventas:Q", title="Soles", axis=alt.Axis(format="~s")),
                        color=alt.Color("subcategoria:N", title="Subcategoría",
                                        scale=alt.Scale(range=["#2a78d6", "#eb6834", "#1baf7a"])),
                        tooltip=[alt.Tooltip("ruta:N", title="Ruta"),
                                 alt.Tooltip("ventas:Q", title="Ventas", format=",.0f"),
                                 alt.Tooltip("unidades:Q", title="Unidades", format=",")]))
        mostrar(graf, 300)
    with d:
        tabla = rama.copy()
        tabla["categoría"] = tabla.apply(lambda r: " " * (r["nivel"] - 1) + r["nombre"], axis=1)
        st.dataframe(tabla[["categoría", "ventas", "unidades"]], hide_index=True, height=340,
                     column_config={"categoría": st.column_config.TextColumn("Categoría", width="medium"),
                                    "ventas": st.column_config.NumberColumn("Ventas (acum.)", format="S/ %,.0f"),
                                    "unidades": st.column_config.NumberColumn("Unidades", format="%,d")})
    nota("El árbol tiene 3 niveles (raíz → subcategoría → hoja) guardados en una sola tabla con "
         "<code>id_padre</code>. Una <b>CTE recursiva</b> recorre el árbol y suma a cada categoría las "
         "ventas de todas sus descendientes.")
    with st.expander("Ver la consulta SQL (WITH RECURSIVE)"):
        st.code("""WITH RECURSIVE arbol AS (
    SELECT id_categoria, id_padre, nombre, 1 AS nivel, CAST(nombre AS CHAR(300)) AS ruta
    FROM categorias WHERE id_padre IS NULL              -- caso base: raíces
    UNION ALL
    SELECT c.id_categoria, c.id_padre, c.nombre, a.nivel + 1, CONCAT(a.ruta, ' > ', c.nombre)
    FROM categorias c JOIN arbol a ON c.id_padre = a.id_categoria   -- paso recursivo
)
SELECT nivel, ruta FROM arbol ORDER BY ruta;""", language="sql")

with tab_stock:
    niv = niveles_stock().set_index("nivel")["variantes"]
    total = niv.sum()
    c = st.columns(4)
    for col, n in zip(c, ["Agotado (0)", "Crítico (1-3)", "Bajo (4-10)", "Normal (>10)"]):
        tarjeta(col, n, f"{niv.get(n, 0):,}", f"{niv.get(n, 0) / total:.1%} de las variantes")

    sc = stock_critico()
    f1, f2, f3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    vend = f1.text_input("Filtrar por vendedor", placeholder="ej. Importaciones Norte")
    prod = f2.text_input("Filtrar por producto o categoría", placeholder="ej. pañales")
    solo_agot = f3.toggle("Solo agotados")
    if vend:
        sc = sc[sc["vendedor"].str.contains(vend, case=False)]
    if prod:
        sc = sc[sc["titulo"].str.contains(prod, case=False) | sc["categoria"].str.contains(prod, case=False)]
    if solo_agot:
        sc = sc[sc["stock"] == 0]
    st.caption(f"{len(sc):,} variantes · ordenadas por demanda de los últimos 90 días "
               "(las más urgentes arriba)")
    st.dataframe(sc, hide_index=True, height=420, column_config={
        "id_variante": "Variante", "titulo": "Producto", "talla": "Talla", "color": "Color",
        "stock": st.column_config.NumberColumn("Stock", format="%d"),
        "vendidas_90d": st.column_config.ProgressColumn("Vendidas (90 días)", format="%d", min_value=0,
                                                        max_value=int(max(sc["vendidas_90d"].max(), 1))
                                                        if len(sc) else 1),
        "vendedor": "Vendedor", "categoria": "Categoría"})
    nota("Una variante agotada que se vende mucho es más urgente que una que nadie compra. "
         "El stock baja en vivo cuando se paga un pedido (procedimiento <code>sp_confirmar_pedido</code>).")
