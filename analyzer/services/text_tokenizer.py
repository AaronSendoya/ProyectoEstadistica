"""
Tokenización semántica para extracción de palabras clave en español.
"""
import re
from collections import Counter

MIN_KEYWORD_LENGTH = 6

SPANISH_STOP_WORDS = frozenset({
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'al', 'lo',
    'en', 'y', 'o', 'u', 'a', 'que', 'es', 'se', 'no', 'con', 'por', 'para', 'su', 'sus',
    'como', 'más', 'pero', 'le', 'ya', 'este', 'esta', 'estos', 'estas', 'ese', 'esa',
    'han', 'ha', 'he', 'si', 'sí', 'me', 'mi', 'tu', 'te', 'nos', 'son', 'fue', 'ser',
    'también', 'todo', 'todos', 'toda', 'todas', 'cada', 'sobre', 'entre', 'cuando',
    'muy', 'sin', 'hasta', 'desde', 'durante', 'después', 'antes', 'aunque', 'mientras',
    'mediante', 'hacia', 'tras', 'ante', 'bajo', 'cabe', 'contra', 'ello', 'esto',
    'entonces', 'algunos', 'algunas', 'alguno', 'alguna', 'aquellos', 'aquellas',
    'aquello', 'aquí', 'allí', 'embargo', 'nuestro', 'nuestra', 'nuestros', 'nuestras',
    'vuestro', 'vuestra', 'pueden', 'puede', 'tienen', 'tiene', 'tenían', 'había',
    'haber', 'siendo', 'sido', 'están', 'estaba', 'estuvo', 'fueron', 'forma', 'parte',
    'mismo', 'misma', 'otro', 'otra', 'otros', 'otras', 'donde', 'quien', 'cual',
    'cuales', 'cuál', 'cuáles', 'porque', 'porqué', 'sino', 'aun', 'aún', 'solo',
    'sólo', 'tan', 'tanto', 'tanta', 'todos', 'nadie', 'nada', 'algo', 'cualquier',
    'quienes', 'poco', 'muchos', 'muchas', 'poca', 'veces', 'vez', 'bien', 'mal',
    'hace', 'hacer', 'hecho', 'hacia', 'así', 'tras', 'luego', 'además', 'tampoco',
    'ni', 'nosotros', 'nosotras', 'ellos', 'ellas', 'usted', 'ustedes', 'les', 'os',
    'ese', 'eso', 'aquél', 'aquella', 'donde', 'cuando', 'quien', 'cuyo', 'cuya',
    'cuyos', 'cuyas', 'través', 'tambien', 'despues', 'mas', 'solo', 'aquel', 'aquella',
})

_WORD_PATTERN = re.compile(r'\b[\wáéíóúüñ]+\b', re.UNICODE)
_EDGE_PUNCT = re.compile(r'^[^\wáéíóúüñ]+|[^\wáéíóúüñ]+$', re.UNICODE)


def normalize_token(raw: str) -> str:
    """Quita puntuación adherida y normaliza a minúsculas."""
    if not raw:
        return ''
    token = raw.lower().strip()
    token = _EDGE_PUNCT.sub('', token)
    return token


def is_semantic_keyword(token: str) -> bool:
    """Palabra válida para análisis: ≥6 letras y fuera de stop words."""
    word = normalize_token(token)
    if len(word) < MIN_KEYWORD_LENGTH:
        return False
    return word not in SPANISH_STOP_WORDS


def tokenize_semantic_words(text: str) -> list[str]:
    """Lista de palabras clave semánticas en orden de aparición."""
    result = []
    for raw in _WORD_PATTERN.findall(text.lower()):
        word = normalize_token(raw)
        if is_semantic_keyword(word):
            result.append(word)
    return result


def count_semantic_words(text: str) -> Counter:
    return Counter(tokenize_semantic_words(text))


def top_semantic_keywords(text: str, limit: int = 12) -> list[str]:
    return [w for w, _ in count_semantic_words(text).most_common(limit)]
