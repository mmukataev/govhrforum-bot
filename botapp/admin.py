# botapp/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Content, UserBotSettings, Feedback

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('content_id', 'image_preview', 'title', 'content_type', 'send_time')
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
            'fields': ('content_id', 'content_type', 'send_time')
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

@admin.register(UserBotSettings)
class UserBotSettingsAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'language', 'last_interaction')
    list_filter = ('language',)
    search_fields = ('user__username',)
    readonly_fields = ('last_interaction',)
    date_hierarchy = 'last_interaction'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'language')
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