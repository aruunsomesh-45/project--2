from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('redirect/', views.redirect_after_login, name='redirect_after_login'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('teacher/dashboard/', views.teacher_placeholder_view, name='teacher_placeholder'),
]
