from flask import Flask, request, send_file, jsonify
from docxtpl import DocxTemplate, RichText
import tempfile
from bs4 import BeautifulSoup
import base64
import os
import tempfile
import subprocess
import logging
import re
import time
import subprocess
import unicodedata
import json


logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)


def save_json_for_debugging(context, filename="debug_context.json"):
    """
    Guarda el JSON del contexto en un archivo para análisis posterior.
    """
    debug_path = os.path.join("/tmp", filename)  # Ruta en /tmp (cámbiala si es necesario)
                       
    try:
        with open(debug_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=4, ensure_ascii=False)
            logging.debug(f"Contexto guardado para análisis en: {debug_path}")
    except Exception as e:
        logging.error(f"Error al guardar el JSON de depuración: {str(e)}")


def clean_context_html(context):
    """
    Recorre recursivamente el contexto y, si encuentra una cadena que parece HTML,
    la reemplaza por la versión limpia obtenida con clean_html.
    """
    if isinstance(context, dict):
        new_context = {}
        for key, value in context.items():
            if isinstance(value, str) and looks_like_html(value):
                logging.debug(f"Limpieza HTML en {key}")
                new_context[key] = clean_html(value)
            elif isinstance(value, (dict, list)):
                new_context[key] = clean_context_html(value)
            else:
                new_context[key] = value
        return new_context
    elif isinstance(context, list):
        new_list = []
        for item in context:
            if isinstance(item, str) and looks_like_html(item):
                new_list.append(clean_html(item))
            elif isinstance(item, (dict, list)):
                new_list.append(clean_context_html(item))
            else:
                new_list.append(item)
        return new_list
    return context


def clean_html(html):
    """
    Limpia el HTML antes de la conversión a DOCX:
      - Decodifica entidades.
      - Elimina atributos innecesarios (style, dir).
      - Desanida etiquetas <span> sin atributos.
      - Elimina elementos vacíos.
      - Desenvuelve contenedores problemáticos (div con ExternalClass y <tbody>).
      - Simplifica la estructura de las tablas desanidando <p> dentro de <td>.
    """
    try:
        # Decodificar entidades comunes
        html = html.replace("&#58;", ":").replace("&#160;", " ")
        soup = BeautifulSoup(html, "html.parser")

        # Desenvolver <div> con clases tipo ExternalClass
        for div in soup.find_all("div", class_=re.compile(r"ExternalClass")):
            div.unwrap()

        # Eliminar atributos 'style' y 'dir'
        for tag in soup.find_all():
            if tag.has_attr("style"):
                del tag["style"]
            if tag.has_attr("dir"):
                del tag["dir"]

        # Desanidar <span> sin atributos
        for span in soup.find_all("span"):
            if not span.attrs:
                span.unwrap()

        # Eliminar elementos vacíos (excepto <br> o <img>)
        for tag in soup.find_all():
            if tag.name not in ['br', 'img'] and not tag.get_text(strip=True):
                tag.decompose()

        # Desenvolver <tbody> para simplificar la estructura de la tabla
        for tbody in soup.find_all("tbody"):
            tbody.unwrap()

        # Simplificar la tabla: quitar etiquetas <p> dentro de <td> para reducir el anidamiento
        for td in soup.find_all("td"):
            for p in td.find_all("p"):
                p.unwrap()

        return str(soup)

    except Exception as e:
        logging.error(f"Error al limpiar HTML: {str(e)}")
        return html



def normalize_unicode(data):
    """
    Recursivamente normaliza todas las cadenas de texto en un JSON.
     - Convierte caracteres Unicode raros a su forma estándar.
     - Elimina espacios en blanco extra.
    """
    if isinstance(data, str):
        return unicodedata.normalize("NFKC", data).strip()  # Normalizar texto

    elif isinstance(data, list):
        return [normalize_unicode(item) for item in data]  # Recorrer listas

    elif isinstance(data, dict):
        return {key: normalize_unicode(value) for key, value in data.items()}  # Recorrer diccionarios

    return data  # Devolver valores no texto sin cambios


