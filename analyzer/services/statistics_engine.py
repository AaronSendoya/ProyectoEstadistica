import numpy as np
import scipy.stats as stats

def calc_mode(data):
    modes_result = stats.mode(data, keepdims=True)
    mode_val = modes_result.mode[0]
    return mode_val if not np.isnan(mode_val) else "N/A"

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
    'media': lambda d: round(float(np.mean(d)), 4),
    'mediana': lambda d: round(float(np.median(d)), 4),
    'moda': lambda d: str(round(float(calc_mode(d)), 4)) if isinstance(calc_mode(d), (int, float, np.number)) else "N/A",
    'rango': lambda d: round(float(np.max(d) - np.min(d)), 4),
    'varianza': lambda d: round(float(np.var(d, ddof=1)), 4),
    'desviacion_estandar': lambda d: round(float(np.std(d, ddof=1)), 4),
    'media_armonica': lambda d: calc_harmonic_mean(d) if isinstance(calc_harmonic_mean(d), str) else round(calc_harmonic_mean(d), 4),
    'media_geometrica': lambda d: calc_geometric_mean(d) if isinstance(calc_geometric_mean(d), str) else round(calc_geometric_mean(d), 4),
    'cuartiles': calc_quartiles,
    'deciles': calc_deciles,
    'percentiles': calc_10th_percentile,
    'coeficiente_variacion': calc_coef_variation,
    'variables_aleatorias': calc_random_variable,
    'espacio_muestral': calc_sample_space
}

def analyze_data(data, requested_metrics):
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
                results[metric] = REGISTRY[metric](data)
            except Exception as e:
                results[metric] = f"Error computacional: {str(e)}"
    return results
