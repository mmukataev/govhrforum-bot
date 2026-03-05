#!/bin/bash
# /var/www/bot/start_bot.sh
cd /var/www/bot
source venv_bot/bin/activate
exec python botapp/bot.py