import base64
import os
from flask import Flask, request, jsonify, send_file
from io import BytesIO
from docxtpl import DocxTemplate
import tempfile

app = Flask(__name__)

# Endpoint para generar PDF o DOCX
@app.route('/generate', methods=['POST'])
def generate_document():
    try:
        # Obtener el payload en formato JSON
        data = request.get_json()

        # Decodificar la plantilla base64
        template_base64 = data.get('template')
        template_data = base64.b64decode(template_base64)

        # Guardar la plantilla temporalmente en un archivo
        temp_template_path = os.path.join(tempfile.gettempdir(), 'template.docx')
        with open(temp_template_path, 'wb') as template_file:
            template_file.write(template_data)

        # Cargar la plantilla DOCX
        doc = DocxTemplate(temp_template_path)

        # Rellenar la plantilla con los datos del JSON
        context = data.get('data', {})
        doc.render(context)

        # Guardar el archivo completado en formato DOCX temporalmente
        output_format = data.get('output_format', 'docx')
        output_file_path = os.path.join(tempfile.gettempdir(), f'output.{output_format}')

        if output_format == 'docx':
            doc.save(output_file_path)
        elif output_format == 'pdf':
            # Si el formato solicitado es PDF, se debería convertir el DOCX a PDF
            # Aquí puedes utilizar una librería como `pdfkit` o cualquier otra para convertir el DOCX a PDF.
            doc.save(output_file_path)  # Placeholder para conversión a PDF

        # Leer el archivo generado
        return send_file(output_file_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ejecutar el servidor en modo desarrollo
if __name__ == '__main__':
    app.run(debug=True)
