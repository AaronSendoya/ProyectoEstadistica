import json
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .services.extractor import extract_numbers
from .services.statistics_engine import analyze_data
from .services.report_generator import generate_excel_report, generate_pdf_report
from .models import AnalysisLog

def index_view(request):
    if request.method == 'GET':
        return render(request, 'analyzer/index.html')

    elif request.method == 'POST':
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                print("DEBUG: No se recibió ningún archivo en request.FILES. Contenido de request.FILES:", request.FILES)
                return JsonResponse({'error': 'No se adjuntó el archivo'}, status=400)
            
            metrics = request.POST.getlist('metrics[]')
            if not metrics:
                print("DEBUG: No se recibieron métricas. Contenido de request.POST:", request.POST)
                return JsonResponse({'error': 'Selecciona al menos una métrica para analizar.'}, status=400)
                
            export_format = request.POST.get('format', 'excel')
            layout = request.POST.get('layout', 'horizontal')
            chart_type = request.POST.get('chart_type', 'bar')
            
            print(f"DEBUG: Archivo recibido: {uploaded_file.name}, Métricas recibidas: {metrics}, Formato: {export_format}, Layout: {layout}, TipoGrafico: {chart_type}")

            # 1. Extracción (Clean data)
            data = extract_numbers(uploaded_file)
            
            # 2. Motor Estadístico
            results = analyze_data(data, metrics)
            if "error" in results:
                return JsonResponse({'error': results["error"]}, status=400)

            # Log action
            AnalysisLog.objects.create(
                filename=uploaded_file.name,
                metrics_requested=json.dumps(metrics),
                export_format=export_format
            )

            # 3. Generación de Reportes
            if export_format == 'pdf':
                pdf_bytes = generate_pdf_report(results, data, layout=layout, chart_type=chart_type)
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="reporte_estadistico.pdf"'
                return response
            else:
                excel_bytes = generate_excel_report(results, data, layout=layout, chart_type=chart_type)
                response = HttpResponse(excel_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="reporte_estadistico.xlsx"'
                return response

        except ValueError as ve:
            print(f"DEBUG: ValueError capturado - {str(ve)}")
            return JsonResponse({'error': str(ve)}, status=400)
        except Exception as e:
            print(f"DEBUG: Error interno no controlado - {str(e)}")
            return JsonResponse({'error': f"Error interno del servidor: {str(e)}"}, status=500)
