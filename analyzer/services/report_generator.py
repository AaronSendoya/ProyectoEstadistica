import io
import base64
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_plots(data, chart_type='bar', target_column=None):
    """
    Genera gráfico en memoria dependiendo del chart_type configurado.
    """
    import numpy as np
    images = {}
    fig, ax = plt.subplots(figsize=(8, 5))
    
    if chart_type == 'line':
        ax.plot(data, color='#10B981', marker='o', linestyle='-', markersize=4)
        ax.set_title('Gráfico Lineal')
        ax.set_xlabel('Índice')
        ax.set_ylabel('Valor')
        
    elif chart_type == 'pie':
        unique, counts = np.unique(data, return_counts=True)
        if len(unique) > 10:
            sorted_indices = np.argsort(-counts)
            unique = unique[sorted_indices[:10]]
            counts = counts[sorted_indices[:10]]
            ax.set_title('Diagrama Circular (Top 10 Valores Estrictos)')
        else:
            ax.set_title('Diagrama Circular')
        ax.pie(counts, labels=unique, autopct='%1.1f%%', startangle=90, colors=plt.cm.Pastel1.colors)
        
    elif chart_type == 'scatter':
        ax.scatter(range(len(data)), data, color='#F59E0B', alpha=0.6)
        ax.set_title('Gráfico de Dispersión')
        ax.set_xlabel('Índice')
        ax.set_ylabel('Valor')
        
    elif chart_type == 'frequency':
        # Histograma de frecuencias para datos continuos/agrupados
        ax.hist(data, bins='sturges', color='#06B6D4', alpha=0.7, edgecolor='black')
        ax.set_title('Histograma de Frecuencias')
        ax.set_xlabel('Intervalos / Valores')
        ax.set_ylabel('Frecuencia Absoluta')
        
    else: # fallback == 'bar'
        unique, counts = np.unique(data, return_counts=True)
        if len(unique) > 30: # Mucha entropia para barras exactas, mejor histograma
            ax.hist(data, bins='auto', color='#4F46E5', alpha=0.7, edgecolor='black')
        else:
            ax.bar(unique, counts, color='#4F46E5', alpha=0.7, edgecolor='black')
        ax.set_title('Gráfico de Columnas / Distribución')
        ax.set_xlabel('Valor')
        ax.set_ylabel('Frecuencia')

    if target_column:
        ax.set_title(f"Distribución de {target_column}")
        ax.set_xlabel(target_column)
        if chart_type != 'pie':
            ax.set_ylabel("Frecuencia / Magnitud")

    img_buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img_buffer, format='png', dpi=100)
    plt.close(fig)
    img_buffer.seek(0)
    images['main'] = img_buffer
    
    return images

