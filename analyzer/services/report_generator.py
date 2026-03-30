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

def generate_plots(data, chart_type='bar'):
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

    img_buffer = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img_buffer, format='png', dpi=100)
    plt.close(fig)
    img_buffer.seek(0)
    images['main'] = img_buffer
    
    return images

def generate_excel_report(results, data, layout='horizontal', chart_type='bar'):
    output = io.BytesIO()
    formatted_results = {k.replace('_', ' ').title(): str(v) for k, v in results.items()}
    
    if layout == 'horizontal':
        df_columns = ['Métrica', 'Valor']
        df_data = [[k, v] for k, v in formatted_results.items()]
        df = pd.DataFrame(df_data, columns=df_columns)
    else:
        df_columns = list(formatted_results.keys())
        df_data = [list(formatted_results.values())]
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
        worksheet.set_column('B:B', 70, data_format)
    else:
        long_metrics = ["percentiles", "espacio muestral", "deciles", "cuartiles"]
        for col_num, col_name in enumerate(df.columns.values):
            if col_name.lower() in long_metrics:
                worksheet.set_column(col_num, col_num, 85, data_format)
            else:
                worksheet.set_column(col_num, col_num, 25, data_format)
                
        for row_num in range(1, len(df)+1):
            worksheet.set_row(row_num, 150) # Autoestirado forzado para percentiles gruesos
            worksheet.write_row(row_num, 0, df.iloc[row_num-1], data_format)
            
    if data:
        images = generate_plots(data, chart_type)
        insert_row = len(df) + 3
        worksheet.insert_image(f'B{insert_row}', 'main_chart.png', {'image_data': images['main']})
        
    writer.close()
    output.seek(0)
    return output

def generate_pdf_report(results, data, layout='horizontal', chart_type='bar'):
    pdf_output = io.BytesIO()
    
    # Orientación dinámica: Si es vertical, lo hacemos apaisado (landscape) para que las 4 columnas quepan súper holgadas
    page_size_used = landscape(letter) if layout == 'vertical' else letter
    doc = SimpleDocTemplate(pdf_output, pagesize=page_size_used, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], textColor=colors.HexColor('#4F46E5'), alignment=1, spaceAfter=20)
    h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'], textColor=colors.HexColor('#374151'), spaceAfter=15, spaceBefore=15)
    
    # Importante: CellStyle con text wrapping de ReportLab.
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, leading=12, alignment=1)
    header_cell_style = ParagraphStyle('HeaderCellStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#374151'), alignment=1)
    
    elements = []
    elements.append(Paragraph("Reporte Estadístico Analítico", title_style))
    elements.append(Spacer(1, 10))
    
    if layout == 'horizontal':
        table_data = [[Paragraph('Métrica Evaluada', header_cell_style), Paragraph('Valor Resultante', header_cell_style)]]
        for metric, value in results.items():
            str_value = str(value).replace('\n', '<br/>')
            table_data.append([
                Paragraph(metric.replace('_', ' ').title(), cell_style),
                Paragraph(str_value, cell_style)
            ])
        col_widths = [180, 300]
        
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
        # Dividimos en bloques de máximo 4 métricas por tabla para evitar "tallest cell" error.
        metric_items = list(results.items())
        chunk_size = 4
        page_width = page_size_used[0] - 80 # Ancho total menos los márgenes
        
        for i in range(0, len(metric_items), chunk_size):
            chunk = metric_items[i:i+chunk_size]
            headers = []
            row_data = []
            
            for metric, value in chunk:
                headers.append(Paragraph(metric.replace('_', ' ').title(), header_cell_style))
                str_value = str(value).replace('\n', '<br/>')
                row_data.append(Paragraph(str_value, cell_style))
                
            table_data = [headers, row_data]
            # Columnas equidistantes en este chunk
            col_widths = [page_width / len(chunk)] * len(chunk)
            
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D3D3D3')), # GRIS por requerimiento
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
    
    if data:
        elements.append(Paragraph("Gráfica de Análisis", h2_style))
        images = generate_plots(data, chart_type)
        
        main_img = RLImage(images['main'], width=450, height=280)
        
        img_table = Table([[main_img]])
        img_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(img_table)
    
    doc.build(elements)
    pdf_output.seek(0)
    return pdf_output
