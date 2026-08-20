from django.contrib import admin
from .models import (
    ScreeningQuestion, SelfReportQuestion, ScreeningAttempt,
    ScreeningResponse, SelfReportResponse, ScreeningReport,
)


@admin.register(ScreeningQuestion)
class ScreeningQuestionAdmin(admin.ModelAdmin):
    list_display = ('tier', 'section', 'topic', 'difficulty', 'display_order')
    list_filter = ('tier', 'section', 'topic', 'difficulty')
    search_fields = ('question_text',)


@admin.register(SelfReportQuestion)
class SelfReportQuestionAdmin(admin.ModelAdmin):
    list_display = ('category', 'sub_key', 'display_order', 'teacher_facing_only')
    list_filter = ('category', 'teacher_facing_only')
    search_fields = ('question_text',)


@admin.register(ScreeningAttempt)
class ScreeningAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'tier', 'part1_status', 'part2_status', 'started_at', 'completed_at')
    list_filter = ('tier', 'part1_status', 'part2_status')
    search_fields = ('student__username', 'student__profile__full_name')


@admin.register(ScreeningReport)
class ScreeningReportAdmin(admin.ModelAdmin):
    list_display = ('student', 'personality_tag', 'interest_tag', 'learning_style_tag', 'wellbeing_flag', 'generated_at')
    search_fields = ('student__username', 'student__profile__full_name')


admin.site.register(ScreeningResponse)
admin.site.register(SelfReportResponse)
