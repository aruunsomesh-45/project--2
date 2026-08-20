from django.contrib import admin
from .models import StudentAIInsight, StudentAIInsightHistory


@admin.register(StudentAIInsight)
class StudentAIInsightAdmin(admin.ModelAdmin):
    list_display = ('student', 'status', 'model_name', 'prompt_version', 'updated_at')
    list_filter = ('status', 'model_name', 'prompt_version')
    search_fields = ('student__username', 'student__profile__full_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StudentAIInsightHistory)
class StudentAIInsightHistoryAdmin(admin.ModelAdmin):
    list_display = ('student', 'model_name', 'prompt_version', 'archived_at')
    search_fields = ('student__username', 'student__profile__full_name')
    readonly_fields = ('archived_at',)