def generate_excel_report(results_pivot, data_dict, chart_types_dict, layout='horizontal', freq_tables=None):
    output = io.BytesIO()
    
    df_metrics = list(results_pivot.keys())
    variables = list(data_dict.keys())
    
    if layout == 'horizontal':
        df_columns = ['Métrica'] + variables
        df_data = []
        for metric in df_metrics:
            row = [metric.replace('_', ' ').title()]
            for var_name in variables:
                row.append(str(results_pivot[metric].get(var_name, 'N/A')))
            df_data.append(row)
        df = pd.DataFrame(df_data, columns=df_columns)
    else:
        df_columns = ['Variable'] + [m.replace('_', ' ').title() for m in df_metrics]
        df_data = []
        for var_name in variables:
            row = [var_name]
            for metric in df_metrics:
                row.append(str(results_pivot[metric].get(var_name, 'N/A')))
            df_data.append(row)
        df = pd.DataFrame(df_data, columns=df_columns)
        
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Resultados')
    
    workbook = writer.book
    worksheet = writer.sheets['Resultados']
    
    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#D3D3D3', 'border': 1,
        'align': 'center', 'valign': 'vcenter'
    })
    
    data_format = workbook.add_format({
        'align': 'center', 'valign': 'top', 'border': 1, 'text_wrap': True
    })
    
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        
    if layout == 'horizontal':
        worksheet.set_column('A:A', 30, data_format)
        if len(variables) > 0:
            last_col_letter = chr(65 + len(variables)) if len(variables) < 26 else 'Z'
            worksheet.set_column(f'B:{last_col_letter}', 70 / len(variables) if variables else 70, data_format)
    else:
        worksheet.set_column('A:A', 30, data_format)
        for col_num, col_name in enumerate(df.columns.values):
            if col_num > 0:
                worksheet.set_column(col_num, col_num, 30, data_format)
                
    for row_num in range(1, len(df)+1):
        worksheet.set_row(row_num, 150) # Autoestirado forzado para percentiles/multi-line
        worksheet.write_row(row_num, 0, df.iloc[row_num-1], data_format)
            
    if data_dict:
        insert_row = len(df) + 3
        current_col = 1
        for var_name, data in data_dict.items():
            chart_type = chart_types_dict.get(var_name, 'bar')
            images = generate_plots(data, chart_type, target_column=var_name)
            col_letter = chr(65 + current_col) if current_col < 26 else 'B'
            worksheet.insert_image(f'{col_letter}{insert_row}', f'{var_name}_chart.png', {'image_data': images['main']})
            current_col += 7
        
    # ── Hojas de Tablas de Frecuencias ──
    if freq_tables:
        for var_name, ft_data in freq_tables.items():
            sheet_name = f'Frec_{var_name[:25]}'  # Nombre máximo de 31 chars en Excel
            filas = ft_data.get('filas', [])
            if not filas:
                continue
            
            ft_columns = ['Intervalo', 'Marca (xi)', 'fi', 'Fi', 'hi', 'Hi']
            ft_rows = []
            for fila in filas:
                ft_rows.append([
                    fila['intervalo'],
                    fila['xi'],
                    fila['fi'],
                    fila['Fi'],
                    fila['hi'],
                    fila['Hi']
                ])
            
            df_freq = pd.DataFrame(ft_rows, columns=ft_columns)
            df_freq.to_excel(writer, index=False, sheet_name=sheet_name)
            
            ws_freq = writer.sheets[sheet_name]
            for col_num, value in enumerate(ft_columns):
                ws_freq.write(0, col_num, value, header_format)
            ws_freq.set_column('A:A', 22, data_format)
            ws_freq.set_column('B:F', 15, data_format)
            
            # Info de parámetros de la tabla
            info_row = len(ft_rows) + 2
            ws_freq.write(info_row, 0, f"n = {ft_data.get('n', '?')}")
            ws_freq.write(info_row + 1, 0, f"k (clases) = {ft_data.get('k', '?')}")
            ws_freq.write(info_row + 2, 0, f"Rango = {ft_data.get('rango', '?')}")
            ws_freq.write(info_row + 3, 0, f"Amplitud = {ft_data.get('amplitud', '?')}")

    writer.close()
    output.seek(0)
    return output

