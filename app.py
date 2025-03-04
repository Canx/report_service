from flask import Flask, request, send_file, jsonify
from docxtpl import DocxTemplate, RichText
from jinja2 import Environment, BaseLoader
import tempfile
from html4docx.h4d import HtmlToDocx
from bs4 import BeautifulSoup
import base64
import os
import tempfile
import subprocess
import logging
import re


logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)



def looks_like_html(text):
    """
    Comprueba si la cadena parece contener etiquetas HTML.
    """
    return bool(re.search(r'<[^>]+>', text))

def html_to_docx(html, tpl):
    """
    Convierte una cadena HTML en un subdocumento DOCX usando html-for-docx y lo
    carga en la plantilla tpl.
    """
    parser = HtmlToDocx()
    # Convertir la cadena HTML a un objeto Document
    document = parser.parse_html_string(html)
    
    # Guardar el documento en un archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp_path = tmp.name
    document.save(tmp_path)
    
    #subdoc2 = tpl.new_subdoc("test.docx")
    # Crear el subdocumento a partir del archivo generado
    subdoc = tpl.new_subdoc(tmp_path)
    
    return subdoc

def process_context(context, tpl):
    """
    Recorre recursivamente el contexto y, si encuentra una cadena que parece HTML,
    la reemplaza por el objeto subdocumento generado.
    
    Esta función revisa:
      - Si context es un diccionario, recorre sus claves.
      - Si context es una lista, recorre cada elemento.
      - Si se encuentra un objeto que sea diccionario o lista anidada, se llama a la función de forma recursiva.
    """
    if isinstance(context, dict):
        for key, value in context.items():
            if isinstance(value, str) and looks_like_html(value):
                context[key] = html_to_docx(value, tpl)
            elif isinstance(value, (dict, list)):
                process_context(value, tpl)
    elif isinstance(context, list):
        for i, item in enumerate(context):
            if isinstance(item, str) and looks_like_html(item):
                context[i] = html_to_docx(item, tpl)
            elif isinstance(item, (dict, list)):
                process_context(item, tpl)



def html_to_richtext(html):
    soup = BeautifulSoup(html, 'html.parser')
    rt = RichText()

    def process_element(elem, indent=0):
        # Si el elemento es un string, lo agregamos con la indentación actual
        if isinstance(elem, str):
            text = elem.strip()
            if text:
                rt.add(" " * indent + text)
            return
        
        # Procesar etiquetas de formato simples
        if elem.name in ['b', 'strong']:
            rt.add(" " * indent + elem.get_text(), bold=True)
        elif elem.name in ['i', 'em']:
            rt.add(" " * indent + elem.get_text(), italic=True)
        # Procesar listas ordenadas y desordenadas
        elif elem.name in ['ul', 'ol']:
            is_ordered = (elem.name == 'ol')
            # Iterar solo sobre elementos <li> hijos directos
            for i, li in enumerate(elem.find_all('li', recursive=False), start=1):
                # Para listas ordenadas se usa el número, para desordenadas una viñeta
                bullet = f"{i}. " if is_ordered else "• "
                # Agregamos un salto de línea para separar cada elemento de lista
                rt.add("\n" + " " * indent + bullet)
                # Procesamos el contenido de cada <li> aumentando la indentación
                for child in li.contents:
                    process_element(child, indent=indent + 4)
        else:
            # Para otros elementos genéricos, procesamos sus hijos de forma recursiva
            for child in elem.contents:
                process_element(child, indent=indent)

    # Procesar cada elemento de nivel superior del HTML
    for element in soup.contents:
        process_element(element)
    
    return rt



def convert_docx_to_pdf(docx_path, pdf_path):
    """Convierte un archivo DOCX a PDF usando unoconv."""
    try:
        os.environ['PYTHONPATH'] = '/usr/lib/python3/dist-packages/'
        logging.debug(f"Convirtiendo {docx_path} a {pdf_path} usando unoconvert.")
        
        # Modificación: pasa la ruta de salida como argumento
        result = subprocess.run(['unoconvert', '--convert-to', 'pdf', docx_path, pdf_path], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            logging.error(f"Error en unoconv: {result.stderr.decode()}")
            raise Exception(f"Error al convertir a PDF: {result.stderr.decode()}")
    except Exception as e:
        logging.error(f"Excepción durante la conversión a PDF: {str(e)}")
        raise e

@app.route('/generate', methods=['POST'])
def generate_document():
    try:
        # Obtener el payload en formato JSON
        data = request.get_json()

        # Verificar si la clave 'template' está presente
        if 'template' not in data:
            return jsonify({"error": "Falta la clave 'template' en el cuerpo de la solicitud."}), 400

        # Verificar si la clave 'data' está presente
        if 'data' not in data:
            return jsonify({"error": "Falta la clave 'data' en el cuerpo de la solicitud."}), 400

        # Decodificar la plantilla base64
        try:
            template_base64 = data.get('template')
            template_data = base64.b64decode(template_base64)
        except (TypeError, ValueError):
            return jsonify({"error": "La plantilla no está correctamente codificada en base64."}), 400

        # Usar NamedTemporaryFile para nombres de archivo únicos
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_template_file:
            temp_template_path = temp_template_file.name
            temp_template_file.write(template_data)
            logging.debug(f"Plantilla guardada en: {temp_template_path}")

        # Cargar la plantilla DOCX con docxtpl
        try:
            
            doc = DocxTemplate(temp_template_path)
        except Exception as e:
            logging.error(f"Error al cargar la plantilla: {str(e)}")
            return jsonify({"error": "No se pudo cargar la plantilla DOCX."}), 400
        
        # Rellenar la plantilla con los datos proporcionados
        context = data.get('data', {})
        try:
            #env = Environment(loader=BaseLoader(), autoescape=False)
            #env.filters['html2richtext'] = html_to_richtext
            #env.filters['html2docx'] = lambda html: html_to_docx(html, doc)
            process_context(context, doc)
            doc.render(context) #p, jinja_env=env)

        except Exception as e:
            logging.error(f"Error al renderizar la plantilla: {str(e)}")
            return jsonify({"error": "Error al renderizar la plantilla con los datos proporcionados."}), 400

        # Guardar el documento rellenado en un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as filled_docx_file:
            filled_docx_path = filled_docx_file.name
            doc.save(filled_docx_path)
            logging.debug(f"Documento rellenado guardado en: {filled_docx_path}")

        # Determinar el formato de salida
        output_format = data.get('formato', 'docx')  # Valor por defecto 'docx'
        if output_format not in ['docx', 'pdf']:
            return jsonify({"error": "Formato no soportado. Los formatos permitidos son 'docx' y 'pdf'."}), 400

        # Si el formato es PDF, convertir el DOCX a PDF
        if output_format == 'pdf':
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as output_pdf_file:
                output_pdf_path = output_pdf_file.name
                try:
                    convert_docx_to_pdf(filled_docx_path, output_pdf_path)
                    logging.debug(f"Documento PDF generado en: {output_pdf_path}")
                    response = send_file(output_pdf_path, as_attachment=True)
                finally:
                    os.remove(output_pdf_path)  # Limpiar siempre, incluso en caso de error
        else:
            # Si el formato de salida es DOCX
            logging.debug(f"Enviando archivo DOCX: {filled_docx_path}")
            response = send_file(filled_docx_path, as_attachment=True)
        
        #os.remove(temp_template_path)
        #os.remove(filled_docx_path)

        return response
    
    except Exception as e:
        logging.error(f"Error al generar documento: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
