from django.urls import path
from . import views

app_name = 'screening'

urlpatterns = [
    path('', views.start_view, name='start'),
    path('take/', views.take_view, name='take'),
    path('report/', views.report_view, name='report'),
]
