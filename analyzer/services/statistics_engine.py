import numpy as np
import scipy.stats as stats
import math

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

# ── MEDIAS MÓVILES ──────────────────────────────────────────────────
def calc_media_movil(data, detail_level, window=3):
    """
    Calcula la Media Móvil Simple (SMA) con una ventana deslizante.
    MM_i = (x_i + x_{i+1} + ... + x_{i+k-1}) / k
    """
    n = len(data)
    if n < window:
        return f"N/A (Se necesitan al menos {window} datos, tienes {n})"
    
    # Calcular media móvil con numpy
    arr = np.array(data, dtype=float)
    cumsum = np.cumsum(arr)
    cumsum = np.insert(cumsum, 0, 0)
    sma = (cumsum[window:] - cumsum[:-window]) / window
    sma_rounded = [round(float(v), 4) for v in sma]
    total_sma = len(sma_rounded)
    
    if detail_level == 'direct':
        # Mostrar los valores de forma compacta
        if total_sma <= 10:
            return ", ".join([f"MM{i+1}: {v}" for i, v in enumerate(sma_rounded)])
        else:
            first5 = ", ".join([f"MM{i+1}: {v}" for i, v in enumerate(sma_rounded[:5])])
            last5 = ", ".join([f"MM{i+1}: {v}" for i, v in enumerate(sma_rounded[-5:], total_sma-5)])
            return f"{first5}, ..., {last5}  ({total_sma} valores)"
    
    if detail_level == 'partial':
        return (f"Fórmula: MM_i = (x_i + x_{{i+1}} + ... + x_{{i+{window-1}}}) / {window}\n"
                f"Ventana (k): {window}\n"
                f"Valores totales calculados: {total_sma}\n"
                f"Primer MM: {sma_rounded[0]} | Último MM: {sma_rounded[-1]}")
    
    # Completo: mostrar TODOS los valores con su procedimiento
    lines = [f"Fórmula: MM_i = (x_i + x_{{i+1}} + ... + x_{{i+{window-1}}}) / {window}"]
    lines.append(f"Ventana (k): {window} | Total de datos: {n} | Total de MM calculadas: {total_sma}")
    lines.append("")
    for i in range(total_sma):
        window_vals = data[i:i+window]
        suma = round(sum(window_vals), 4)
        vals_str = ' + '.join([str(round(v, 4)) for v in window_vals])
        lines.append(f"MM_{i+1} = ({vals_str}) / {window} = {suma} / {window} = {sma_rounded[i]}")
    return "\n".join(lines)

# ── MEDIDAS DE FORMA ────────────────────────────────────────────────
def calc_asimetria(data, detail_level):
    """
    Calcula el Coeficiente de Asimetría (Skewness) de Fisher.
    Positivo = cola derecha más larga, Negativo = cola izquierda más larga.
    """
    n = len(data)
    if n < 3:
        return f"N/A (Se necesitan al menos 3 datos, tienes {n})"
    
    skew_val = round(float(stats.skew(data, bias=False)), 4)
    
    # Interpretación
    if abs(skew_val) < 0.5:
        interp = "Distribución aproximadamente simétrica"
    elif skew_val >= 0.5:
        interp = "Asimetría positiva (cola derecha más larga)"
    else:
        interp = "Asimetría negativa (cola izquierda más larga)"
    
    if detail_level == 'direct':
        return f"{skew_val} ({interp})"
    
    mean_val = np.mean(data)
    std_val = np.std(data, ddof=1)
    
    if detail_level == 'partial':
        return f"Fórmula: γ₁ = [n/((n-1)(n-2))] · Σ[(xᵢ - x̄)/s]³\nResultado: {skew_val}\nInterpretación: {interp}"
    
    return (f"Fórmula: γ₁ = [n/((n-1)(n-2))] · Σ[(xᵢ - x̄)/s]³\n"
            f"Sustitución: n={n}, x̄={round(mean_val,4)}, s={round(std_val,4)}\n"
            f"Resultado: {skew_val}\n"
            f"Interpretación: {interp}")

