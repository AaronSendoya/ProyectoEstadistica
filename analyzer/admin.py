from django.contrib import admin
from .models import DocumentoTexto, AnalysisLog


@admin.register(DocumentoTexto)
class DocumentoTextoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha_subida', 'contenido_preview')
    search_fields = ('titulo', 'contenido')
    readonly_fields = ('fecha_subida',)

    @admin.display(description='Vista previa')
    def contenido_preview(self, obj):
        return (obj.contenido[:80] + '…') if len(obj.contenido) > 80 else obj.contenido


admin.site.register(AnalysisLog)
