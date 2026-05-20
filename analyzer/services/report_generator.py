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


def generate_problem_tree_pdf(problem_text, causes, effects, linked_data=None):
    """
    Genera un reporte PDF con diseño premium para el Árbol de Problemas.
    """
    pdf_output = io.BytesIO()
    doc = SimpleDocTemplate(pdf_output, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    # Custom Styles (Harmonious colors)
    title_style = ParagraphStyle('PT_Title', parent=styles['Heading1'], textColor=colors.HexColor('#7C3AED'), alignment=1, spaceAfter=20)
    h2_style = ParagraphStyle('PT_H2', parent=styles['Heading2'], textColor=colors.HexColor('#374151'), spaceBefore=15, spaceAfter=8)
    problem_style = ParagraphStyle('PT_Problem', parent=styles['Heading2'], textColor=colors.white, alignment=1)
    card_title_style = ParagraphStyle('PT_CardTitle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1F2937'), alignment=1)
    body_style = ParagraphStyle('PT_Body', parent=styles['Normal'], fontSize=9, leading=12)
    
    elements = []
    
    # Title
    elements.append(Paragraph("Reporte de Planificación: Árbol de Problemas", title_style))
    elements.append(Spacer(1, 10))
    
    # 1. Central Problem (Highlight Card)
    elements.append(Paragraph("PROBLEMA CENTRAL", ParagraphStyle('PT_Header_PC', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#6B7280'), spaceAfter=5, alignment=1)))
    
    prob_p = Paragraph(f"<b>{problem_text}</b>", problem_style)
    prob_table = Table([[prob_p]], colWidths=[500])
    prob_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#7C3AED')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#6D28D9')),
    ]))
    elements.append(prob_table)
    elements.append(Spacer(1, 20))
    
    # 2. Effects Section (Branches)
    elements.append(Paragraph("EFECTOS (CONSECUENCIAS)", h2_style))
    eff_elements = []
    if not effects:
        eff_elements.append([Paragraph("No se registraron efectos.", body_style)])
    else:
        for idx, eff in enumerate(effects):
            eff_elements.append([Paragraph(f"<b>Efecto {idx+1}:</b> {eff}", body_style)])
            
    eff_table = Table(eff_elements, colWidths=[500])
    eff_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FDF2F8')), # Light pink/purple shade
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F472B6')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(eff_table)
    elements.append(Spacer(1, 20))
    
    # 3. Causes Section (Roots)
    elements.append(Paragraph("CAUSAS (ORÍGENES)", h2_style))
    cause_elements = []
    if not causes:
        cause_elements.append([Paragraph("No se registraron causas.", body_style)])
    else:
        for idx, cause in enumerate(causes):
            cause_elements.append([Paragraph(f"<b>Causa {idx+1}:</b> {cause}", body_style)])
            
    cause_table = Table(cause_elements, colWidths=[500])
    cause_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F3FF')), # Light indigo/violet shade
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A78BFA')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(cause_table)
    elements.append(Spacer(1, 25))
    
    # 4. Quantitative Linked Data (If exists)
    if linked_data:
        elements.append(Paragraph("Sustentación Cuantitativa (Datos Vinculados)", h2_style))
        elements.append(Paragraph("Las siguientes variables del dataset fueron vinculadas para justificar causas y efectos:", ParagraphStyle('LD_Desc', parent=styles['Normal'], fontSize=9, spaceAfter=10)))
        
        ld_header = [Paragraph("<b>Nodo / Tarjeta</b>", card_title_style), 
                     Paragraph("<b>Variable Mapeada</b>", card_title_style), 
                     Paragraph("<b>Métricas Descriptivas de los Datos</b>", card_title_style)]
        ld_rows = [ld_header]
        
        for item in linked_data:
            node_desc = Paragraph(f"<b>{item.get('node_type', '')}:</b> {item.get('node_text', '')}", body_style)
            var_name = Paragraph(f"<code>{item.get('columna', '')}</code>", body_style)
            
            stats_str = ""
            for sk, sv in item.get('stats', {}).items():
                stats_str += f"<b>{sk}:</b> {sv}<br/>"
            stats_p = Paragraph(stats_str if stats_str else "N/A", body_style)
            
            ld_rows.append([node_desc, var_name, stats_p])
            
        ld_table = Table(ld_rows, colWidths=[200, 110, 190])
        ld_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EDE9FE')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(ld_table)
        
    doc.build(elements)
    pdf_output.seek(0)
    return pdf_output


