#!/bin/bash

# Variables
USER="usuario"  # Cambia esto por tu nombre de usuario
WORKING_DIR="$(pwd)"  # Establece el directorio actual como WORKING_DIR
VENV_PATH="$WORKING_DIR/venv"
VENV_UNO_PATH="$WORKING_DIR/venv_uno"
GUNICORN_CMD="$VENV_PATH/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app"
SERVICE_FILE="/etc/systemd/system/mi_app.service"

# Instalar unoconv
echo "Instalando libreoffice..."
sudo add-apt-repository -y ppa:libreoffice/ppa
sudo apt update
sudo apt install -y libreoffice python3-pip python3-venv

# Crear el entorno virtual si no existe
if [ ! -d "$VENV_PATH" ]; then
    echo "Creando entorno virtual en $VENV_PATH"
    python3 -m venv --upgrade-deps "$VENV_PATH"
fi

# Instalar paquetes necesarios
if [ -f "$WORKING_DIR/requirements.txt" ]; then
    echo "Instalando paquetes desde requirements.txt"
    "$VENV_PATH/bin/pip" install -r "$WORKING_DIR/requirements.txt"
else
    echo "No se encontró requirements.txt. Asegúrate de que el archivo esté en el directorio de la aplicación."
fi

# Crear archivo de servicio systemd
echo "Creando archivo de servicio systemd en $SERVICE_FILE"
cat <<EOL | sudo tee "$SERVICE_FILE"
[Unit]
Description=Gunicorn instance to serve mi_app
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$WORKING_DIR
Environment="PATH=$VENV_PATH/bin"
ExecStart=$GUNICORN_CMD

[Install]
WantedBy=multi-user.target
EOL

# Recargar systemd y habilitar el servicio
echo "Habilitando y comenzando el servicio"
sudo systemctl daemon-reload
sudo systemctl enable mi_app
sudo systemctl start mi_app

echo "Instalación completa. Puedes verificar el estado del servicio con: sudo systemctl status mi_app"