def looks_like_html(text):
    """
    Comprueba si la cadena parece contener etiquetas HTML.
    """
    return bool(re.search(r'<[^>]+>', text))

def html_to_docx(html, tpl):
    """
    Convierte una cadena HTML en un subdocumento DOCX usando un proceso de conversión intermedia:
    HTML -> ODT -> DOCX.
    Se guarda el HTML en un archivo temporal, se convierte a ODT y luego se convierte a DOCX usando unoconvert.
    Finalmente, se carga el DOCX en la plantilla tpl.
    """
    start_time = time.time()  # Iniciar temporizador

    # Guardar el HTML en un archivo temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as tmp_html:
        tmp_html.write(html)
        tmp_html_path = tmp_html.name

    # Archivo temporal para el ODT intermedio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".odt") as tmp_odt:
        tmp_odt_path = tmp_odt.name

    # Convertir HTML a ODT
    result_odt = subprocess.run(
        ['unoconvert', '--convert-to', 'odt', tmp_html_path, tmp_odt_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result_odt.returncode != 0:
        error_msg = result_odt.stderr.decode()
        raise Exception("Error al convertir HTML a ODT con unoconvert: " + error_msg)

    # Archivo temporal para el DOCX final
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
        tmp_docx_path = tmp_docx.name

    # Convertir ODT a DOCX
    result_docx = subprocess.run(
        ['unoconvert', '--convert-to', 'docx', tmp_odt_path, tmp_docx_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result_docx.returncode != 0:
        error_msg = result_docx.stderr.decode()
        raise Exception("Error al convertir ODT a DOCX con unoconvert: " + error_msg)

    # Cargar el documento DOCX generado como subdocumento en la plantilla
    subdoc = tpl.new_subdoc(tmp_docx_path)

    logging.debug(f"HTML convertido en {time.time() - start_time:.2f} segundos")

    # Opcional: eliminar los archivos temporales
    os.remove(tmp_html_path)
    os.remove(tmp_odt_path)
    os.remove(tmp_docx_path)

    return subdoc


def process_context(context, tpl):
    """
    Recorre recursivamente el contexto y, si encuentra una cadena que parece HTML,
    la reemplaza por el objeto subdocumento generado con html_to_docx.
    Se agregan bloques try/except para capturar y registrar errores durante la conversión.
    """
    if isinstance(context, dict):
        new_context = {}
        for key, value in context.items():
            try:
                if isinstance(value, str) and looks_like_html(value):
                    new_context[key] = html_to_docx(value, tpl)
                elif isinstance(value, (dict, list)):
                    new_context[key] = process_context(value, tpl)
                else:
                    new_context[key] = value
            except Exception as e:
                logging.error(f"Error procesando la clave '{key} {str(e)}':{str(value)}")
                # Si ocurre un error, conservamos el valor original para evitar romper el proceso
                new_context[key] = value
        return new_context

    elif isinstance(context, list):
        new_list = []
        for idx, item in enumerate(context):
            try:
                if isinstance(item, str) and looks_like_html(item):
                    new_list.append(html_to_docx(item, tpl))
                elif isinstance(item, (dict, list)):
                    new_list.append(process_context(item, tpl))
                else:
                    new_list.append(item)
            except Exception as e:
                logging.error(f"Error procesando el índice {idx}: {str(e)}")
                # Si ocurre un error, se agrega el elemento original
                new_list.append(item)
        return new_list

    return context


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

            logging.debug("Antes de normalizar")
            context = normalize_unicode(context)

            logging.debug("Antes de clean_context_html")
            context = clean_context_html(context)
 
            save_json_for_debugging(context)

            logging.debug("Antes de process_context")
            context = process_context(context, doc)


            logging.debug("Antes de render")
            doc.render(context) #p, jinja_env=env)

        except Exception as e:
            logging.error(f"Error al renderizar la plantilla: {str(e)}")
            logging.error(f"Context: {str(context)}")
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