def generate_bayesian_network_pdf(nodes, edges, cpts, evidence, inference_results):
    """
    Genera un reporte PDF con diseño premium para la Red Bayesiana.
    """
    pdf_output = io.BytesIO()
    doc = SimpleDocTemplate(pdf_output, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('BN_Title', parent=styles['Heading1'], textColor=colors.HexColor('#0891B2'), alignment=1, spaceAfter=20)
    h2_style = ParagraphStyle('BN_H2', parent=styles['Heading2'], textColor=colors.HexColor('#374151'), spaceBefore=15, spaceAfter=8)
    body_style = ParagraphStyle('BN_Body', parent=styles['Normal'], fontSize=9, leading=12)
    header_style = ParagraphStyle('BN_Header', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#374151'), alignment=1)
    cell_style = ParagraphStyle('BN_Cell', parent=styles['Normal'], fontSize=8, alignment=1)
    
    elements = []
    
    # Title
    elements.append(Paragraph("Reporte de Análisis: Inferencia en Red Bayesiana", title_style))
    elements.append(Spacer(1, 10))
    
    # 1. Network Structure
    elements.append(Paragraph("1. Estructura de la Red Bayesiana", h2_style))
    nodes_str = ", ".join(nodes.keys())
    elements.append(Paragraph(f"<b>Variables (Nodos):</b> {nodes_str}", body_style))
    
    edges_str = " | ".join([f"{u} → {v}" for u, v in edges]) if edges else "Ninguna (Variables independientes)"
    elements.append(Paragraph(f"<b>Dependencias (Relaciones):</b> {edges_str}", body_style))
    elements.append(Spacer(1, 10))
    
    # 2. Evidence (Context)
    elements.append(Paragraph("2. Evidencia (Condiciones Observadas)", h2_style))
    if not evidence:
        elements.append(Paragraph("<i>No se fijó ninguna evidencia. Se calculan probabilidades a priori.</i>", body_style))
    else:
        ev_elements = []
        for var, val in evidence.items():
            ev_elements.append([Paragraph(f"<b>Variable:</b> {var}", body_style), Paragraph(f"<b>Valor Observado:</b> {val}", body_style)])
        ev_table = Table(ev_elements, colWidths=[250, 250])
        ev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ECFDF5')), # Soft emerald
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#10B981')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(ev_table)
    elements.append(Spacer(1, 15))
    
    # 3. Inference Results (Core calculation)
    elements.append(Paragraph("3. Resultados de Inferencia Exacta (Variable Elimination)", h2_style))
    inf_rows = [[Paragraph("<b>Variable Consultada</b>", header_style), Paragraph("<b>Distribución de Probabilidad Posterior</b>", header_style)]]
    
    for var, dist in inference_results.items():
        var_p = Paragraph(f"<b>{var}</b>", body_style)
        
        dist_str = ""
        for state, prob in dist.items():
            pct = float(prob) * 100
            dist_str += f"• {state}: <b>{pct:.2f}%</b> (prob={prob})<br/>"
        dist_p = Paragraph(dist_str, body_style)
        
        inf_rows.append([var_p, dist_p])
        
    inf_table = Table(inf_rows, colWidths=[200, 300])
    inf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0F2FE')), # Light cyan
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(inf_table)
    elements.append(Spacer(1, 20))
    
    # 4. Tables CPT Summary
    elements.append(Paragraph("4. Tablas de Probabilidad Condicional (CPT)", h2_style))
    for var, cpt_info in cpts.items():
        elements.append(Paragraph(f"<b>Tabla CPT de: {var}</b>", ParagraphStyle('BN_CptNode', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#0891B2'), spaceBefore=8, spaceAfter=4)))
        
        cpt_vars = cpt_info['variables']
        # Header for CPT
        cpt_header = [Paragraph(v, header_style) for v in cpt_vars] + [Paragraph("P", header_style)]
        cpt_rows = [cpt_header]
        
        for k, v in cpt_info['table'].items():
            row_items = []
            if isinstance(k, str):
                cleaned = k.strip('()')
                tup = tuple(x.strip().replace("'", "").replace('"', '') for x in cleaned.split(','))
                if len(tup) == 1 and k.endswith(','):
                    tup = (tup[0],)
            else:
                tup = k
            for val in tup:
                row_items.append(Paragraph(str(val), cell_style))
            row_items.append(Paragraph(f"<b>{float(v):.4f}</b>", cell_style))
            cpt_rows.append(row_items)
            
        col_width_factor = 500 / (len(cpt_vars) + 1)
        cpt_table = Table(cpt_rows, colWidths=[col_width_factor]*(len(cpt_vars)+1))
        cpt_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(cpt_table)
        elements.append(Spacer(1, 10))
        
    doc.build(elements)
    pdf_output.seek(0)
    return pdf_output


def generate_markov_chains_pdf(states, transition_matrix, steps, projections, steady_state, simulated_path=None):
    """
    Genera un reporte PDF con diseño premium para Cadenas de Markov.
    """
    pdf_output = io.BytesIO()
    doc = SimpleDocTemplate(pdf_output, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('MC_Title', parent=styles['Heading1'], textColor=colors.HexColor('#DB2777'), alignment=1, spaceAfter=20)
    h2_style = ParagraphStyle('MC_H2', parent=styles['Heading2'], textColor=colors.HexColor('#374151'), spaceBefore=15, spaceAfter=8)
    body_style = ParagraphStyle('MC_Body', parent=styles['Normal'], fontSize=9, leading=12)
    header_style = ParagraphStyle('MC_Header', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#374151'), alignment=1)
    cell_style = ParagraphStyle('MC_Cell', parent=styles['Normal'], fontSize=8, alignment=1)
    
    elements = []
    
    # Title
    elements.append(Paragraph("Reporte de Análisis: Cadenas de Markov", title_style))
    elements.append(Spacer(1, 10))
    
    # 1. Transition Matrix
    elements.append(Paragraph("1. Matriz de Transición de Estados", h2_style))
    elements.append(Paragraph("Muestra las probabilidades de transición del estado origen (fila) al estado destino (columna):", body_style))
    elements.append(Spacer(1, 5))
    
    # Render Matrix
    mat_header = [Paragraph("<b>Origen \\ Destino</b>", header_style)] + [Paragraph(s, header_style) for s in states]
    mat_rows = [mat_header]
    for idx, row_probs in enumerate(transition_matrix):
        row = [Paragraph(f"<b>{states[idx]}</b>", body_style)]
        for p in row_probs:
            row.append(Paragraph(f"{float(p):.4f}", cell_style))
        mat_rows.append(row)
        
    col_width_factor = 500 / (len(states) + 1)
    mat_table = Table(mat_rows, colWidths=[col_width_factor]*(len(states)+1))
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FDF2F8')), # Soft pink
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F472B6')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#F8FAFC')),
    ]))
    elements.append(mat_table)
    elements.append(Spacer(1, 15))
    
    # 2. Steady State (Equilibrium)
    elements.append(Paragraph("2. Distribución de Estado Estacionario (Largo Plazo)", h2_style))
    elements.append(Paragraph("Distribución de equilibrio probabilístico hacia donde converge el sistema a largo plazo (infinito número de pasos):", body_style))
    elements.append(Spacer(1, 5))
    
    steady_rows = [[Paragraph("<b>Estado</b>", header_style), Paragraph("<b>Probabilidad Estacionaria Limítrofe</b>", header_style)]]
    for idx, state in enumerate(states):
        prob = steady_state[idx]
        pct = float(prob) * 100
        steady_rows.append([Paragraph(state, body_style), Paragraph(f"<b>{pct:.2f}%</b> (prob={prob:.4f})", body_style)])
        
    steady_table = Table(steady_rows, colWidths=[250, 250])
    steady_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(steady_table)
    elements.append(Spacer(1, 15))
    
    # 3. Future Projections (Step by Step)
    elements.append(Paragraph(f"3. Proyección Evolutiva (Hasta {steps} Pasos en el Futuro)", h2_style))
    elements.append(Paragraph("Evolución temporal del vector de probabilidades para cada paso:", body_style))
    elements.append(Spacer(1, 5))
    
    proj_header = [Paragraph("<b>Paso</b>", header_style)] + [Paragraph(s, header_style) for s in states]
    proj_rows = [proj_header]
    for step_num, dist in enumerate(projections):
        row = [Paragraph(f"Paso {step_num}", body_style)]
        for p in dist:
            row.append(Paragraph(f"{float(p):.4f}", cell_style))
        proj_rows.append(row)
        
    proj_table = Table(proj_rows, colWidths=[col_width_factor]*(len(states)+1))
    proj_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECEFEE')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
    ]))
    elements.append(proj_table)
    elements.append(Spacer(1, 15))
    
    # 4. Random Walk Simulation (If exists)
    if simulated_path:
        elements.append(Paragraph("4. Simulación Monte Carlo de Recorrido Aleatorio (Random Walk)", h2_style))
        elements.append(Paragraph(f"Secuencia simulada de estados visitados paso a paso (primeros 40 mostrados):", body_style))
        
        path_str = " → ".join(simulated_path[:40])
        if len(simulated_path) > 40:
            path_str += f" → ... (+{len(simulated_path) - 40} estados)"
            
        elements.append(Paragraph(f"<font color='#DB2777'><b>Camino:</b></font> {path_str}", ParagraphStyle('MC_Path', parent=styles['Normal'], fontSize=8.5, leading=11, spaceBefore=5)))
        elements.append(Spacer(1, 10))
        
        # Calculate simulated frequencies
        from collections import Counter
        counts = Counter(simulated_path)
        total = len(simulated_path)
        
        freq_rows = [[Paragraph("<b>Estado</b>", header_style), Paragraph("<b>Veces Visitado</b>", header_style), Paragraph("<b>Frecuencia Empírica</b>", header_style)]]
        for s in states:
            c = counts.get(s, 0)
            pct = (c / total) * 100
            freq_rows.append([Paragraph(s, body_style), Paragraph(str(c), body_style), Paragraph(f"<b>{pct:.2f}%</b>", body_style)])
            
        freq_table = Table(freq_rows, colWidths=[150, 150, 200])
        freq_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FDF2F8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F472B6')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(freq_table)
        
    doc.build(elements)
    pdf_output.seek(0)
    return pdf_output

