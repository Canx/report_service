import base64
import requests
import json

# Ruta del archivo .docx que quieres codificar
docx_file_path = 'templates/informe_NESE.docx'

# Leer el archivo en binario y convertirlo a base64
with open(docx_file_path, 'rb') as file:
    encoded_template = base64.b64encode(file.read()).decode('utf-8')


payload = {
    "template": encoded_template,
    "formato": "pdf",
    "data": {
            "alumno": {
                "apellidos": "CADENA ACEVEDO",
                "grupo": "4ESOB",
                "nombre": "SOFÍA"
            },
            "medidas": [
                {
                    "medida": {
                        "Id": 19,
                        "Value": "Ubicación en primeras filas del aula"
                    },
                    "profesor": {
                        "Id": 162,
                        "Value": "162"
                    }
                },
                {
                    "descripcion": "<div class=\"ExternalClass97F48A2DC6B2461C8F5B08701DF77EB0\"><p>Sofía ha ido evolucionando positivamente en unos aspectos aunque no en otros. Su rendimiento en el trabajo no ha sido constante y no ha entregado todos los trabajos del curso pero los que sí ha entregado, han ido mejorando en calidad. En el aula se entretiene y dispersa hablando con las compañeras. El dibujo técnico le costó de entender y realizar, causa de su nota baja en la segunda evaluación. En esta última evaluación, con trabajos más creativos, ha presentado unos trabajos de mejor ejecución.</p></div>",
                    "medida": {
                        "Id": 22,
                        "Value": "SIN ADAPTACIÓN"
                    },
                    "profesor": {
                        "Id": 154,
                        "Value": "154"
                    }
                }
            ]
        }
    }

# URL del servidor Flask
url = "http://localhost:5000/generate"
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



# Crear el payload común
# payload_old = {
#     "template": encoded_template,
#     "data": {
#         "nombre": "Empresa XYZ",
#         "fecha": "2024-10-08",
#         "usuarios": [
#             {"nombre": "Juan", "edad": 28, "ciudad": "Madrid"},
#             {"nombre": "Ana", "edad": 22, "ciudad": "Barcelona"},
#             {"nombre": "Pedro", "edad": 30, "ciudad": "Sevilla"}
#         ]
#     }
# }
