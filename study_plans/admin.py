from django.contrib import admin
from .models import StudyPlan, StudyTask, StudyResource, PlanAdaptationDraft


class StudyTaskInline(admin.TabularInline):
    model = StudyTask
    extra = 0


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'teacher', 'subject', 'status', 'ai_generated', 'created_at')
    list_filter = ('status', 'difficulty', 'ai_generated')
    search_fields = ('title', 'subject', 'student__username', 'student__profile__full_name')
    inlines = [StudyTaskInline]


@admin.register(StudyTask)
class StudyTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'study_plan', 'date', 'task_type', 'status', 'estimated_minutes')
    list_filter = ('task_type', 'status')
    search_fields = ('title', 'study_plan__title')


admin.site.register(StudyResource)
admin.site.register(PlanAdaptationDraft)
