Instalar LibreOffice y unoconv
RUN apt-get update && \
    apt-get install -y libreoffice unoconv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos necesarios
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exponer el puerto
EXPOSE 8000

# Comando para iniciar la aplicación
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
