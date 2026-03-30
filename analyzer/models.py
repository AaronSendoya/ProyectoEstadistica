from django.db import models

class AnalysisLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255)
    metrics_requested = models.TextField()
    export_format = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {self.filename}"
