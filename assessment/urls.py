from django.urls import path
from . import views

app_name = 'assessment'

urlpatterns = [
    path('', views.assessment_take_view, name='take'),
    path('save/', views.assessment_save_view, name='save'),
    path('submit/', views.assessment_submit_view, name='submit'),
    path('profile/', views.learning_profile_view, name='profile'),
]
