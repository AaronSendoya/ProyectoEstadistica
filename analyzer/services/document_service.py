"""
Persistencia y unión de corpus multi-documento (SQLite / DocumentoTexto).
"""
import json
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile

from analyzer.models import DocumentoTexto

CORPUS_SEPARATOR = '\n\n---\n\n'


def save_documento_from_upload(uploaded_file) -> DocumentoTexto:
    """Guarda un archivo .txt en la base de datos local."""
    name = uploaded_file.name
    if not name.lower().endswith('.txt'):
        raise ValueError(f'Solo se permiten archivos .txt: {name}')

    uploaded_file.seek(0)
    contenido = uploaded_file.read().decode('utf-8', errors='ignore').strip()
    if not contenido:
        raise ValueError(f'El archivo "{name}" está vacío o no es legible.')

    titulo = name.rsplit('.', 1)[0] or name
    return DocumentoTexto.objects.create(titulo=titulo, contenido=contenido)


def save_documentos_from_uploads(uploaded_files) -> list[dict]:
    """Persiste varios .txt y devuelve metadatos para el frontend."""
    saved = []
    for f in uploaded_files:
        doc = save_documento_from_upload(f)
        saved.append(serialize_documento(doc))
    return saved


def serialize_documento(doc: DocumentoTexto) -> dict:
    preview = doc.contenido[:120].replace('\n', ' ')
    if len(doc.contenido) > 120:
        preview += '…'
    return {
        'id': doc.pk,
        'titulo': doc.titulo,
        'fecha_subida': doc.fecha_subida.isoformat(),
        'chars': len(doc.contenido),
        'preview': preview,
    }


def list_documentos() -> list[dict]:
    return [
        serialize_documento(d)
        for d in DocumentoTexto.objects.all().order_by('-fecha_subida')
    ]


def get_documentos_by_ids(documento_ids: list[int]) -> list[DocumentoTexto]:
    if not documento_ids:
        return []
    docs = list(
        DocumentoTexto.objects.filter(pk__in=documento_ids).order_by('fecha_subida')
    )
    found_ids = {d.pk for d in docs}
    missing = set(documento_ids) - found_ids
    if missing:
        raise ValueError(f'No se encontraron documentos con ID: {sorted(missing)}')
    return docs


def build_unified_corpus(documento_ids: list[int]) -> tuple[str, dict]:
    """
    Concatena el contenido de varios documentos en un único corpus correlativo.
    Orden: fecha de subida ascendente (más antiguo primero).
    """
    docs = get_documentos_by_ids(documento_ids)
    parts = [doc.contenido.strip() for doc in docs if doc.contenido.strip()]
    if not parts:
        raise ValueError('Los documentos seleccionados no tienen contenido válido.')

    corpus = CORPUS_SEPARATOR.join(parts)
    meta = {
        'documento_ids': [d.pk for d in docs],
        'titulos': [d.titulo for d in docs],
        'document_count': len(docs),
        'total_chars': len(corpus),
    }
    return corpus, meta


def parse_documento_ids_from_request(request) -> list[int]:
    """Lee IDs desde FormData (documento_ids[]) o JSON (documento_ids)."""
    ids = []

    if request.content_type and 'application/json' in request.content_type:
        try:
            body = json.loads(request.body.decode('utf-8') or '{}')
            raw = body.get('documento_ids', [])
            if isinstance(raw, list):
                ids = [int(x) for x in raw if str(x).strip().isdigit()]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    else:
        raw_list = request.POST.getlist('documento_ids[]')
        if not raw_list:
            raw_list = request.POST.getlist('documento_ids')
        single = request.POST.get('documento_ids')
        if single and not raw_list:
            raw_list = [single]
        for item in raw_list:
            try:
                ids.append(int(item))
            except (ValueError, TypeError):
                continue

    return list(dict.fromkeys(ids))


def corpus_from_request_or_file(request, require_txt: bool = True) -> tuple[str, dict]:
    """
    Resuelve el texto a analizar: prioridad documento_ids, luego archivo .txt subido.
    """
    ids = parse_documento_ids_from_request(request)
    if ids:
        corpus, meta = build_unified_corpus(ids)
        meta['source'] = 'database'
        return corpus, meta

    uploaded = request.FILES.get('file')
    if uploaded:
        if require_txt and not uploaded.name.lower().endswith('.txt'):
            raise ValueError('Sin documentos seleccionados: suba un archivo .txt o elija artículos guardados.')
        uploaded.seek(0)
        text = uploaded.read().decode('utf-8', errors='ignore')
        return text, {'source': 'upload', 'titulos': [uploaded.name]}

    raise ValueError('Seleccione uno o más artículos guardados o suba un archivo .txt.')


def uploaded_file_from_corpus(text: str, filename: str = 'corpus_unificado.txt') -> SimpleUploadedFile:
    """Adaptador para reutilizar funciones que esperan UploadedFile."""
    return SimpleUploadedFile(filename, text.encode('utf-8'), content_type='text/plain')