def generate_pdf_report(results_pivot, data_dict, chart_types_dict, layout='horizontal', freq_tables=None):
    pdf_output = io.BytesIO()
    
    # Orientación dinámica: Si es vertical, lo hacemos apaisado (landscape)
    page_size_used = landscape(letter) if layout == 'vertical' else letter
    doc = SimpleDocTemplate(pdf_output, pagesize=page_size_used, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], textColor=colors.HexColor('#4F46E5'), alignment=1, spaceAfter=20)
    h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'], textColor=colors.HexColor('#374151'), spaceAfter=15, spaceBefore=15)
    
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, leading=12, alignment=1)
    header_cell_style = ParagraphStyle('HeaderCellStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#374151'), alignment=1)
    
    elements = []
    elements.append(Paragraph("Reporte Estadístico Analítico Multi-Variable", title_style))
    elements.append(Spacer(1, 10))
    
    variables = list(data_dict.keys())
    long_procedures = [] # Para guardar procedimientos que no caben en la tabla

    # PRE-PROCESAMIENTO: Separar procedimientos largos
    pivot_filtered = {}
    long_metrics_set = set() # Nombres de métricas que se movieron al detalle
    
    for metric, vars_data in results_pivot.items():
        metric_label = metric.replace('_', ' ').title()
        is_long = False
        for var_name in variables:
            val = str(vars_data.get(var_name, ''))
            if val.count('\n') > 12: # Límite de líneas por celda un poco más estricto
                is_long = True
                break
        
        if is_long:
            long_metrics_set.add(metric)
            for var_name in variables:
                val = vars_data.get(var_name)
                if val:
                    long_procedures.append((var_name, metric_label, val))
        
        # Siempre mantenemos la métrica en pivot_filtered para que aparezca en la tabla
        # pero cambiaremos su contenido si es larga
        pivot_filtered[metric] = vars_data

    # 1. RENDERIZAR TABLA PRINCIPAL
    available_width = page_size_used[0] - 80 # Letter vertical = 532, Landscape = 712
    
    if layout == 'horizontal':
        header_row = [Paragraph('Métrica Evaluada', header_cell_style)]
        for var_name in variables:
            header_row.append(Paragraph(var_name, header_cell_style))
        table_data = [header_row]
        
        for metric, vars_data in pivot_filtered.items():
            metric_label = metric.replace('_', ' ').title()
            row = [Paragraph(metric_label, cell_style)]
            
            for var_name in variables:
                val = str(vars_data.get(var_name, 'N/A'))
                if metric in long_metrics_set:
                    # En lugar de dejarlo vacío o roto, ponemos aviso
                    row.append(Paragraph("<i>Ver detalle extenso al final del reporte</i>", ParagraphStyle('SmallItalic', parent=cell_style, fontSize=7, textColor=colors.grey)))
                else:
                    row.append(Paragraph(val.replace('\n', '<br/>'), cell_style))
            table_data.append(row)
            
        col_metrics_width = 110
        col_vars_width = (available_width - col_metrics_width) / len(variables) if variables else 300
        col_widths = [col_metrics_width] + [col_vars_width] * len(variables)
        
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
    else:
        # Layout Vertical
        for var_name in variables:
            elements.append(Paragraph(f"Variable: {var_name}", h2_style))
            v_table_data = [[Paragraph('Métrica', header_cell_style), Paragraph('Resultado', header_cell_style)]]
            for metric, vars_data in pivot_filtered.items():
                val = str(vars_data.get(var_name, 'N/A'))
                v_table_data.append([
                    Paragraph(metric.replace('_', ' ').title(), cell_style),
                    Paragraph(val.replace('\n', '<br/>'), cell_style)
                ])
            
            t = Table(v_table_data, colWidths=[150, 450], repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 20))
    
    # 2. RENDERIZAR PROCEDIMIENTOS EXTENSOS (Si existen)
    if long_procedures:
        elements.append(Paragraph("Detalle de Procedimientos Extensos", h2_style))
        for var_name, metric_name, procedure in long_procedures:
            elements.append(Paragraph(f"{metric_name} - {var_name}", ParagraphStyle('ProcTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#4F46E5'), spaceBefore=10)))
            # Importante: Cada línea como párrafo separado para permitir saltos de página
            for line in procedure.split('\n'):
                if line.strip():
                    elements.append(Paragraph(line, ParagraphStyle('ProcLine', parent=styles['Normal'], fontSize=8, leading=10, leftIndent=10)))
            elements.append(Spacer(1, 10))

    # 3. RENDERIZAR TABLAS DE FRECUENCIAS
    if freq_tables:
        elements.append(Paragraph("Tablas de Distribución de Frecuencias", h2_style))
        for var_name, ft_data in freq_tables.items():
            filas = ft_data.get('filas', [])
            if not filas: continue
            
            elements.append(Paragraph(f"Variable: {var_name}", ParagraphStyle('ftTitle', parent=styles['Heading3'], textColor=colors.HexColor('#4F46E5'), spaceAfter=8)))
            info_text = f"n = {ft_data.get('n', '?')} | k (clases) = {ft_data.get('k', '?')} | Rango = {ft_data.get('rango', '?')} | Amplitud = {ft_data.get('amplitud', '?')}"
            elements.append(Paragraph(info_text, ParagraphStyle('ftInfo', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#6B7280'), spaceAfter=8)))
            
            ft_header = [Paragraph('Intervalo', header_cell_style), Paragraph('xi', header_cell_style), Paragraph('fi', header_cell_style), 
                         Paragraph('Fi', header_cell_style), Paragraph('hi', header_cell_style), Paragraph('Hi', header_cell_style)]
            ft_table_data = [ft_header]
            for fila in filas:
                ft_table_data.append([Paragraph(str(fila['intervalo']), cell_style), Paragraph(str(fila['xi']), cell_style), Paragraph(str(fila['fi']), cell_style),
                                      Paragraph(str(fila['Fi']), cell_style), Paragraph(str(fila['hi']), cell_style), Paragraph(str(fila['Hi']), cell_style)])
            
            ft_table = Table(ft_table_data, colWidths=[120, 60, 50, 50, 60, 60], repeatRows=1)
            ft_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E7FF')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#9CA3AF')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ]))
            elements.append(ft_table)
            elements.append(Spacer(1, 20))
    
    # 4. RENDERIZAR GRÁFICOS
    if data_dict:
        elements.append(Paragraph("Gráficas de Análisis", h2_style))
        for var_name, data in data_dict.items():
            chart_type = chart_types_dict.get(var_name, 'bar')
            images = generate_plots(data, chart_type, target_column=var_name)
            elements.append(Paragraph(f"Contexto Analítico: {var_name}", ParagraphStyle('imgTit', alignment=1, spaceAfter=5)))
            main_img = RLImage(images['main'], width=450, height=280)
            img_table = Table([[main_img]])
            img_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
            elements.append(img_table)
            elements.append(Spacer(1, 20))
    
    doc.build(elements)
    pdf_output.seek(0)
    return pdf_output
