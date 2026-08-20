from django.urls import path
from . import student_views as views

app_name = 'study_plans'

urlpatterns = [
    path('', views.my_plans_view, name='my_plans'),
    path('tasks/<int:task_id>/start/', views.task_start_view, name='task_start'),
    path('tasks/<int:task_id>/complete/', views.task_complete_view, name='task_complete'),
    path('tasks/<int:task_id>/skip/', views.task_skip_view, name='task_skip'),
]
