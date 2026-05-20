"""
Motor de Análisis para Árbol de Problemas.
Detecta causas, efectos y estructura jerárquica en textos de investigación.
"""
import re
from collections import defaultdict


class ProblemTreeAnalyzer:
    """
    Analiza un DataFrame de párrafos para identificar causas, efectos y relaciones.
    """
    
    def __init__(self):
        # Conectores lingüísticos para identificar causas
        self.CAUSE_CONNECTORS = {
            'porque', 'debido', 'ya que', 'raíz', 'origen', 'causa', 'motivo',
            'provocado', 'originado', 'resultado de', 'consecuencia de', 'dado que',
            'puesto que', 'causa de', 'ocasionado', 'generó', 'produjo'
        }
        
        # Conectores para identificar efectos
        self.EFFECT_CONNECTORS = {
            'consecuencia', 'efecto', 'impacto', 'resultado', 'por lo tanto',
            'por ende', 'entonces', 'generó', 'causó', 'ocasionó', 'derivó',
            'originó', 'condujo', 'produce', 'propicia', 'facilita', 'impide'
        }
        
        # Palabras clave para problema central
        self.PROBLEM_KEYWORDS = {
            'problema', 'crisis', 'conflicto', 'desafío', 'dificultad', 'obstáculo',
            'limitación', 'insuficiencia', 'deficiencia', 'falta', 'carencia'
        }
    
    def detect_connectors_in_text(self, text):
        """
        Detecta conectores de causa y efecto en un texto.
        
        Args:
            text (str): Texto a analizar
            
        Returns:
            dict: {'has_cause': bool, 'has_effect': bool, 'cause_words': list, 'effect_words': list}
        """
        text_lower = text.lower()
        
        # Encontrar palabras conectoras presentes
        cause_words = [w for w in self.CAUSE_CONNECTORS if w in text_lower]
        effect_words = [w for w in self.EFFECT_CONNECTORS if w in text_lower]
        
        return {
            'has_cause': len(cause_words) > 0,
            'has_effect': len(effect_words) > 0,
            'cause_words': cause_words,
            'effect_words': effect_words
        }
    
    def classify_paragraph(self, paragraph_text, paragraph_num):
        """
        Clasifica un párrafo como CAUSA, EFECTO o PROBLEMA CENTRAL.
        
        Args:
            paragraph_text (str): Contenido del párrafo
            paragraph_num (int): Número de párrafo
            
        Returns:
            dict: {'type': 'CAUSA'|'EFECTO'|'CENTRAL', 'confidence': float, 'connectors': list}
        """
        text_lower = paragraph_text.lower()
        detection = self.detect_connectors_in_text(paragraph_text)
        
        # Buscar palabras de problema
        problem_words = [w for w in self.PROBLEM_KEYWORDS if w in text_lower]
        has_problem_keyword = len(problem_words) > 0
        
        # Lógica de clasificación
        if detection['has_cause'] and not detection['has_effect']:
            confidence = 0.9 if len(detection['cause_words']) > 1 else 0.7
            return {
                'type': 'CAUSA',
                'confidence': confidence,
                'connectors': detection['cause_words']
            }
        elif detection['has_effect'] and not detection['has_cause']:
            confidence = 0.9 if len(detection['effect_words']) > 1 else 0.7
            return {
                'type': 'EFECTO',
                'confidence': confidence,
                'connectors': detection['effect_words']
            }
        elif has_problem_keyword or (paragraph_num == 1 and not detection['has_cause'] and not detection['has_effect']):
            return {
                'type': 'CENTRAL',
                'confidence': 0.85 if has_problem_keyword else 0.6,
                'connectors': problem_words
            }
        else:
            # Párrafo neutral o ambiguo
            return {
                'type': 'NEUTRAL',
                'confidence': 0.5,
                'connectors': []
            }
    
    def analyze_dataframe(self, df):
        """
        Analiza un DataFrame de párrafos (salida de extract_text_metrics).
        
        Args:
            df (pd.DataFrame): DataFrame con columnas: Párrafo, Contenido, métricas
            
        Returns:
            dict: Estructura del árbol de problemas
        """
        causes = []
        effects = []
        central_problem = ""
        all_classifications = []
        
        # Analizar cada párrafo
        for idx, row in df.iterrows():
            content = row.get('Contenido', '')
            paragraph_num = row.get('Párrafo', idx + 1)
            
            if not content or len(content.strip()) == 0:
                continue
            
            # Clasificar párrafo
            classification = self.classify_paragraph(content, int(paragraph_num))
            classification['paragraph_num'] = int(paragraph_num)
            classification['text'] = content[:300]  # Primeros 300 caracteres
            
            # Agregar métricas
            classification['metrics'] = {
                'palabras': int(row.get('Total_Palabras', 0)),
                'oraciones': int(row.get('Total_Oraciones', 0)),
                'densidad': float(row.get('Densidad_Léxica', 0))
            }
            
            all_classifications.append(classification)
            
            # Recolectar por tipo
            if classification['type'] == 'CAUSA':
                causes.append({
                    'id': f'causa_{len(causes)+1}',
                    'text': content[:300],
                    'paragraph': int(paragraph_num),
                    'connectors': classification['connectors'],
                    'metrics': classification['metrics'],
                    'confidence': classification['confidence']
                })
            elif classification['type'] == 'EFECTO':
                effects.append({
                    'id': f'efecto_{len(effects)+1}',
                    'text': content[:300],
                    'paragraph': int(paragraph_num),
                    'connectors': classification['connectors'],
                    'metrics': classification['metrics'],
                    'confidence': classification['confidence']
                })
            elif classification['type'] == 'CENTRAL' and not central_problem:
                central_problem = content[:400]
        
        # Si no se detectó problema central, usar el primer párrafo
        if not central_problem and len(df) > 0:
            central_problem = df.iloc[0].get('Contenido', '')[:400]
        
        # Construir relaciones causa-efecto basadas en proximidad
        connections = self._build_connections(causes, effects, all_classifications)
        
        return {
            'central_problem': central_problem,
            'causes': causes,
            'effects': effects,
            'connections': connections,
            'classifications': all_classifications,
            'statistics': {
                'total_paragraphs': len(df),
                'causes_count': len(causes),
                'effects_count': len(effects),
                'average_confidence': (
                    sum(c['confidence'] for c in causes + effects) / (len(causes) + len(effects))
                    if (causes or effects) else 0.0
                )
            }
        }
    
    def _build_connections(self, causes, effects, all_classifications):
        """
        Construye un grafo de conexiones entre causas y efectos basado en proximidad.
        
        Args:
            causes (list): Lista de causas
            effects (list): Lista de efectos
            all_classifications (list): Lista completa de clasificaciones
            
        Returns:
            list: Conexiones {from: id, to: id, strength: float}
        """
        connections = []
        
        # Para cada causa, conectarla con el efecto más cercano
        for cause in causes:
            cause_para = cause['paragraph']
            closest_effect = None
            min_distance = float('inf')
            
            for effect in effects:
                effect_para = effect['paragraph']
                distance = abs(effect_para - cause_para)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_effect = effect
            
            if closest_effect and min_distance <= 5:  # Máximo 5 párrafos de distancia
                # Calcular fuerza basada en densidad léxica y proximidad
                strength = max(0.3, 1.0 - (min_distance / 10.0))
                
                connections.append({
                    'from': cause['id'],
                    'to': closest_effect['id'],
                    'strength': strength,
                    'distance': min_distance
                })
        
        return connections


def analyze_text_for_problem_tree(text_content):
    """
    Función conveniente para analizar texto plano directamente.
    
    Args:
        text_content (str): Contenido del archivo de texto
        
    Returns:
        dict: Estructura del árbol de problemas
    """
    from .extractor import extract_text_metrics
    
    # Extraer métricas y párrafos
    df = extract_text_metrics(text_content)
    
    # Analizar
    analyzer = ProblemTreeAnalyzer()
    return analyzer.analyze_dataframe(df)
