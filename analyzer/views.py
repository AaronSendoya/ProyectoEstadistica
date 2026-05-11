import json
import base64
import pandas as pd
import numpy as np
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .services.extractor import extract_numbers, get_file_info
from .services.statistics_engine import analyze_data
from .services.report_generator import generate_excel_report, generate_pdf_report, generate_plots
from .models import AnalysisLog

def peek_file_columns(request):
    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return JsonResponse({'error': 'No se adjuntaron archivos'}, status=400)
        try:
            all_files_info = []
            for f in uploaded_files:
                file_info_list = get_file_info(f)
                all_files_info.extend(file_info_list)

            # Merge per-sheet profiles into one global data_profile
            profiles = [s.get('profile', {}) for s in all_files_info if s.get('profile')]
            merged_profile = {
                'total_rows': sum(p.get('n', 0) for p in profiles),
                'min_n': min((p.get('n', 0) for p in profiles), default=0),
                'has_negative': any(p.get('has_negative', False) for p in profiles),
                'has_zero': any(p.get('has_zero', False) for p in profiles),
                'unique_ratio': (sum(p.get('unique_ratio', 0) for p in profiles) / len(profiles)) if profiles else 0,
                'has_numeric': any(p.get('has_numeric', False) for p in profiles),
            }

            return JsonResponse({'sheets': all_files_info, 'data_profile': merged_profile})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def index_view(request):
    if request.method == 'GET':
        return render(request, 'analyzer/index.html')

    elif request.method == 'POST':
        try:
            uploaded_files = request.FILES.getlist('file')
            if not uploaded_files:
                print("DEBUG: No se recibió ningún archivo en request.FILES. Contenido de request.FILES:", request.FILES)
                return JsonResponse({'error': 'No se adjuntó el archivo'}, status=400)
            
            metrics = request.POST.getlist('metrics[]')
            if not metrics:
                print("DEBUG: No se recibieron métricas. Contenido de request.POST:", request.POST)
                return JsonResponse({'error': 'Selecciona al menos una métrica para analizar.'}, status=400)
                
            export_format = request.POST.get('format', 'excel')
            layout = request.POST.get('layout', 'horizontal')
            detail_level = request.POST.get('detail_level', 'direct')
            variables_json = request.POST.get('variables', '[]')
            
            try:
                variables_list = json.loads(variables_json)
            except json.JSONDecodeError:
                variables_list = []
                
            if not variables_list:
                return JsonResponse({'error': 'Agrega al menos una variable a analizar en el Constructor.'}, status=400)
            
            print(f"DEBUG: Archivo: {', '.join([uf.name for uf in uploaded_files])}, Métricas: {metrics}, Vars: {variables_list}, Formato: {export_format}, Nivel: {detail_level}")

            import numpy as np

            # Separar métricas de posición individuales
            pos_metrics = [m for m in metrics if m.startswith(('cuartil_', 'decil_', 'percentil_'))]
            engine_metrics = [m for m in metrics if not m.startswith(('cuartil_', 'decil_', 'percentil_'))]

            results_pivot = {}
            images_base64_list = []
            valid_data_for_reports = {} 
            chart_types_for_reports = {}
            freq_tables = {}  # Tablas de frecuencias por variable

            for var_obj in variables_list:
                target_column = var_obj.get('columna')
                chart_type = var_obj.get('grafico', 'bar')
                
                # 1. Extracción (Clean data) - Agregar de todos los archivos
                data = []
                for uf in uploaded_files:
                    uf.seek(0)
                    try:
                        file_data = extract_numbers(uf, target_column)
                        data.extend(file_data)
                    except Exception as e:
                        print(f"Advertencia: {e}")
                
                if not data:
                    return JsonResponse({'error': f"Error en columna {target_column}: no se encontraron datos válidos en los archivos proporcionados."}, status=400)
                
                # Convertir a nativos para guardarlo en la sesión (JSON)
                try:
                    native_data = [float(x) for x in data]
                except:
                    native_data = list(data)
                
                valid_data_for_reports[target_column] = native_data
                chart_types_for_reports[target_column] = chart_type

                # 2. Motor Estadístico
                var_results = analyze_data(data, engine_metrics, detail_level)
                if "error" in var_results:
                     return JsonResponse({'error': f"Error en motor para {target_column}: {var_results['error']}"}, status=400)

                # Agregar las métricas de posición individuales manualmente con numpy (siempre 'direct' output format)
                if pos_metrics:
                    for pm in pos_metrics:
                        try:
                            if pm.startswith('cuartil_'):
                                q_num = int(pm.split('_')[1])
                                val = np.percentile(data, q_num * 25)
                                var_results[f'Cuartil {q_num}'] = f"{val:.4f}"
                            elif pm.startswith('decil_'):
                                d_num = int(pm.split('_')[1])
                                val = np.percentile(data, d_num * 10)
                                var_results[f'Decil {d_num}'] = f"{val:.4f}"
                            elif pm.startswith('percentil_'):
                                p_num = int(pm.split('_')[1])
                                val = np.percentile(data, p_num)
                                var_results[f'Percentil {p_num}'] = f"{val:.4f}"
                        except Exception as e:
                            var_results[pm] = f"Error: {str(e)}"
                
                # Acumular resultados en el pivote
                for metric_name, metric_val in var_results.items():
                    # Separar tabla de frecuencias del pivot normal
                    if isinstance(metric_val, dict) and metric_val.get('__tipo__') == 'tabla_frecuencias':
                        freq_tables[target_column] = metric_val
                        continue
                    if metric_name not in results_pivot:
                        results_pivot[metric_name] = {}
                    results_pivot[metric_name][target_column] = metric_val

                # 3. Generar imagen individual de la variable
                images = generate_plots(data, chart_type=chart_type, target_column=target_column)
                chart_bytes = images['main'].getvalue()
                images_base64_list.append({
                    'target_column': target_column,
                    'chart_type': chart_type,
                    'base64': base64.b64encode(chart_bytes).decode('utf-8')
                })

            # Log action
            AnalysisLog.objects.create(
                filename=", ".join([uf.name for uf in uploaded_files]),
                metrics_requested=json.dumps(metrics),
                export_format=export_format
            )

            # 4. Guardar en sesión
            request.session['last_results_pivot'] = results_pivot
            request.session['last_data_dict'] = valid_data_for_reports
            request.session['last_chart_types'] = chart_types_for_reports
            request.session['last_layout'] = layout
            request.session['last_freq_tables'] = freq_tables

            return JsonResponse({
                'results_pivot': results_pivot,
                'freq_tables': freq_tables,
                'images': images_base64_list,
                'variables': [var['columna'] for var in variables_list]
            })

        except ValueError as ve:
            print(f"DEBUG: ValueError capturado - {str(ve)}")
            return JsonResponse({'error': str(ve)}, status=400)
        except Exception as e:
            print(f"DEBUG: Error interno no controlado - {str(e)}")
            return JsonResponse({'error': f"Error interno del servidor: {str(e)}"}, status=500)

def download_report(request, format_type):
    results_pivot = request.session.get('last_results_pivot')
    data_dict = request.session.get('last_data_dict', {})
    chart_types_dict = request.session.get('last_chart_types', {})
    layout = request.session.get('last_layout', 'horizontal')
    freq_tables = request.session.get('last_freq_tables', {})

    if not results_pivot:
        return JsonResponse({'error': 'No hay datos en sesión para generar el reporte.'}, status=400)

    try:
        if format_type == 'pdf':
            pdf_bytes = generate_pdf_report(results_pivot, data_dict, chart_types_dict, layout, freq_tables)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="reporte_estadistico.pdf"'
            return response
        elif format_type == 'excel':
            excel_bytes = generate_excel_report(results_pivot, data_dict, chart_types_dict, layout, freq_tables)
            response = HttpResponse(excel_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="reporte_estadistico.xlsx"'
            return response
        else:
            return JsonResponse({'error': 'Formato no válido.'}, status=400)
    except Exception as e:
        print(f"DEBUG: Error al generar reporte {format_type} - {str(e)}")
        return JsonResponse({'error': f"Error al generar el reporte: {str(e)}"}, status=500)
