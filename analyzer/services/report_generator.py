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

def generate_excel_report(results_pivot, data_dict, chart_types_dict, layout='horizontal'):
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
        
    writer.close()
    output.seek(0)
    return output

def generate_pdf_report(results_pivot, data_dict, chart_types_dict, layout='horizontal'):
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

    if layout == 'horizontal':
        header_row = [Paragraph('Métrica Evaluada', header_cell_style)]
        for var_name in variables:
            header_row.append(Paragraph(var_name, header_cell_style))
        table_data = [header_row]
        
        for metric, vars_data in results_pivot.items():
            row = [Paragraph(metric.replace('_', ' ').title(), cell_style)]
            for var_name in variables:
                row.append(Paragraph(str(vars_data.get(var_name, 'N/A')).replace('\n', '<br/>'), cell_style))
            table_data.append(row)
            
        remaining_space = 400
        var_width = remaining_space / len(variables) if variables else 300
        col_widths = [140] + [var_width] * len(variables)
        
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D3E4F6')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#9CA3AF')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
    else:
        # Layout Vertical: CHUNKING
        chunk_size = max(1, 4 - (1 if len(variables) > 2 else 0))
        metric_items = list(results_pivot.items())
        page_width = page_size_used[0] - 80 
        
        for i in range(0, len(metric_items), chunk_size):
            chunk = metric_items[i:i+chunk_size]
            headers = [Paragraph('Variable', header_cell_style)]
            for metric, _ in chunk:
                headers.append(Paragraph(metric.replace('_', ' ').title(), header_cell_style))
                
            table_data = [headers]
            for var_name in variables:
                row = [Paragraph(var_name, header_cell_style)]
                for metric, vars_data in chunk:
                    row.append(Paragraph(str(vars_data.get(var_name, 'N/A')).replace('\n', '<br/>'), cell_style))
                table_data.append(row)
            
            col_widths = [page_width / (len(chunk) + 1)] * (len(chunk) + 1)
            
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D3D3D3')), 
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#9CA3AF')),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 25))
    
    if data_dict:
        elements.append(Paragraph("Gráficas de Análisis", h2_style))
        for var_name, data in data_dict.items():
            chart_type = chart_types_dict.get(var_name, 'bar')
            images = generate_plots(data, chart_type, target_column=var_name)
            
            elements.append(Paragraph(f"Contexto Analítico: {var_name}", ParagraphStyle('imgTit', alignment=1, spaceAfter=5)))
            main_img = RLImage(images['main'], width=450, height=280)
            
            img_table = Table([[main_img]])
            img_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(img_table)
            elements.append(Spacer(1, 20))
    
    doc.build(elements)
    pdf_output.seek(0)
    return pdf_output
