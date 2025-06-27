import streamlit as st
import pandas as pd
import tempfile
import os
from scraper import init_driver, scrape_best_product

st.title("🛒 Actualizador de Precios Golomax")

uploaded_file = st.file_uploader("📤 Sube tu archivo CSV de productos",
                                 type=["csv"])

if uploaded_file:
    st.info(
        "Procesando archivo... puede tardar unos minutos según la cantidad de productos."
    )
    df_in = pd.read_csv(uploaded_file)
    df_in.columns = df_in.columns.str.strip()
    if not set(["Cantidad", "Nombre"]).issubset(df_in.columns):
        old0, old1 = df_in.columns[0], df_in.columns[1]
        df_in = df_in.rename(columns={old0: "Cantidad", old1: "Nombre"})

    driver = init_driver()
    resultados = []

    try:
        for _, row in df_in.iterrows():
            pedido = row["Cantidad"]
            termino = row["Nombre"]
            try:
                nombre, precio_txt, precio_val, min_qty, link = scrape_best_product(
                    driver, termino)
            except Exception as e:
                nombre, precio_txt, precio_val, min_qty, link = termino, "", 0.0, pedido, ""

            qty_used = max(min_qty,
                           ((pedido + min_qty - 1) // min_qty) * min_qty)
            total = round(qty_used * precio_val, 2)
            resultados.append({
                "Cantidad pedida": pedido,
                "Cantidad mínima": min_qty,
                "Cantidad ajustada": qty_used,
                "Nombre": nombre,
                "Precio unitario": precio_txt,
                "Precio total": total,
                "Link": link
            })
    finally:
        driver.quit()

    df_out = pd.DataFrame(resultados)
    st.success(f"✅ Procesamiento finalizado. {len(df_out)} filas procesadas.")
    st.dataframe(df_out)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmpfile:
        df_out.to_csv(tmpfile.name, index=False, encoding="utf-8-sig")
        tmpfile.flush()
        tmp_path = tmpfile.name

    with open(tmp_path, "rb") as f:
        st.download_button(label="⬇️ Descargar archivo CSV modificado",
                           data=f,
                           file_name="output.csv",
                           mime="text/csv")

    os.remove(tmp_path)
