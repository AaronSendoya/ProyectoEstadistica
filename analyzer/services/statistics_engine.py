import numpy as np
import scipy.stats as stats

def calc_media(data, detail_level):
    n = len(data)
    sum_x = np.sum(data)
    res = round(float(np.mean(data)), 4)
    if detail_level == 'direct': return res
    if detail_level == 'partial': return f"Fórmula: Σx / N\nResultado: {res}"
    return f"Fórmula: Σx / N\nSustitución: {sum_x:.4f} / {n}\nResultado: {res}"

def calc_mediana(data, detail_level):
    res = round(float(np.median(data)), 4)
    n = len(data)
    if detail_level == 'direct': return res
    if detail_level == 'partial': return f"Fórmula: Punto medio de datos ordenados\nResultado: {res}"
    return f"Fórmula: Punto medio de datos ordenados\nSustitución: Pos. {n/2 if n%2==0 else (n+1)/2}\nResultado: {res}"

def calc_mode_detailed(data, detail_level):
    modes_result = stats.mode(data, keepdims=True)
    mode_val = modes_result.mode[0]
    res_val = mode_val if not np.isnan(mode_val) else "N/A"
    res = str(round(float(res_val), 4)) if isinstance(res_val, (int, float, np.number)) else "N/A"
    if detail_level == 'direct': return res
    if detail_level == 'partial': return f"Fórmula: Valor con mayor frecuencia\nResultado: {res}"
    return f"Fórmula: Valor con mayor frecuencia\nSustitución: Observando frecuencias\nResultado: {res}"

def calc_rango(data, detail_level):
    min_x, max_x = np.min(data), np.max(data)
    res = round(float(max_x - min_x), 4)
    if detail_level == 'direct': return res
    if detail_level == 'partial': return f"Fórmula: Max - Min\nResultado: {res}"
    return f"Fórmula: Max - Min\nSustitución: {max_x} - {min_x}\nResultado: {res}"

def calc_varianza(data, detail_level):
    n = len(data)
    res = round(float(np.var(data, ddof=1)), 4)
    if detail_level == 'direct': return res
    if detail_level == 'partial': return f"Fórmula: Σ(x - μ)² / (N-1)\nResultado: {res}"
    return f"Fórmula: Σ(x - μ)² / (N-1)\nSustitución: Sumatoria distancias al cuadrado / {n-1}\nResultado: {res}"

def calc_desviacion(data, detail_level):
    n = len(data)
    var = np.var(data, ddof=1)
    res = round(float(np.std(data, ddof=1)), 4)
    if detail_level == 'direct': return res
    if detail_level == 'partial': return f"Fórmula: √(Σ(x - μ)² / (N-1))\nResultado: {res}"
    return f"Fórmula: √(Σ(x - μ)² / (N-1))\nSustitución: √({var:.4f})\nResultado: {res}"

def calc_quartiles(data):
    return f"Q1: {np.percentile(data, 25):.2f}, Q2: {np.median(data):.2f}, Q3: {np.percentile(data, 75):.2f}"

def calc_deciles(data):
    deciles = [np.percentile(data, i*10) for i in range(1, 10)]
    return ", ".join([f"D{i}: {val:.2f}" for i, val in enumerate(deciles, 1)])

def calc_10th_percentile(data):
    percentiles = [np.percentile(data, i) for i in range(1, 100)]
    lines = []
    chunk = []
    for i, val in enumerate(percentiles, 1):
        chunk.append(f"P{i}: {val:.2f}")
        if len(chunk) == 10 or i == 99:
            lines.append(", ".join(chunk))
            chunk = []
    return "\n".join(lines)

def calc_coef_variation(data):
    mean_val = np.mean(data)
    if mean_val == 0:
        return "N/A (Media es 0)"
    return str(round((np.std(data, ddof=1) / mean_val) * 100, 2)) + " %"

def calc_random_variable(data):
    unique_vals = np.unique(data)
    if len(unique_vals) <= 20:
        return "Variable Discreta (Pocos valores únicos)"
    return "Variable Continua (Muchos valores fraccionarios/únicos)"

def calc_sample_space(data):
    unique_vals = np.unique(data)
    if len(unique_vals) > 10:
        return f"{{{', '.join(map(str, unique_vals[:5]))}, ..., {', '.join(map(str, unique_vals[-5:]))}}} (Espacio: {len(unique_vals)} elementos)"
    return f"{{{', '.join(map(str, unique_vals))}}}"

def calc_harmonic_mean(data):
    positive_data = [x for x in data if x > 0]
    if not positive_data:
        return "N/A (Requiere al menos 1 dato estrictamente positivo)"
    return stats.hmean(positive_data)

def calc_geometric_mean(data):
    positive_data = [x for x in data if x > 0]
    if not positive_data:
        return "N/A (Requiere al menos 1 dato estrictamente positivo)"
    return stats.gmean(positive_data)

# Patron Registry
REGISTRY = {
    'media': calc_media,
    'mediana': calc_mediana,
    'moda': calc_mode_detailed,
    'rango': calc_rango,
    'varianza': calc_varianza,
    'desviacion_estandar': calc_desviacion,
    'media_armonica': lambda d, dl: calc_harmonic_mean(d) if isinstance(calc_harmonic_mean(d), str) else round(calc_harmonic_mean(d), 4),
    'media_geometrica': lambda d, dl: calc_geometric_mean(d) if isinstance(calc_geometric_mean(d), str) else round(calc_geometric_mean(d), 4),
    'cuartiles': lambda d, dl: calc_quartiles(d),
    'deciles': lambda d, dl: calc_deciles(d),
    'percentiles': lambda d, dl: calc_10th_percentile(d),
    'coeficiente_variacion': lambda d, dl: calc_coef_variation(d),
    'variables_aleatorias': lambda d, dl: calc_random_variable(d),
    'espacio_muestral': lambda d, dl: calc_sample_space(d)
}

def analyze_data(data, requested_metrics, detail_level='direct'):
    """
    Motor estadístico: calcula cada una de las métricas solicitadas devolviendo un diccionario
    llave: valor para el reporte.
    """
    if not data:
        return {"error": "No hay datos válidos para procesar."}
    
    results = {}
    for metric in requested_metrics:
        if metric in REGISTRY:
            try:
                results[metric] = REGISTRY[metric](data, detail_level)
            except Exception as e:
                results[metric] = f"Error computacional: {str(e)}"
    return results
