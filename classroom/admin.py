from django.contrib import admin
from .models import Class, ClassStudent


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'grade', 'section', 'class_code', 'teacher', 'is_active', 'created_at')
    list_filter = ('is_active', 'subject', 'grade')
    search_fields = ('name', 'class_code', 'teacher__username', 'teacher__profile__full_name')


@admin.register(ClassStudent)
class ClassStudentAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'student', 'joined_at')
    list_filter = ('classroom',)
    search_fields = ('classroom__name', 'student__username', 'student__profile__full_name')
