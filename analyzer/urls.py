from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('history/', views.history_view, name='history'),
    path('help/', views.help_view, name='help'),
    path('word-counter/', views.word_counter_view, name='word_counter'),
    path('api/columns/', views.peek_file_columns, name='peek_columns'),
    path('download/<str:format_type>/', views.download_report, name='download_report'),
]
