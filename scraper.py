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


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii",
                                                      "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
    text = text.strip().lower()
    return re.sub(r"\s+", "-", text)


def init_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    service = Service()
    return webdriver.Chrome(service=service, options=opts)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def scrape_best_product(driver, search_term: str):
    driver.get(
        f"https://www.golomax.com.ar/catalogo/buscar?search_text={search_term}"
    )
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.precio-unitario[content]")))
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
    bloques = driver.find_elements(By.CSS_SELECTOR, "div.block-producto")
    candidates = []
    for b in bloques:
        nombre = b.find_element(By.CSS_SELECTOR,
                                "h3[itemprop='name']").text.strip()
        precio_txt = b.find_element(
            By.CSS_SELECTOR, "div.precio-unitario[content]").text.strip()
        precio_val = float(
            b.find_element(By.CSS_SELECTOR,
                           "div.precio-unitario[content]").get_attribute(
                               "content").strip())
        try:
            min_input = b.find_element(By.CSS_SELECTOR,
                                       "div.meta-cart input.quantity")
            min_qty = int(
                min_input.get_attribute("value")
                or min_input.get_attribute("min") or 1)
        except:
            min_qty = 1
        typeid = b.get_attribute("typeid") or "0"
        img_src = b.find_element(By.CSS_SELECTOR,
                                 "div.image img").get_attribute("src")
        article_id = img_src.rsplit("/", 1)[-1].split("_")[0]
        slug = slugify(nombre)
        link = f"https://www.golomax.com.ar/catalogo/detalle/{typeid}-{article_id}-{slug}"
        score = similarity(nombre, search_term)
        candidates.append({
            "nombre": nombre,
            "precio_txt": precio_txt,
            "precio_val": precio_val,
            "min_qty": min_qty,
            "link": link,
            "score": score
        })
    best = sorted(candidates, key=lambda x:
                  (-x['score'], x['nombre'].lower()))[0]
    return best['nombre'], best['precio_txt'], best['precio_val'], best[
        'min_qty'], best['link']
