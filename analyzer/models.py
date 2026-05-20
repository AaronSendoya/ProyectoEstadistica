from django.db import models


class DocumentoTexto(models.Model):
    """Artículo de investigación en texto plano persistido en SQLite."""

    titulo = models.CharField(max_length=255)
    contenido = models.TextField()
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'Documento de texto'
        verbose_name_plural = 'Documentos de texto'

    def __str__(self):
        return self.titulo


class AnalysisLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    metrics_requested = models.TextField()
    export_format = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {self.filename}"
