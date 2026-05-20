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

    # Nuevos Módulos Avanzados
    path('problem-tree/', views.problem_tree_view, name='problem_tree'),
    path('bayesian-network/', views.bayesian_network_view, name='bayesian_network'),
    path('markov-chains/', views.markov_chains_view, name='markov_chains'),

    # APIs de cálculo para los nuevos módulos
    path('api/file-stats/', views.api_file_stats, name='api_file_stats'),
    path('api/markov/calculate/', views.api_markov_calculate, name='api_markov_calculate'),
    path('api/markov/estimate/', views.api_markov_estimate, name='api_markov_estimate'),
    path('api/bayesian/learn/', views.api_bayesian_learn, name='api_bayesian_learn'),
    path('api/bayesian/infer/', views.api_bayesian_infer, name='api_bayesian_infer'),
    path('api/problem-tree/analyze/', views.api_problem_tree_analyze, name='api_problem_tree_analyze'),
    path('api/problem-tree/pdf/', views.problem_tree_pdf, name='problem_tree_pdf'),
    path('api/bayesian/pdf/', views.bayesian_network_pdf, name='bayesian_network_pdf'),
    path('api/markov/pdf/', views.markov_chains_pdf, name='markov_chains_pdf'),
]
