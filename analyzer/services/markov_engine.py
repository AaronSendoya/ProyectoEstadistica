import numpy as np

def estimate_transition_matrix(sequence):
    """
    Estima la matriz de transición desde una secuencia de estados observados.
    Maneja correctamente secuencias de palabras clave con suavizado Laplace.
    
    Args:
        sequence (list): Lista de valores categóricos (estados/palabras clave).
    Returns:
        dict: {
            'states': lista de estados únicos,
            'matrix': matriz de transición (NxN),
            'counts': matriz de conteos de transiciones
        }
    """
    if not sequence or len(sequence) < 2:
        raise ValueError("La secuencia debe tener al menos dos observaciones.")
    
    # Identificar estados únicos manteniendo orden de aparición
    seen = set()
    states = []
    for item in sequence:
        if item not in seen:
            states.append(item)
            seen.add(item)
    states.sort()  # Ordena alfabéticamente para consistencia
    
    n = len(states)
    state_to_idx = {state: idx for idx, state in enumerate(states)}
    
    # Inicializar matriz de conteos con suavizado Laplace (pseudo-conteo de 1)
    counts = np.ones((n, n))  # Comienza con 1 para evitar probabilidades cero
    
    # Contar transiciones
    for i in range(len(sequence) - 1):
        curr_state = sequence[i]
        next_state = sequence[i+1]
        if curr_state in state_to_idx and next_state in state_to_idx:
            counts[state_to_idx[curr_state], state_to_idx[next_state]] += 1
        
    # Convertir a probabilidades
    matrix = np.zeros((n, n))
    for i in range(n):
        row_sum = counts[i].sum()
        if row_sum > 0:
            matrix[i] = counts[i] / row_sum
        else:
            # Si un estado no tiene transiciones, auto-loop con probabilidad 1.0
            matrix[i, i] = 1.0
            
    return {
        'states': states,
        'matrix': matrix.tolist(),
        'counts': counts.tolist()
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