def calc_curtosis(data, detail_level):
    """
    Calcula la Curtosis (Kurtosis) en exceso (Fisher).
    >0 = Leptocúrtica (puntiaguda), <0 = Platicúrtica (achatada), ≈0 = Mesocúrtica (normal).
    """
    n = len(data)
    if n < 4:
        return f"N/A (Se necesitan al menos 4 datos, tienes {n})"
    
    kurt_val = round(float(stats.kurtosis(data, bias=False)), 4)
    
    # Interpretación
    if abs(kurt_val) < 0.5:
        interp = "Mesocúrtica (forma similar a la normal)"
    elif kurt_val >= 0.5:
        interp = "Leptocúrtica (más puntiaguda que la normal, colas pesadas)"
    else:
        interp = "Platicúrtica (más achatada que la normal, colas ligeras)"
    
    if detail_level == 'direct':
        return f"{kurt_val} ({interp})"
    
    mean_val = np.mean(data)
    std_val = np.std(data, ddof=1)
    
    if detail_level == 'partial':
        return f"Fórmula: κ = [n(n+1)/((n-1)(n-2)(n-3))] · Σ[(xᵢ - x̄)/s]⁴ - 3(n-1)²/((n-2)(n-3))\nResultado: {kurt_val}\nInterpretación: {interp}"
    
    return (f"Fórmula: κ = [n(n+1)/((n-1)(n-2)(n-3))] · Σ[(xᵢ - x̄)/s]⁴ - 3(n-1)²/((n-2)(n-3))\n"
            f"Sustitución: n={n}, x̄={round(mean_val,4)}, s={round(std_val,4)}\n"
            f"Resultado: {kurt_val}\n"
            f"Interpretación: {interp}")

# ── TABLA DE DISTRIBUCIÓN DE FRECUENCIAS ────────────────────────────
def calc_tabla_frecuencias(data, detail_level):
    """
    Genera una tabla de distribución de frecuencias con:
    - Intervalo de clase
    - Marca de clase (xi)
    - Frecuencia absoluta (fi)
    - Frecuencia absoluta acumulada (Fi)
    - Frecuencia relativa (hi)
    - Frecuencia relativa acumulada (Hi)
    Retorna un diccionario con la estructura de la tabla para renderizado especial.
    """
    n = len(data)
    if n < 2:
        return "N/A (Se necesitan al menos 2 datos)"
    
    arr = np.array(data, dtype=float)
    
    # Número de clases usando regla de Sturges: k = 1 + 3.322 * log10(n)
    k = max(3, int(math.ceil(1 + 3.322 * math.log10(n))))
    
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))
    rango = max_val - min_val
    
    # Evitar amplitud 0 si todos los datos son iguales
    if rango == 0:
        amplitud = 1.0
    else:
        amplitud = round(rango / k, 4)
        # Redondear amplitud hacia arriba para cubrir todo el rango
        if amplitud * k < rango:
            amplitud = round(rango / k + 0.0001, 4)
    
    tabla = []
    fi_acum = 0
    hi_acum = 0.0
    
    for i in range(k):
        li = round(min_val + i * amplitud, 4)       # Límite inferior
        ls = round(min_val + (i + 1) * amplitud, 4) # Límite superior
        xi = round((li + ls) / 2, 4)                 # Marca de clase
        
        # Contar frecuencia absoluta (el último intervalo incluye el extremo superior)
        if i == k - 1:
            fi = int(np.sum((arr >= li) & (arr <= ls)))
        else:
            fi = int(np.sum((arr >= li) & (arr < ls)))
        
        fi_acum += fi
        hi = round(fi / n, 4)
        hi_acum = round(hi_acum + hi, 4)
        
        tabla.append({
            'intervalo': f"[{li}, {ls})",
            'xi': xi,
            'fi': fi,
            'Fi': fi_acum,
            'hi': hi,
            'Hi': min(hi_acum, 1.0)  # Asegurar que no exceda 1.0 por redondeo
        })
    
    # Corregir el último intervalo para que sea cerrado [li, ls]
    if tabla:
        last = tabla[-1]
        last['intervalo'] = last['intervalo'][:-1] + ']'
    
    # Retornar como estructura especial que se renderizará como tabla
    return {
        '__tipo__': 'tabla_frecuencias',
        'k': k,
        'amplitud': amplitud,
        'n': n,
        'rango': round(rango, 4),
        'filas': tabla
    }


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
    'espacio_muestral': lambda d, dl: calc_sample_space(d),
    # ── Nuevas métricas ──
    'media_movil': calc_media_movil,
    'asimetria': calc_asimetria,
    'curtosis': calc_curtosis,
    'tabla_frecuencias': calc_tabla_frecuencias,
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
