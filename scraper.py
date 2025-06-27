import time
import re
import unicodedata
from difflib import SequenceMatcher
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Convierte texto a slug URL-friendly
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
    text = text.strip().lower()
    return re.sub(r"\s+", "-", text)


# Inicializa el driver de Selenium en modo headless optimizado
def init_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--blink-settings=imagesEnabled=false")  # 🚀 desactiva imágenes
    opts.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/102.0.0.0 Safari/537.36"
    )
    service = Service()
    return webdriver.Chrome(service=service, options=opts)


# Calcula similitud entre dos textos usando SequenceMatcher
def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# Busca el producto más parecido a search_term y devuelve sus datos, incluyendo cantidad mínima disponible
def scrape_best_product(driver, search_term: str):
    driver.get(f"https://www.golomax.com.ar/catalogo/buscar?search_text={search_term}")

    # Espera a que cargue al menos un precio con atributo content
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.precio-unitario[content]"))
    )

    # 🚀 En vez de hacer scroll infinito, solo espera un momento para la carga inicial
    time.sleep(2)  # ajusta este valor si hace falta más/menos tiempo

    # Recolecta todos los bloques de producto
    bloques = driver.find_elements(By.CSS_SELECTOR, "div.block-producto")
    if not bloques:
        raise Exception(f"No se encontraron productos para '{search_term}'")  # 🚨 marca error si no hay resultados

    candidates = []
    for b in bloques:
        # Nombre
        nombre = b.find_element(By.CSS_SELECTOR, "h3[itemprop='name']").text.strip()
        # Precio formateado y valor float
        precio_txt = b.find_element(By.CSS_SELECTOR, "div.precio-unitario[content]").text.strip()
        precio_val = float(
            b.find_element(By.CSS_SELECTOR, "div.precio-unitario[content]").get_attribute("content").strip()
        )
        # Extrae cantidad mínima del input
        try:
            min_input = b.find_element(By.CSS_SELECTOR, "div.meta-cart input.quantity")
            min_qty = int(min_input.get_attribute("value") or min_input.get_attribute("min") or 1)
        except:
            min_qty = 1

        # Construcción de link
        typeid = b.get_attribute("typeid") or "0"
        img_src = b.find_element(By.CSS_SELECTOR, "div.image img").get_attribute("src")
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
    best = sorted(candidates, key=lambda x: (-x['score'], x['nombre'].lower()))[0]

    return best['nombre'], best['precio_txt'], best['precio_val'], best['min_qty'], best['link']
