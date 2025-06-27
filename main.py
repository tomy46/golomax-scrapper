import time
import re
import unicodedata
import pandas as pd
from difflib import SequenceMatcher
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Convierte texto a slug URL-friendly
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii",
                                                      "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
    text = text.strip().lower()
    return re.sub(r"\s+", "-", text)


# Inicializa el driver de Selenium en modo headless
def init_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    service = Service()
    return webdriver.Chrome(service=service, options=opts)


# Calcula similitud entre dos textos usando SequenceMatcher
def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# Busca el producto más parecido a search_term y devuelve sus datos, incluyendo cantidad mínima disponible
def scrape_best_product(driver, search_term: str):
    driver.get(
        f"https://www.golomax.com.ar/catalogo/buscar?search_text={search_term}"
    )

    # Espera a que cargue al menos un precio con atributo content
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.precio-unitario[content]")))

    # Scrolleo infinito para carga dinámica
    last_h = driver.execute_script("return document.body.scrollHeight")
    same = 0
    while same < 2:
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            same += 1
        else:
            last_h = new_h
            same = 0

    # Recolecta todos los bloques de producto
    bloques = driver.find_elements(By.CSS_SELECTOR, "div.block-producto")
    candidates = []
    for b in bloques:
        # Nombre
        nombre = b.find_element(By.CSS_SELECTOR,
                                "h3[itemprop='name']").text.strip()
        # Precio formateado y valor float
        precio_txt = b.find_element(
            By.CSS_SELECTOR, "div.precio-unitario[content]").text.strip()
        precio_val = float(
            b.find_element(By.CSS_SELECTOR,
                           "div.precio-unitario[content]").get_attribute(
                               "content").strip())
        # Extrae cantidad mínima del input
        try:
            min_input = b.find_element(By.CSS_SELECTOR,
                                       "div.meta-cart input.quantity")
            min_qty = int(
                min_input.get_attribute("value")
                or min_input.get_attribute("min") or 1)
        except:
            min_qty = 1

        # Construcción de link
        typeid = b.get_attribute("typeid") or "0"
        img_src = b.find_element(By.CSS_SELECTOR,
                                 "div.image img").get_attribute("src")
        article_id = img_src.rsplit("/", 1)[-1].split("_")[0]
        slug = slugify(nombre)
        link = f"https://www.golomax.com.ar/catalogo/detalle/{typeid}-{article_id}-{slug}"
        # Similitud con término de búsqueda
        score = similarity(nombre, search_term)
        candidates.append({
            "nombre": nombre,
            "precio_txt": precio_txt,
            "precio_val": precio_val,
            "min_qty": min_qty,
            "link": link,
            "score": score
        })

    # Ordena por similitud descendente y luego alfabéticamente ascendente
    best = sorted(candidates, key=lambda x:
                  (-x['score'], x['nombre'].lower()))[0]

    return best['nombre'], best['precio_txt'], best['precio_val'], best[
        'min_qty'], best['link']


# Flujo principal
def main():
    # Lee input.csv y normaliza nombres de columnas
    df_in = pd.read_csv("input.csv")
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
                print(f"❌ No encontrado '{termino}': {e}")
                nombre, precio_txt, precio_val, min_qty, link = termino, "", 0.0, pedido, ""

            # ajusta cantidad: mínimo o múltiplo de éste
            if pedido <= min_qty:
                qty_used = min_qty
            else:
                # rounds up al siguiente múltiplo de min_qty
                multiples = (pedido + min_qty - 1) // min_qty
                qty_used = multiples * min_qty

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

    # Guarda output.csv con columnas final
    df_out = pd.DataFrame(resultados)
    df_out.to_csv("output.csv", index=False, encoding="utf-8-sig")
    print(f"✅ Generado output.csv con {len(df_out)} filas.")


if __name__ == "__main__":
    main()
