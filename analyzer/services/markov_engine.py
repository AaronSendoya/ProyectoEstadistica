import numpy as np
from collections import Counter

# Máximo de estados en la cadena (evita explosión combinatoria N×N en .txt largos)
TOP_N_KEYWORDS = 20
MIN_SEQUENCE_LENGTH = 2
EDGE_DISPLAY_THRESHOLD = 0.05


def get_top_keyword_states(sequence, top_n=TOP_N_KEYWORDS):
    """Devuelve las top_n palabras más frecuentes en la secuencia."""
    if not sequence:
        return []
    return [word for word, _ in Counter(sequence).most_common(top_n)]


def filter_sequence_to_top_keywords(sequence, top_n=TOP_N_KEYWORDS):
    """
    Filtra la secuencia para conservar solo transiciones entre palabras del Top N.
    Returns:
        tuple: (secuencia_filtrada, lista_top_keywords)
    """
    top_keywords = get_top_keyword_states(sequence, top_n)
    if not top_keywords:
        return [], []
    allowed = set(top_keywords)
    filtered = [w for w in sequence if w in allowed]
    return filtered, top_keywords


def build_top_transitions_list(states, matrix, threshold=EDGE_DISPLAY_THRESHOLD, limit=10):
    """Lista las transiciones con P > threshold, ordenadas por probabilidad (máx. limit)."""
    transitions = []
    for i, from_s in enumerate(states):
        for j, to_s in enumerate(states):
            prob = float(matrix[i][j])
            if prob >= threshold:
                transitions.append({
                    'from': from_s,
                    'to': to_s,
                    'probability': round(prob, 4),
                })
    transitions.sort(key=lambda x: x['probability'], reverse=True)
    return transitions[:limit]


def estimate_transition_matrix(sequence, top_n=TOP_N_KEYWORDS):
    """
    Estima la matriz de transición desde una secuencia de estados observados.
    Aplica filtro Top N Keywords antes de construir la matriz (máx. 20×20).

    Args:
        sequence (list): Lista de valores categóricos (estados/palabras clave).
        top_n (int): Número máximo de estados (palabras clave más frecuentes).
    Returns:
        dict: states, matrix, counts, meta (estadísticas de filtrado)
    """
    if not sequence or len(sequence) < MIN_SEQUENCE_LENGTH:
        raise ValueError("La secuencia debe tener al menos dos observaciones.")

    original_len = len(sequence)
    vocab_before = len(set(sequence))

    filtered, top_keywords = filter_sequence_to_top_keywords(sequence, top_n)
    if len(filtered) < MIN_SEQUENCE_LENGTH:
        raise ValueError(
            f"Tras filtrar a las {top_n} palabras clave principales, "
            "quedan menos de 2 observaciones. Usa un texto más extenso."
        )

    states = sorted(top_keywords)
    n = len(states)
    state_to_idx = {state: idx for idx, state in enumerate(states)}

    counts = np.ones((n, n))

    for i in range(len(filtered) - 1):
        curr_state = filtered[i]
        next_state = filtered[i + 1]
        if curr_state in state_to_idx and next_state in state_to_idx:
            counts[state_to_idx[curr_state], state_to_idx[next_state]] += 1

    matrix = np.zeros((n, n))
    for i in range(n):
        row_sum = counts[i].sum()
        if row_sum > 0:
            matrix[i] = counts[i] / row_sum
        else:
            matrix[i, i] = 1.0

    return {
        'states': states,
        'matrix': matrix.tolist(),
        'counts': counts.tolist(),
        'meta': {
            'top_n': top_n,
            'original_sequence_length': original_len,
            'filtered_sequence_length': len(filtered),
            'vocabulary_size_before': vocab_before,
            'states_count': n,
            'filtered': vocab_before > n or original_len != len(filtered),
        },
    }


def predict_steps(matrix, initial_dist, steps):
    """
    Proyecta la distribución de estados después de N pasos.
    
    Args:
        matrix (list of lists): Matriz de transición NxN
        initial_dist (list): Distribución inicial 1xN
        steps (int): Número de pasos a proyectar
    Returns:
        list: Distribución de probabilidad proyectada
    """
    P = np.array(matrix)
    x = np.array(initial_dist)
    
    # Validar dimensiones
    if P.shape[0] != P.shape[1]:
        raise ValueError("La matriz de transición debe ser cuadrada.")
    if len(x) != P.shape[0]:
        raise ValueError("El vector de estado inicial debe coincidir con las dimensiones de la matriz.")
        
    # Calcular P^n
    P_n = np.linalg.matrix_power(P, steps)
    result = x.dot(P_n)
    return result.tolist()


