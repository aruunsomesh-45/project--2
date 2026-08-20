from django.urls import path
from . import teacher_views as views

app_name = 'study_plans_teacher'

urlpatterns = [
    path('study-plans/', views.plan_list_view, name='list'),
    path('student/<int:student_id>/study-plans/create/', views.plan_create_view, name='create'),
    path('student/<int:student_id>/progress/', views.student_progress_view, name='student_progress'),

    path('study-plans/<int:plan_id>/', views.plan_detail_view, name='detail'),
    path('study-plans/<int:plan_id>/generate/', views.plan_generate_view, name='generate'),
    path('study-plans/<int:plan_id>/approve/', views.plan_approve_view, name='approve'),
    path('study-plans/<int:plan_id>/archive/', views.plan_archive_view, name='archive'),

    path('study-plans/<int:plan_id>/tasks/add/', views.task_add_view, name='task_add'),
    path('study-plans/<int:plan_id>/tasks/<int:task_id>/delete/', views.task_delete_view, name='task_delete'),
    path('study-plans/<int:plan_id>/tasks/<int:task_id>/resources/add/', views.resource_add_view, name='resource_add'),

    path('study-plans/<int:plan_id>/adapt/', views.adaptation_request_view, name='adapt_request'),
    path('study-plans/<int:plan_id>/adaptation/<int:draft_id>/apply/', views.adaptation_apply_view, name='adaptation_apply'),
    path('study-plans/<int:plan_id>/adaptation/<int:draft_id>/discard/', views.adaptation_discard_view, name='adaptation_discard'),
]
