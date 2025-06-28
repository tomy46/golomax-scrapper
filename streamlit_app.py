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

    try:
        df_in = pd.read_csv(uploaded_file, encoding="utf-8")
    except Exception as e:
        st.error(f"❌ Error al leer el archivo CSV: {e}")
        st.stop()

    df_in.columns = df_in.columns.str.strip()

    # Si las columnas esperadas no están, intenta renombrar las dos primeras
    if not set(["Cantidad", "Nombre"]).issubset(df_in.columns):
        if len(df_in.columns) >= 2:
            old0, old1 = df_in.columns[0], df_in.columns[1]
            df_in = df_in.rename(columns={old0: "Cantidad", old1: "Nombre"})
        else:
            st.error(
                "❌ El archivo debe contener al menos dos columnas: 'Cantidad' y 'Nombre'."
            )
            st.stop()

    # Chequea que las columnas finales existan
    if not set(["Cantidad", "Nombre"]).issubset(df_in.columns):
        st.error(
            "❌ El archivo debe contener las columnas 'Cantidad' y 'Nombre'. Verificá el CSV."
        )
        st.stop()

    # Elimina filas con datos faltantes en las columnas clave
    df_in = df_in.dropna(subset=["Cantidad", "Nombre"])

    progress_placeholder = st.empty()  # Muestra la tabla parcial
    logs_placeholder = st.empty()  # Muestra mensajes de progreso y errores

    driver = init_driver()
    resultados = []

    try:
        for idx, row in df_in.iterrows():
            try:
                pedido = int(row["Cantidad"])
            except (ValueError, TypeError):
                logs_placeholder.warning(
                    f"❌ Cantidad inválida en '{row['Nombre']}': {row['Cantidad']}"
                )
                continue  # Saltea esta fila y sigue con la siguiente

            termino = str(row["Nombre"]).strip()
            try:
                nombre, precio_txt, precio_val, min_qty, link = scrape_best_product(
                    driver, termino)
                logs_placeholder.info(f"✅ Producto encontrado: {nombre}")
            except Exception as e:
                nombre, precio_txt, precio_val, min_qty, link = termino, "", 0.0, pedido, ""
                logs_placeholder.warning(f"❌ Error buscando '{termino}': {e}")

            qty_used = max(min_qty,
                           ((pedido + min_qty - 1) // min_qty) * min_qty)
            total = qty_used * precio_val

            # 🚀 Formatea precios al estilo argentino: 1.234,56
            total_formatted = f"{total:,.2f}".replace(",", "X").replace(
                ".", ",").replace("X", ".")

            resultados.append({
                "Cantidad pedida": pedido,
                "Cantidad mínima": min_qty,
                "Cantidad ajustada": qty_used,
                "Nombre": nombre,
                "Precio unitario": precio_txt,
                "Precio total": total_formatted,
                "Link": link
            })

            # Actualiza la tabla parcial en cada iteración
            df_partial = pd.DataFrame(resultados)
            progress_placeholder.dataframe(df_partial)

            # 🚨 Cada 20 productos reinicia el driver para liberar memoria
            if idx > 0 and idx % 20 == 0:
                driver.quit()
                driver = init_driver()
                logs_placeholder.info(
                    "♻️ Reiniciando navegador para liberar memoria...")

    finally:
        driver.quit()

    if resultados:
        df_out = pd.DataFrame(resultados)
        st.success(
            f"✅ Procesamiento finalizado. {len(df_out)} filas procesadas.")

        with tempfile.NamedTemporaryFile(delete=False,
                                         suffix=".csv") as tmpfile:
            df_out.to_csv(tmpfile.name, index=False, encoding="utf-8-sig")
            tmpfile.flush()
            tmp_path = tmpfile.name

        with open(tmp_path, "rb") as f:
            st.download_button(label="⬇️ Descargar archivo CSV modificado",
                               data=f,
                               file_name="output.csv",
                               mime="text/csv")

        os.remove(tmp_path)
    else:
        st.warning("⚠️ No se procesaron filas válidas. Revisá tu archivo CSV.")
