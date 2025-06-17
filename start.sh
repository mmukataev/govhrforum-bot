#!/bin/bash
source /var/www/bot/venv_bot/bin/activate  # путь к твоему виртуальному окружению
python /var/www/bot/botapp/bot.py &
venv_bot/bin/gunicorn telegrambot.wsgi:application --bind 0.0.0.0:9000
