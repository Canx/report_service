from flask import Flask, request, send_file, jsonify
from docxtpl import DocxTemplate
import base64
import os
import tempfile
import subprocess
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

def convert_docx_to_pdf(docx_path, pdf_path):
    """Convierte un archivo DOCX a PDF usando unoconv."""
    os.environ['PYTHONPATH'] = '/usr/lib/python3/dist-packages/'
    logging.debug(f"Convirtiendo {docx_path} a {pdf_path} usando unoconv.")
    
    # Modificación: pasa la ruta de salida como argumento
    result = subprocess.run(['unoconv', '-f', 'pdf', '-o', pdf_path, docx_path], 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        logging.error(f"Error en unoconv: {result.stderr.decode()}")
        raise Exception(f"Error al convertir a PDF: {result.stderr.decode()}")

@app.route('/generate', methods=['POST'])
def generate_document():
    try:
        # Obtener el payload en formato JSON
        data = request.get_json()
        template_base64 = data.get('template')
        template_data = base64.b64decode(template_base64)

        # Usar NamedTemporaryFile para nombres de archivo únicos
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_template_file:
            temp_template_path = temp_template_file.name
            temp_template_file.write(template_data)
            logging.debug(f"Plantilla guardada en: {temp_template_path}")

        # Cargar la plantilla DOCX con docxtpl
        doc = DocxTemplate(temp_template_path)
        context = data.get('data', {})
        doc.render(context)

        # Guardar el documento rellenado en un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as filled_docx_file:
            filled_docx_path = filled_docx_file.name
            doc.save(filled_docx_path)
            logging.debug(f"Documento rellenado guardado en: {filled_docx_path}")

        # Determinar el formato de salida
        output_format = data.get('output_format', 'docx')  # Valor por defecto 'docx'
        if output_format == 'pdf':
            # Convertir el DOCX a PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output_pdf_file:
                output_pdf_path = output_pdf_file.name
                convert_docx_to_pdf(filled_docx_path, output_pdf_path)
                logging.debug(f"Documento PDF generado en: {output_pdf_path}")
                response = send_file(output_pdf_path, as_attachment=True)
                os.remove(output_pdf_path)

        else:
            # Si el formato de salida es DOCX
            logging.debug(f"Enviando archivo DOCX: {filled_docx_path}")
            response = send_file(filled_docx_path, as_attachment=True)
        
        os.remove(temp_template_path)
        os.remove(filled_docx_path)

        return response
    
    except Exception as e:
        logging.error(f"Error al generar documento: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
