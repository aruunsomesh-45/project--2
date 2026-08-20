from django.urls import path
from . import views

app_name = 'classroom'

urlpatterns = [
    path('', views.teacher_dashboard_view, name='dashboard'),
    path('class/<int:pk>/', views.class_detail_view, name='class_detail'),
    path('class/<int:pk>/edit/', views.class_edit_view, name='class_edit'),
    path('class/<int:pk>/delete/', views.class_delete_view, name='class_delete'),
    path('class/<int:pk>/regenerate-code/', views.class_regenerate_code_view, name='class_regenerate_code'),
    path('class/<int:pk>/student/<int:student_id>/remove/', views.remove_student_view, name='remove_student'),
    path('student/<int:student_id>/', views.teacher_student_profile_view, name='student_profile'),
    path('student/<int:student_id>/screening/', views.student_screening_report_view, name='student_screening_report'),
    path('join/', views.student_join_class_view, name='join_class'),
]
