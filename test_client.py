import base64
import requests
import json

# Ruta del archivo .docx que quieres codificar
docx_file_path = 'templates/informe_NESE.docx'

# Leer el archivo en binario y convertirlo a base64
with open(docx_file_path, 'rb') as file:
    encoded_template = base64.b64encode(file.read()).decode('utf-8')

# Crear el payload común
payload_old = {
    "template": encoded_template,
    "data": {
        "nombre": "Empresa XYZ",
        "fecha": "2024-10-08",
        "usuarios": [
            {"nombre": "Juan", "edad": 28, "ciudad": "Madrid"},
            {"nombre": "Ana", "edad": 22, "ciudad": "Barcelona"},
            {"nombre": "Pedro", "edad": 30, "ciudad": "Sevilla"}
        ]
    }
}

payload = {
    "template": encoded_template,
    "formato": "pdf",
    "data": {
        "alumno": {
            "nombre": "ANTONIO",
            "apellidos": "PEREZ PEREZ",
            "grupo": "2ESOC"
        },
        "medidas": [
            { "profesor": { "Id": 1, "Value": 123},
              "medida": { "Id": 1, "Value": "SIN ADAPTACION"},
              "descripcion": "<i>muy bien</i><br><ol><li>Elemento 1</li><li>Elemento 2</li></ol>"
            }
        ]
    }
}

# URL del servidor Flask
url = "http://localhost:8001/generate"
headers = {"Content-Type": "application/json"}

# Función para hacer la solicitud y guardar el archivo
def make_request_and_save(output_format):
    # Modificar el payload para el formato solicitado
    payload["formato"] = output_format
    
    # Hacer la solicitud POST al servidor Flask
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    # Verificar si la respuesta fue exitosa
    if response.status_code == 200:
        # Definir el nombre del archivo de salida
        output_filename = f'output.{output_format}'
        # Guardar el archivo descargado
        with open(output_filename, 'wb') as f:
            f.write(response.content)
        print(f"Archivo guardado como {output_filename}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)  # Para ver el mensaje de error en texto si lo hay

# Probar la generación de PDF
print("Probando generación de PDF...")
make_request_and_save("pdf")

# Probar la generación de DOCX
print("Probando generación de DOCX...")
make_request_and_save("docx")
