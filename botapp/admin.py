# botapp/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Content, UserBotSettings, Feedback, Sessions

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('content_id', 'image_preview', 'title', 'content_type', 'display_sessions',  'send_time')
    list_filter = ('content_type',)
    search_fields = ('title', 'text', 'title_kz', 'text_kz', 'title_en', 'text_en')
    ordering = ('-send_time',)
    date_hierarchy = 'send_time'
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 200px;"/>', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = "Превью"
    
    fieldsets = (
        (None, {
            'fields': ('content_id', 'content_type', 'send_time', 'selected_session', 'selected_sessions', 'is_session_select_message')
        }),
        ('Русский контент', {
            'fields': ('title', 'text')
        }),
        ('Казахский контент', {
            'fields': ('title_kz', 'text_kz')
        }),
        ('Английский контент', {
            'fields': ('title_en', 'text_en')
        }),
        ('Изображение', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse',)
        }),
    )

    def display_sessions(self, obj):
        return ", ".join(
            obj.selected_sessions.values_list("title", flat=True)
        )

    display_sessions.short_description = "Сессии"

@admin.register(UserBotSettings)
class UserBotSettingsAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'language', 'selected_session', 'last_interaction')
    list_filter = ('language',)
    search_fields = ('user__username',)
    readonly_fields = ('last_interaction',)
    date_hierarchy = 'last_interaction'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'language', 'selected_session')
        }),
        ('Дополнительная информация', {
            'fields': ('last_interaction',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'is_positive', 'created_at')
    list_filter = ('is_positive', 'created_at')
    search_fields = ('user__username', 'content__title', 'details')

@admin.register(Sessions)
class SessionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'title_kz', 'title_en')
    search_fields = ('title', 'title_kz', 'title_en')