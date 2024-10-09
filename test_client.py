import base64
import requests
import json

# Ruta del archivo .docx que quieres codificar
docx_file_path = 'templates/example1.docx'

# Leer el archivo en binario y convertirlo a base64
with open(docx_file_path, 'rb') as file:
    encoded_template = base64.b64encode(file.read()).decode('utf-8')

# Crear el payload JSON
payload = {
    "template": encoded_template,
    "data": {
        "nombre": "Empresa XYZ",
        "fecha": "2024-10-08",
        "usuarios": [
        {"nombre": "Juan", "edad": 28, "ciudad": "Madrid"},
        {"nombre": "Ana", "edad": 22, "ciudad": "Barcelona"},
        {"nombre": "Pedro", "edad": 30, "ciudad": "Sevilla"}
        ]
    },
    "output_format": "pdf"
}

# Hacer la solicitud POST al servidor Flask
url = "http://localhost:5000/generate"
headers = {"Content-Type": "application/json"}

response = requests.post(url, headers=headers, data=json.dumps(payload))

# Verificar si la respuesta fue exitosa
if response.status_code == 200:
    # Guardar el archivo descargado
    output_filename = 'output.pdf'  # Cambia a 'output.pdf' si es el formato solicitado
    with open(output_filename, 'wb') as f:
        f.write(response.content)
    print(f"Archivo guardado como {output_filename}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)  # Para ver el mensaje de error en texto si lo hay