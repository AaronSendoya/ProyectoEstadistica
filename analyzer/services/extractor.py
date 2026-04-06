import pandas as pd
import pdfplumber
import docx
import re
import io

def compute_data_profile(df):
    """Computes statistical profile of a DataFrame to enable metric validation."""
    import numpy as np
    numeric_df = df.select_dtypes(include='number')
    n = len(df)
    profile = {
        'n': n,
        'has_negative': False,
        'has_zero': False,
        'unique_ratio': 0.0,
        'has_numeric': len(numeric_df.columns) > 0,
    }
    if len(numeric_df.columns) > 0:
        flat = numeric_df.values.flatten()
        flat = flat[~np.isnan(flat.astype(float))]
        if len(flat) > 0:
            profile['has_negative'] = bool(np.any(flat < 0))
            profile['has_zero'] = bool(np.any(flat == 0))
            profile['unique_ratio'] = round(float(len(np.unique(flat)) / len(flat)), 4)
    return profile

def get_file_info(uploaded_file):
    filename = uploaded_file.name
    filename_lower = filename.lower()
    result_list = []
    
    try:
        if filename_lower.endswith(('.xls', '.xlsx')):
            import numpy as np
            # Leemos todas las hojas de forma eficiente
            dfs = pd.read_excel(uploaded_file, sheet_name=None, nrows=100)
            for sheet_name, df in dfs.items():
                df = df.replace({pd.NA: None, np.nan: None})
                profile = compute_data_profile(df)
                result_list.append({
                    'name': f"{filename} - {sheet_name}",
                    'columns': [str(col) for col in df.columns],
                    'preview': df.to_dict('records'),
                    'profile': profile
                })
        else:
            result_list.append({
                'name': filename,
                'columns': ['Datos Genéricos del Documento'],
                'preview': [{'Dato': 'Vista previa no disponible para PDF/Word'}],
                'profile': {'n': 0, 'has_negative': False, 'has_zero': False, 'unique_ratio': 0.0, 'has_numeric': False}
            })
    except Exception as e:
        print("Error en get_file_info:", e)
        
    return result_list

def extract_numbers(uploaded_file, target_column=None):
    filename = uploaded_file.name.lower()
    numbers = []

    try:
        if filename.endswith(('.xls', '.xlsx')):
            try:
                dfs = pd.read_excel(uploaded_file, sheet_name=None)
                
                for sheet_name, df in dfs.items():
                    # Extraer de todas las hojas que contengan la columna objetivo, o aplanar toda la hoja
                    if target_column and target_column in df.columns:
                        source_values = df[target_column].dropna().values
                    elif not target_column:
                        source_values = df.values.flatten()
                    else:
                        continue # La columna no está en esta hoja

                    for value in source_values:
                        try:
                            num = float(value)
                            if not pd.isna(num):
                                numbers.append(num)
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                raise ValueError(f"Error al leer Excel multicapa. Verifica que el archivo no esté corrupto. Detalle: {str(e)}")

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
