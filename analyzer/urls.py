from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('api/columns/', views.peek_file_columns, name='peek_columns'),
    path('download/<str:format_type>/', views.download_report, name='download_report'),
]
