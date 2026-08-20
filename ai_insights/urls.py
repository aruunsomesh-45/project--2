from django.urls import path
from . import views

app_name = 'ai_insights'

urlpatterns = [
    path('student/<int:student_id>/ai-insights/generate/', views.generate_insights_view, name='generate'),
    path('student/<int:student_id>/ai-insights/regenerate/', views.regenerate_insights_view, name='regenerate'),
]
