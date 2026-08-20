from django.contrib import admin
from .models import AssessmentQuestion, AssessmentResponse, LearningProfile


@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = ('display_order', 'dimension', 'question_type', 'question_text')
    list_filter = ('dimension', 'question_type')
    search_fields = ('question_text', 'dimension')
    ordering = ('display_order',)


@admin.register(AssessmentResponse)
class AssessmentResponseAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'answer_value', 'answered_at')
    list_filter = ('question__dimension',)
    search_fields = ('student__profile__full_name',)


@admin.register(LearningProfile)
class LearningProfileAdmin(admin.ModelAdmin):
    list_display = ('student', 'archetype', 'completed_at')
    list_filter = ('archetype',)
    search_fields = ('student__profile__full_name',)
