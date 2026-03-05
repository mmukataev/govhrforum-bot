#!/bin/bash
# /var/www/bot/start_gunicorn.sh

# Активируем виртуальное окружение
source /var/www/bot/venv_bot/bin/activate

# Запускаем Gunicorn
exec gunicorn telegrambot.wsgi:application --bind 0.0.0.0:9050 --workers 2 --timeout 120