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

    # Supabase-hosted Google OAuth
    path('login/google/', views.supabase_login_view, name='supabase_login'),
    path('login/google/callback/', views.supabase_callback_view, name='supabase_callback'),
    path('api/supabase-callback/', views.supabase_callback_api_view, name='supabase_callback_api'),
]
