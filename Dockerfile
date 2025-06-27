# Usa una imagen oficial de Python como base
FROM python:3.10-slim

# Instala dependencias del sistema necesarias para Chrome y Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    --no-install-recommends

# Instala Google Chrome estable
RUN wget -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb

# Configura Chrome para Selenium
ENV CHROME_BIN=/usr/bin/google-chrome

# Copia archivos de tu proyecto al contenedor
COPY . /app
WORKDIR /app

# Instala dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto que Render asigna
EXPOSE $PORT

# Comando de inicio
CMD streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
