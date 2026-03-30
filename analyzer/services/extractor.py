import pandas as pd
import pdfplumber
import docx
import re
import io

def extract_numbers(uploaded_file):
    filename = uploaded_file.name.lower()
    numbers = []

    try:
        if filename.endswith(('.xls', '.xlsx')):
            try:
                df = pd.read_excel(uploaded_file)
                for value in df.values.flatten():
                    try:
                        num = float(value)
                        if not pd.isna(num):
                            numbers.append(num)
                    except (ValueError, TypeError):
                        pass
            except Exception as e:
                raise ValueError(f"Error al leer Excel. Verifica que el archivo no esté corrupto. Detalle: {str(e)}")

        elif filename.endswith('.pdf'):
            try:
                file_bytes = uploaded_file.read()
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            matches = re.findall(r'-?\d+\.?\d*', text)
                            numbers.extend([float(x) for x in matches])
            except Exception as e:
                raise ValueError(f"Error al procesar el PDF. Asegúrate de que contiene texto leíble. Detalle: {str(e)}")

        elif filename.endswith(('.doc', '.docx')):
            try:
                doc = docx.Document(uploaded_file)
                for paragraph in doc.paragraphs:
                    matches = re.findall(r'-?\d+\.?\d*', paragraph.text)
                    numbers.extend([float(x) for x in matches])
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            matches = re.findall(r'-?\d+\.?\d*', cell.text)
                            numbers.extend([float(x) for x in matches])
            except Exception as e:
                raise ValueError(f"Error al procesar el documento Word. Verifica su formato y contenido. Detalle: {str(e)}")
        
        else:
            raise ValueError("Formato de archivo no compatible. Solo se permiten archivos Excel, Word o PDF.")

        # Limpiar y retornar si existe informacion
        if not numbers:
            raise ValueError("El archivo subido no contiene cifras o datos numéricos válidos accesibles. Por favor verifica su contenido.")
        
        return numbers

    except ValueError as ve:
        raise ve
    except Exception as e:
        raise ValueError(f"Ocurrió un error inesperado durante la extracción de datos: {str(e)}")