def calculate_steady_state(matrix):
    """
    Calcula la distribución estacionaria (estado estable) de una cadena de Markov.
    Encuentra el vector de probabilidad π tal que π * P = π.
    
    Args:
        matrix (list of lists): Matriz de transición NxN
    Returns:
        list: Distribución de probabilidad estacionaria
    """
    P = np.array(matrix)
    n = P.shape[0]
    
    if P.shape[0] != P.shape[1]:
        raise ValueError("La matriz de transición debe ser cuadrada.")
        
    # Usar autovectores de P^T para encontrar eigenvectores de izquierda
    try:
        eigenvalues, eigenvectors = np.linalg.eig(P.T)
        
        # Encontrar el autovector correspondiente a autovalor = 1
        idx = np.argmin(np.abs(eigenvalues - 1.0))
        
        # Verificar que el autovalor más cercano sea efectivamente ~1
        if np.abs(eigenvalues[idx] - 1.0) > 1e-4:
            raise ValueError("No se encontró un estado estacionario estable.")
            
        steady = np.real(eigenvectors[:, idx])
        
        # Normalizar para que sum = 1
        steady = steady / np.sum(steady)
        
        # Asegurar valores positivos
        steady = np.abs(steady)
        steady = steady / np.sum(steady)
        
        return steady.tolist()
    except Exception as e:
        # Método alternativo: Iteración de Potencia (aproximación)
        try:
            temp = np.ones(n) / n
            for _ in range(200):
                next_temp = temp.dot(P)
                if np.allclose(temp, next_temp, atol=1e-8):
                    return next_temp.tolist()
                temp = next_temp
            return temp.tolist()
        except Exception as e_inner:
            raise ValueError(f"Error al calcular el estado estacionario: {str(e_inner)}")


def simulate_monte_carlo(matrix, states, initial_state, steps):
    """
    Simula un paseo aleatorio (trayectoria Monte Carlo) en la cadena de Markov.
    
    Args:
        matrix (list of lists): Matriz de transición NxN
        states (list): Nombres únicos de los estados
        initial_state (str): Estado inicial
        steps (int): Número de pasos a simular
    Returns:
        list: Lista de estados visitados en orden
    """
    P = np.array(matrix)
    state_to_idx = {s: i for i, s in enumerate(states)}
    
    if initial_state not in state_to_idx:
        raise ValueError(f"El estado inicial '{initial_state}' no existe en el sistema.")
        
    curr_idx = state_to_idx[initial_state]
    path = [initial_state]
    
    for _ in range(steps):
        # Probabilidades para el siguiente paso desde el estado actual
        probs = P[curr_idx]
        
        # Elegir siguiente índice según probabilidades de transición
        next_idx = np.random.choice(len(states), p=probs)
        path.append(states[next_idx])
        curr_idx = next_idx
        
    return path


def calculate_transition_frequencies(sequence):
    """
    Calcula las frecuencias de transición y genera estadísticas adicionales
    para análisis de flujo de conceptos en texto.
    
    Args:
        sequence (list): Secuencia de palabras clave
    Returns:
        dict: Estadísticas de transiciones frecuentes
    """
    if len(sequence) < 2:
        return {}
    
    from collections import Counter
    transitions = []
    for i in range(len(sequence) - 1):
        transitions.append((sequence[i], sequence[i+1]))
    
    freq = Counter(transitions)
    
    # Top 10 transiciones más frecuentes
    top_transitions = freq.most_common(10)
    
    # Calcular entropía de la secuencia como medida de predictabilidad
    total_transitions = len(transitions)
    entropy = 0.0
    for trans, count in freq.items():
        if count > 0:
            p = count / total_transitions
            entropy -= p * np.log2(p)
    
    return {
        'top_transitions': top_transitions,
        'total_transitions': total_transitions,
        'unique_transitions': len(freq),
        'entropy': float(entropy)
    }
