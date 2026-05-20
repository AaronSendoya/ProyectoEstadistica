import json
import base64
import pandas as pd
import numpy as np
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .services.extractor import extract_numbers, get_file_info
from .services.statistics_engine import analyze_data
from .services.report_generator import generate_excel_report, generate_pdf_report, generate_plots
from .models import AnalysisLog, DocumentoTexto


def peek_file_columns(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        from .services.document_service import parse_documento_ids_from_request, build_unified_corpus
        from .services.extractor import build_txt_sheet_preview, get_file_info

        documento_ids = parse_documento_ids_from_request(request)
        all_files_info = []

        if documento_ids:
            corpus, meta = build_unified_corpus(documento_ids)
            titulo = ' + '.join(meta.get('titulos', [])[:3])
            if meta.get('document_count', 0) > 3:
                titulo += f" (+{meta['document_count'] - 3} más)"
            sheet = build_txt_sheet_preview(corpus, sheet_name=titulo or 'Corpus unificado')
            sheet['documento_ids'] = documento_ids
            sheet['corpus_meta'] = meta
            all_files_info.append(sheet)
        else:
            uploaded_files = request.FILES.getlist('files')
            if not uploaded_files:
                return JsonResponse({'error': 'No se adjuntaron archivos ni documentos seleccionados'}, status=400)
            for f in uploaded_files:
                file_info_list = get_file_info(f)
                for sheet_info in file_info_list:
                    if sheet_info.get('txt_info'):
                        sheet_info['has_content_column'] = True
                all_files_info.extend(file_info_list)

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


# ── BIBLIOTECA DE DOCUMENTOS (.txt en SQLite) ───────────────────────────────────

def api_documentos_list(request):
    """Lista todos los artículos guardados en la base de datos."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    from .services.document_service import list_documentos
    return JsonResponse({'documents': list_documentos(), 'count': DocumentoTexto.objects.count()})


def api_documentos_upload(request):
    """Sube uno o varios .txt y los persiste en DocumentoTexto."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        from .services.document_service import save_documentos_from_uploads, list_documentos
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return JsonResponse({'error': 'No se adjuntaron archivos .txt'}, status=400)
        non_txt = [f.name for f in uploaded_files if not f.name.lower().endswith('.txt')]
        if non_txt:
            return JsonResponse({
                'error': f'Solo archivos .txt en la biblioteca. Rechazados: {", ".join(non_txt)}',
            }, status=400)
        saved = save_documentos_from_uploads(uploaded_files)
        return JsonResponse({
            'success': True,
            'saved': saved,
            'documents': list_documentos(),
            'message': f'{len(saved)} documento(s) guardado(s) en la base de datos.',
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_documentos_delete(request, documento_id):
    """Elimina un documento de la biblioteca."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        doc = DocumentoTexto.objects.filter(pk=documento_id).first()
        if not doc:
            return JsonResponse({'error': 'Documento no encontrado'}, status=404)
        titulo = doc.titulo
        doc.delete()
        from .services.document_service import list_documentos
        return JsonResponse({
            'success': True,
            'message': f'Documento "{titulo}" eliminado.',
            'documents': list_documentos(),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def home_view(request):
    """Vista de inicio con dashboard resumen."""
    # Obtener estadísticas para el dashboard
    total_analisis = AnalysisLog.objects.count()
    ultimos_analisis = AnalysisLog.objects.order_by('-created_at')[:5]
    
    # Contar formatos más usados
    formatos = {}
    for log in AnalysisLog.objects.all():
        fmt = log.export_format
        formatos[fmt] = formatos.get(fmt, 0) + 1
    
    context = {
        'total_analisis': total_analisis,
        'ultimos_analisis': ultimos_analisis,
        'formatos_populares': formatos,
    }
    return render(request, 'analyzer/home.html', context)


def analysis_view(request):
    if request.method == 'GET':
        return render(request, 'analyzer/analysis.html')

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

def history_view(request):
    """Vista del historial de análisis."""
    logs = AnalysisLog.objects.order_by('-created_at')
    return render(request, 'analyzer/history.html', {'logs': logs})


def help_view(request):
    """Vista de ayuda y guía de métricas."""
    return render(request, 'analyzer/help.html')


def word_counter_view(request):
    """Vista para conteo de palabras en textos."""
    if request.method == 'GET':
        return render(request, 'analyzer/word_counter.html')

    elif request.method == 'POST':
        try:
            text = request.POST.get('text', '')
            uploaded_files = request.FILES.getlist('files')

            # Procesar archivos subidos si existen
            if uploaded_files:
                for f in uploaded_files:
                    if f.name.endswith('.txt'):
                        text += f.read().decode('utf-8') + '\n'
                    elif f.name.endswith('.docx'):
                        from docx import Document
                        doc = Document(f)
                        for para in doc.paragraphs:
                            text += para.text + '\n'

            if not text.strip():
                return JsonResponse({'error': 'No se proporcionó texto para analizar'}, status=400)

            # Análisis de palabras
            words = text.split()
            word_count = len(words)

            # Contar palabras únicas (ignorando mayúsculas/minúsculas y puntuación básica)
            import re
            clean_words = [re.sub(r'[^\w\s]', '', w).lower() for w in words]
            clean_words = [w for w in clean_words if w]
            unique_words = set(clean_words)

            from collections import Counter
            from .services.text_tokenizer import count_semantic_words
            word_freq = Counter(clean_words)
            semantic_freq = count_semantic_words(text)
            most_common = word_freq.most_common(20)
            keywords_semantic = semantic_freq.most_common(20)

            # Estadísticas adicionales
            char_count = len(text)
            char_count_no_spaces = len(text.replace(' ', '').replace('\n', ''))
            sentence_count = len([s for s in text.split('.') if s.strip()])
            paragraph_count = len([p for p in text.split('\n\n') if p.strip()])

            # Longitud promedio de palabras
            avg_word_length = sum(len(w) for w in clean_words) / len(clean_words) if clean_words else 0

            result = {
                'word_count': word_count,
                'unique_words': len(unique_words),
                'char_count': char_count,
                'char_count_no_spaces': char_count_no_spaces,
                'sentence_count': sentence_count,
                'paragraph_count': paragraph_count,
                'avg_word_length': round(avg_word_length, 2),
                'most_common': most_common,
                'keywords_semantic': keywords_semantic,
                'text_preview': text[:500] + '...' if len(text) > 500 else text
            }

            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


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


# ── NUEVOS MÓDULOS DE MODELADO PROBABILÍSTICO Y DECISIONES ────────────────────────

def problem_tree_view(request):
    """Renderiza la vista interactiva del Árbol de Problemas."""
    return render(request, 'analyzer/problem_tree.html')


def bayesian_network_view(request):
    """Renderiza la vista interactiva de la Red Bayesiana."""
    return render(request, 'analyzer/bayesian_network.html')


def markov_chains_view(request):
    """Renderiza la vista interactiva de las Cadenas de Markov."""
    return render(request, 'analyzer/markov_chains.html')


# ── CADENAS DE MARKOV API ────────────────────────────────────────────────────────

def api_markov_calculate(request):
    """Realiza proyecciones, convergencia y estado estacionario desde una matriz manual."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body)
        states = data.get('states')
        matrix = data.get('matrix')
        initial_dist = data.get('initial_dist')
        steps = int(data.get('steps', 10))

        if not states or not matrix or not initial_dist:
            return JsonResponse({'error': 'Faltan parámetros requeridos (estados, matriz o vector inicial).'}, status=400)

        from .services.markov_engine import (
            predict_steps,
            calculate_steady_state,
            simulate_monte_carlo,
            build_top_transitions_list,
            TOP_N_KEYWORDS,
        )

        if len(states) > TOP_N_KEYWORDS:
            return JsonResponse({
                'error': f'Máximo {TOP_N_KEYWORDS} estados permitidos en el modelo manual.',
            }, status=400)

        projections = []
        for s in range(steps + 1):
            proj = predict_steps(matrix, initial_dist, s)
            projections.append(proj)

        steady_state = calculate_steady_state(matrix)
        simulated_path = simulate_monte_carlo(matrix, states, states[0], 200)

        request.session['last_markov_states'] = states
        request.session['last_markov_matrix'] = matrix
        request.session['last_markov_steps'] = steps
        request.session['last_markov_projections'] = projections
        request.session['last_markov_steady_state'] = steady_state
        request.session['last_markov_simulated_path'] = simulated_path

        top_transitions = build_top_transitions_list(states, matrix, limit=10)

        return JsonResponse({
            'projections': projections,
            'steady_state': steady_state,
            'simulated_path': simulated_path[:50],
            'transitions': top_transitions,
            'states': states,
            'matrix': matrix,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_markov_estimate(request):
    """Estima matriz de transición desde documentos guardados, .txt o Excel/Word."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        target_column = request.POST.get('column')
        steps = int(request.POST.get('steps', 10))

        from .services.document_service import (
            corpus_from_request_or_file,
            parse_documento_ids_from_request,
        )
        from .services.extractor import extract_categorical_column, extract_keyword_sequence_from_text
        from .services.markov_engine import (
            estimate_transition_matrix,
            predict_steps,
            calculate_steady_state,
            simulate_monte_carlo,
            build_top_transitions_list,
            TOP_N_KEYWORDS,
        )

        documento_ids = parse_documento_ids_from_request(request)
        uploaded_file = request.FILES.get('file')

        if documento_ids:
            text_corpus, corpus_meta = corpus_from_request_or_file(request)
            sequence = extract_keyword_sequence_from_text(text_corpus)
            source_meta = corpus_meta
        elif uploaded_file and uploaded_file.name.lower().endswith('.txt'):
            uploaded_file.seek(0)
            text_corpus = uploaded_file.read().decode('utf-8', errors='ignore')
            sequence = extract_keyword_sequence_from_text(text_corpus)
            source_meta = {'source': 'upload', 'titulos': [uploaded_file.name]}
        elif uploaded_file:
            sequence = extract_categorical_column(uploaded_file, target_column)
            source_meta = {'source': 'file', 'titulos': [uploaded_file.name]}
        else:
            return JsonResponse({'error': 'Seleccione artículos guardados o suba un archivo.'}, status=400)

        if not sequence or len(sequence) < 2:
            return JsonResponse({'error': 'La secuencia debe tener al menos dos elementos para estimar transiciones.'}, status=400)

        estimation = estimate_transition_matrix(sequence, top_n=TOP_N_KEYWORDS)
        states = estimation['states']
        matrix = estimation['matrix']
        filter_meta = {**estimation.get('meta', {}), **source_meta}

        # 3. Vector inicial uniforme
        n = len(states)
        initial_dist = [1.0 / n] * n

        # 4. Proyecciones
        projections = []
        for s in range(steps + 1):
            proj = predict_steps(matrix, initial_dist, s)
            projections.append(proj)

        # 5. Estado Estacionario
        steady_state = calculate_steady_state(matrix)

        # 6. Simulación Monte Carlo
        simulated_path = simulate_monte_carlo(matrix, states, states[0], 200)

        # Guardar en sesión
        request.session['last_markov_states'] = states
        request.session['last_markov_matrix'] = matrix
        request.session['last_markov_steps'] = steps
        request.session['last_markov_projections'] = projections
        request.session['last_markov_steady_state'] = steady_state
        request.session['last_markov_simulated_path'] = simulated_path

        top_transitions = build_top_transitions_list(states, matrix, limit=10)
        top_transitions_full = build_top_transitions_list(states, matrix, limit=50)

        return JsonResponse({
            'states': states,
            'matrix': matrix,
            'projections': projections,
            'steady_state': steady_state,
            'simulated_path': simulated_path[:50],
            'sequence_preview': sequence[:20],
            'transitions': top_transitions,
            'transitions_graph': top_transitions_full,
            'meta': filter_meta,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_file_stats(request):
    """Calcula estadísticas descriptivas básicas para una columna dada en un archivo Excel o Word."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        uploaded_file = request.FILES.get('file')
        target_column = request.POST.get('column')
        
        if not uploaded_file or not target_column:
            return JsonResponse({'error': 'Se requiere un archivo y una columna.'}, status=400)
            
        from .services.extractor import extract_numbers
        
        uploaded_file.seek(0)
        data = extract_numbers(uploaded_file, target_column)
        
        if not data:
            return JsonResponse({'error': f"No se encontraron datos numéricos válidos en la columna '{target_column}'."}, status=400)
            
        import numpy as np
        arr = np.array(data)
        stats = {
            'n': len(arr),
            'mean': float(np.mean(arr)),
            'std': float(np.std(arr)) if len(arr) > 1 else 0.0,
            'min': float(np.min(arr)),
            'max': float(np.max(arr)),
        }
        return JsonResponse({'stats': stats})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── RED BAYESIANA API ────────────────────────────────────────────────────────────

def api_bayesian_keywords(request):
    """Palabras clave desde documentos guardados o .txt para la Red Bayesiana."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        from .services.document_service import corpus_from_request_or_file
        from .services.extractor import extract_top_keywords
        from .services.bayesian_engine import build_structured_network_schema

        text_content, meta = corpus_from_request_or_file(request, require_txt=True)
        keywords = extract_top_keywords(text_content)
        schema = build_structured_network_schema(keywords[:4])

        return JsonResponse({
            'keywords': keywords,
            'schema': schema,
            'corpus_meta': meta,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_bayesian_learn(request):
    """Aprende las tablas de probabilidad condicional (CPT) desde un archivo de datos Excel, Word o texto plano."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        uploaded_file = request.FILES.get('file')
        nodes_json = request.POST.get('nodes')
        edges_json = request.POST.get('edges')
        selected_keywords_json = request.POST.get('selected_keywords', '[]')

        if not nodes_json or not edges_json:
            return JsonResponse({'error': 'Se requiere esquema de nodos y aristas.'}, status=400)

        nodes = json.loads(nodes_json)
        edges = json.loads(edges_json)
        selected_keywords = json.loads(selected_keywords_json)

        import pandas as pd
        from .services.document_service import (
            corpus_from_request_or_file,
            parse_documento_ids_from_request,
        )

        documento_ids = parse_documento_ids_from_request(request)
        used_txt_corpus = False

        if documento_ids or (uploaded_file and uploaded_file.name.lower().endswith('.txt')):
            from .services.extractor import prepare_bayesian_txt_dataframe, extract_text_metrics
            text_content, _ = corpus_from_request_or_file(request, require_txt=True)
            used_txt_corpus = True
            if selected_keywords:
                df = prepare_bayesian_txt_dataframe(text_content, selected_keywords)
            else:
                df = extract_text_metrics(text_content)
                df['Total_Palabras_Cat'] = pd.cut(df['Total_Palabras'], bins=3, labels=['Bajo', 'Medio', 'Alto']).astype(str)
                df['Densidad_Léxica_Cat'] = pd.cut(df['Densidad_Léxica'], bins=3, labels=['Baja', 'Media', 'Alta']).astype(str)
                df['Total_Oraciones_Cat'] = pd.cut(df['Total_Oraciones'], bins=3, labels=['Pocas', 'Moderadas', 'Muchas']).astype(str)
                df = df.rename(columns={
                    'Total_Palabras_Cat': 'Densidad_Contenido',
                    'Densidad_Léxica_Cat': 'Complejidad_Léxica',
                    'Total_Oraciones_Cat': 'Estructura_Oracional',
                })
        elif uploaded_file and uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file and uploaded_file.name.lower().endswith(('.doc', '.docx')):
            from .services.extractor import extract_docx_dataframes
            dfs = extract_docx_dataframes(uploaded_file)
            if not dfs:
                return JsonResponse({'error': 'El documento Word no contiene tablas o datos válidos.'}, status=400)
            first_key = list(dfs.keys())[0]
            df = dfs[first_key]
        else:
            return JsonResponse({
                'error': 'Seleccione artículos guardados, suba .txt o use Excel/Word.',
            }, status=400)

        from .services.bayesian_engine import learn_cpts_from_dataframe
        cpts = learn_cpts_from_dataframe(df, nodes, edges)

        # Convertir llaves tuple a string para envío JSON
        cpts_serializable = {}
        for node_name, cpt_info in cpts.items():
            str_table = {}
            for combo, prob in cpt_info['table'].items():
                str_table[str(combo)] = prob
            cpts_serializable[node_name] = {
                'variables': cpt_info['variables'],
                'table': str_table
            }

        response_data = {'cpts': cpts_serializable}
        if used_txt_corpus and selected_keywords:
            from .services.bayesian_engine import build_structured_network_schema
            response_data['schema'] = build_structured_network_schema(selected_keywords)

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_bayesian_infer(request):
    """Calcula inferencia exacta en base al grafo, CPTs y evidencias proporcionadas."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body)
        nodes = data.get('nodes')
        edges = data.get('edges')
        cpts = data.get('cpts')
        evidence = data.get('evidence', {})
        targets = data.get('targets', [])

        if not nodes or not cpts or not targets:
            return JsonResponse({'error': 'Faltan parámetros requeridos para la inferencia.'}, status=400)

        from .services.bayesian_engine import run_variable_elimination
        
        results = {}
        for target in targets:
            prob_dist = run_variable_elimination(nodes, edges, cpts, evidence, target)
            results[target] = prob_dist

        # Guardar en sesión para exportaciones PDF
        request.session['last_bayesian_nodes'] = nodes
        request.session['last_bayesian_edges'] = edges
        request.session['last_bayesian_cpts'] = cpts
        request.session['last_bayesian_evidence'] = evidence
        request.session['last_bayesian_results'] = results

        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── ÁRBOL DE PROBLEMAS API ───────────────────────────────────────────────────────

def api_problem_tree_analyze(request):
    """
    Analiza un archivo de texto para detectar causas, efectos y estructura jerárquica.
    Devuelve un JSON con el árbol de problemas estructurado para visualización.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        from .services.document_service import corpus_from_request_or_file
        from .services.problem_tree_engine import analyze_text_for_problem_tree

        text_content, corpus_meta = corpus_from_request_or_file(request, require_txt=True)
        tree_structure = analyze_text_for_problem_tree(text_content)

        request.session['last_problem_tree'] = tree_structure

        return JsonResponse({
            'success': True,
            'tree': tree_structure,
            'corpus_meta': corpus_meta,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── REPORTES PDF ESPECIALIZADOS ──────────────────────────────────────────────────

def problem_tree_pdf(request):
    """Genera y descarga el reporte PDF del Árbol de Problemas."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            problem_text = data.get('problem_text', 'Problema Central')
            causes = data.get('causes', [])
            effects = data.get('effects', [])
            linked_data = data.get('linked_data', None)
            
            # Si hay variables vinculadas en la sesión y no se enviaron, podríamos cruzarlas
            from .services.report_generator import generate_problem_tree_pdf
            pdf_bytes = generate_problem_tree_pdf(problem_text, causes, effects, linked_data)
            
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="arbol_de_problemas.pdf"'
            return response
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Solo se permite método POST.'}, status=405)


def bayesian_network_pdf(request):
    """Genera y descarga el reporte PDF de la Red Bayesiana."""
    try:
        nodes = request.session.get('last_bayesian_nodes')
        edges = request.session.get('last_bayesian_edges', [])
        cpts = request.session.get('last_bayesian_cpts')
        evidence = request.session.get('last_bayesian_evidence', {})
        results = request.session.get('last_bayesian_results')

        if not nodes or not cpts or not results:
            # Fallback en caso de que expiren los datos de sesión, intentar leer desde JSON en POST
            if request.method == 'POST':
                data = json.loads(request.body)
                nodes = data.get('nodes')
                edges = data.get('edges', [])
                cpts = data.get('cpts')
                evidence = data.get('evidence', {})
                results = data.get('results')
            else:
                return HttpResponse("No hay datos de análisis Bayesiano disponibles para exportar.", status=400)

        from .services.report_generator import generate_bayesian_network_pdf
        pdf_bytes = generate_bayesian_network_pdf(nodes, edges, cpts, evidence, results)
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="analisis_red_bayesiana.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)


def markov_chains_pdf(request):
    """Genera y descarga el reporte PDF de Cadenas de Markov."""
    try:
        states = request.session.get('last_markov_states')
        matrix = request.session.get('last_markov_matrix')
        steps = request.session.get('last_markov_steps', 10)
        projections = request.session.get('last_markov_projections')
        steady_state = request.session.get('last_markov_steady_state')
        simulated_path = request.session.get('last_markov_simulated_path')

        if not states or not matrix or not steady_state:
            if request.method == 'POST':
                data = json.loads(request.body)
                states = data.get('states')
                matrix = data.get('matrix')
                steps = data.get('steps', 10)
                projections = data.get('projections')
                steady_state = data.get('steady_state')
                simulated_path = data.get('simulated_path')
            else:
                return HttpResponse("No hay datos de Cadenas de Markov disponibles para exportar.", status=400)

        from .services.report_generator import generate_markov_chains_pdf
        pdf_bytes = generate_markov_chains_pdf(states, matrix, steps, projections, steady_state, simulated_path)
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_cadenas_markov.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error al generar PDF: {str(e)}", status=500)

