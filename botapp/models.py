# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Sessions(models.Model):
    title = models.CharField(max_length=255)
    title_kz = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Сессия на выбор'
        verbose_name_plural = 'Сессия на выбор'

    def __str__(self):
        return f"{self.title}"

class UserBotSettings(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True)
    selected_session = models.ForeignKey(
        Sessions,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_settings'
    )
    language = models.CharField(max_length=10, choices=[
        ('ru', 'Русский'),
        ('kz', 'Қазақша'),
        ('en', 'English')
    ], default='en')
    last_interaction = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки бота пользователя'
        verbose_name_plural = 'Настройки бота пользователей'

    def __str__(self):
        return f"{self.telegram_id } - {self.get_language_display()}"

class Content(models.Model):
    TYPE_CHOICES = [
        ('info', 'Информация'),
        ('news', 'Новость'),
        ('ask', 'ask'),
        # ('select_session', 'Выбор сессии'),
    ]
    
    content_id = models.IntegerField(unique=True)
    content_type = models.CharField(max_length=25, choices=TYPE_CHOICES)

    selected_session = models.ForeignKey(
        Sessions,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contents'
    )

    is_session_select_message = models.BooleanField(default=False)
    selected_sessions = models.ManyToManyField(
        Sessions,
        blank=True,
        related_name="contents_for_choise"
    )
    # asdasdasd

    title = models.CharField(max_length=255)
    title_kz = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255)
    text = models.TextField()
    text_kz = models.TextField()
    text_en = models.TextField()
    send_time = models.DateTimeField()
    image = models.FileField(
        upload_to='content_images/',
        null=True,
        blank=True,
        verbose_name='Изображение'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Контент'
        verbose_name_plural = 'Контент'
        ordering = ['-send_time']

    def __str__(self):
        return f"{self.content_id}: {self.title}"

class Feedback(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    is_positive = models.BooleanField()
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'