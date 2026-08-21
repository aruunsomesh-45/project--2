"""
config URL Configuration

Routes:
    /               → Landing page
    /accounts/      → Registration, login, logout, onboarding
    /assessment/    → Assessment flow, auto-save, profile
    /admin/         → Django admin
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    path('accounts/', include('accounts.urls')),
    path('assessment/', include('assessment.urls')),
    path('classroom/', include('classroom.urls')),
    path('classroom/', include('ai_insights.urls')),
    path('screening/', include('screening.urls')),
    path('study-plans/', include('study_plans.urls')),
    path('classroom/', include('study_plans.teacher_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
