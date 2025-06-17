module.exports = {
  apps: [
    {
      name: "telegram-bot",
      script: "/var/www/bot/start_bot.sh",
      cwd: "/var/www/bot",
      interpreter: "bash",
      env: {
        PYTHONPATH: "/var/www/bot",
        DJANGO_SETTINGS_MODULE: "telegrambot.settings"
      },
      error_file: "/var/www/bot/logs/bot-error.log",
      out_file: "/var/www/bot/logs/bot-out.log"
    },
    {
      name: "gunicorn",
      script: "/var/www/bot/start_gunicorn.sh",
      cwd: "/var/www/bot",
      interpreter: "bash",
      env: {
        PYTHONPATH: "/var/www/bot",
        DJANGO_SETTINGS_MODULE: "telegrambot.settings"
      },
      error_file: "/var/www/bot/logs/gunicorn-error.log",
      out_file: "/var/www/bot/logs/gunicorn-out.log"
    }
  ]
}