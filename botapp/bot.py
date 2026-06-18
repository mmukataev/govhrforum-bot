import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telegrambot.settings')
import django
django.setup()

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import MessageHandler, filters

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from botapp.models import Content, UserBotSettings, Feedback, Sessions
from django.contrib.auth import get_user_model


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

# Хранилище пользователей в памяти
user_storage = {}

# Кэш для хранения информации об отправленных сообщениях
last_content_tracker = {}
last_content_lock = asyncio.Lock()

async def cleanup_tracker():
    """Очистка трекера от старых записей"""
    while True:
        await asyncio.sleep(3600)  # Очищаем каждый час
        now = timezone.localtime(timezone.now())
        async with last_content_lock:
            # Удаляем записи старше 7 дней
            to_delete = [k for k, v in last_content_tracker.items() 
                        if (now - v['timestamp']).days > 7]
            for k in to_delete:
                last_content_tracker.pop(k, None)

def get_language_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_or_create_user_settings(user_id):
    User = get_user_model()
    try:
        settings = await UserBotSettings.objects.aget(telegram_id=user_id)
    except ObjectDoesNotExist:
        print(f"Creating new user and settings for telegram_id={user_id}")
        user, created = await User.objects.aupdate_or_create(
            username=f'user_{user_id}',
            defaults={}
        )
        print(f"User created: {user}, created={created}")
        settings = await UserBotSettings.objects.acreate(
            user=user,
            telegram_id=user_id
        )
        print(f"UserBotSettings created: {settings}")
    return settings

async def get_sessions_keyboard(content_obj, language="ru"):
    keyboard = []

    async for session in content_obj.selected_sessions.all().aiterator():

        if language == "kz":
            title = session.title_kz
        elif language == "en":
            title = session.title_en
        else:
            title = session.title

        keyboard.append([
            InlineKeyboardButton(
                title,
                callback_data=f"session_{session.id}"
            )
        ])

    return InlineKeyboardMarkup(keyboard)

async def handle_change_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    content_id = query.data.split("_")[2]

    settings = await get_or_create_user_settings(user_id)

    content_obj = await Content.objects.aget(content_id=content_id)

    keyboard = await get_sessions_keyboard(content_obj, settings.language)

    if settings.language == "kz":
        text = "Сессияны таңдаңыз:"
    elif settings.language == "en":
        text = "Choose a session:"
    else:
        text = "Выберите сессию:"

    await query.edit_message_text(
        text=text,
        reply_markup=keyboard
    )

async def handle_session_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    print("CLICKED:", query.data)

    await query.answer()

    try:
        user_id = query.from_user.id
        session_id = int(query.data.split("_")[1])

        settings = await get_or_create_user_settings(user_id)

        session = await Sessions.objects.aget(id=session_id)

        settings.selected_session = session
        await settings.asave()

        print("SESSION SAVED:", session.id)

        content_obj = await Content.objects.aget(
            selected_sessions__id=session.id
        )

        print("CONTENT FOUND:", content_obj.content_id)

        keyboard = get_change_session_keyboard(
            content_obj,
            settings.language
        )

        await query.edit_message_text(
            f"✅ {session.title}",
            reply_markup=keyboard
        )

        print("MESSAGE UPDATED")

    except Exception as e:
        print("SESSION SELECT ERROR:", str(e))
        import traceback
        traceback.print_exc()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Создаем/обновляем запись пользователя при старте
    await get_or_create_user_settings(user_id)
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🇰🇿 Тілді таңдаңыз\n🇷🇺 Пожалуйста, выберите язык\n🇬🇧 Please choose a language",
        reply_markup=get_language_keyboard(),
    )

async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    language = query.data.split('_')[1]

    # Сохраняем язык пользователя в базе данных
    settings = await get_or_create_user_settings(user_id)
    settings.language = language
    await settings.asave()

    # Получаем обновленные настройки для сообщения
    if language == "ru":
        message = "✅ Отлично! Язык интерфейса переключен на русский 🇷🇺"
    elif language == "kz":
        message = "✅ Керемет! Интерфейс тілі қазақ тіліне ауыстырылды 🇰🇿"
    else:
        message = "✅ Great! Interface language switched to English 🇬🇧"

    await query.edit_message_text(text=message)

def get_change_session_keyboard(content_obj, language="ru"):
    if language == "kz":
        text = "🔄 Сессияны ауыстыру"
    elif language == "en":
        text = "🔄 Change session"
    else:
        text = "🔄 Сменить сессию"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text,
                callback_data=f"change_session_{content_obj.content_id}"
            )
        ]
    ])

async def send_content_to_user(application, content, user_id):
    
    try:
        settings = await get_or_create_user_settings(user_id)
        user_language = settings.language
        
        # Store the last content ID in global tracker with lock
        async with last_content_lock:
            last_content_tracker[user_id] = {
                'content_id': content['id'],
                'timestamp': datetime.now()
            }
        
        if user_language == "ru":
            message = f"<b>{content['title']}</b>\n\n{content['text']}"
        elif user_language == "kz":
            message = f"<b>{content['title_kz']}</b>\n\n{content['text_kz']}"
        else:
            message = f"<b>{content['title_en']}</b>\n\n{content['text_en']}"

        if content.get("is_session_select_message"):
            settings = await get_or_create_user_settings(user_id)

            content_obj = await Content.objects.aget(
                content_id=content["id"]
            )

            reply_markup = await get_sessions_keyboard(
                content_obj,
                settings.language
            )

            await application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            return True
    
        if content.get('image'):
            image_path = content['image']
            if os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    if content['type'] == 'ask':
                        reply_markup = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("👍", callback_data="feedback_positive"),
                                InlineKeyboardButton("👎", callback_data="feedback_negative")
                            ]
                        ])
                        await application.bot.send_photo(
                            chat_id=user_id,
                            photo=photo,
                            caption=message,
                            parse_mode="HTML",
                            reply_markup=reply_markup
                        )
                    else:
                        await application.bot.send_photo(
                            chat_id=user_id,
                            photo=photo,
                            caption=message,
                            parse_mode="HTML"
                        )
            else:
                await send_text_message(application, content, user_id, message)
        else:
            await send_text_message(application, content, user_id, message)
        return True
    except Exception as e:
        print(f"Failed to send to user {user_id}: {str(e)}")
        return False

async def send_text_message(application, content, user_id, message):
    """Отправляет текстовое сообщение с учетом типа контента"""
    if content['type'] == 'ask':
        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍", callback_data="feedback_positive"),
                InlineKeyboardButton("👎", callback_data="feedback_negative")
            ]
        ])
        await application.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        await application.bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML"
        )



# async def send_content_to_all_users(application, content):
#     """Отправляет контент всем пользователям"""
#     now = timezone.localtime(timezone.now())
#     print(f"\n=== Processing content ID {content['id']} ===")
    
#     # Получаем всех пользователей из базы данных
#     user_ids = []
#     async for settings in UserBotSettings.objects.all().aiterator():
#         user_ids.append(settings.telegram_id)

    
#     print(f"Found {len(user_ids)} users")
    
#     success_count = 0
#     fail_count = 0
    
#     for user_id in user_ids:
#         result = await send_content_to_user(application, content, user_id)
#         if result:
#             success_count += 1
#         else:
#             fail_count += 1
    
#     print(f"Send results: {success_count} success, {fail_count} failed")
async def send_content_to_all_users(application, content):
    content_obj = await Content.objects.select_related(
        "selected_session"
    ).aget(content_id=content["id"])

    print(
        f"Content={content_obj.content_id}, "
        f"is_session_select_message={content_obj.is_session_select_message}, "
        f"session={content_obj.selected_session_id}"
    )

    user_ids = set()

    async for user in UserBotSettings.objects.all().aiterator():

        if content_obj.is_session_select_message:
            user_ids.add(user.telegram_id)

        elif content_obj.selected_session_id:
            if user.selected_session_id == content_obj.selected_session_id:
                user_ids.add(user.telegram_id)

        else:
            user_ids.add(user.telegram_id)

    for user_id in user_ids:
        await send_content_to_user(application, content, user_id)

async def get_content_to_send():
    """Получает контент для отправки из базы данных"""
    now = timezone.localtime(timezone.now())
    current_date = now.date()
    current_hour = now.hour
    current_minute = now.minute
    
    contents = []
    
    async for content in Content.objects.filter(
        send_time__date=current_date,
        send_time__hour=current_hour,
        send_time__minute=current_minute
    ):
        contents.append({
            'id': content.content_id,
            'type': content.content_type,
            'title': content.title,
            'title_kz': content.title_kz,
            'title_en': content.title_en,
            'selected_session_id': content.selected_session_id,
            'is_session_select_message': content.is_session_select_message,
            'text': content.text,
            'text_kz': content.text_kz,
            'text_en': content.text_en,
            'time': content.send_time,
            'image': content.image.path if content.image else None
        })
    return contents

async def content_scheduler(application):
    """Планировщик, который проверяет контент для отправки"""
    print("Optimized content scheduler started")
    
    asyncio.create_task(cleanup_tracker())
    
    while True:
        try:
            contents_to_send = await get_content_to_send()
            
            for content in contents_to_send:
                await send_content_to_all_users(application, content)

            sleep_time = 60 - datetime.now().second - datetime.now().microsecond/1000000
            await asyncio.sleep(sleep_time)
            
        except Exception as e:
            print(f"Scheduler error: {str(e)}")
            await asyncio.sleep(60)

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    feedback_text = update.message.text
    
    # Get user's settings
    settings = await get_or_create_user_settings(user_id)
    
    # Get the last content ID from global tracker
    async with last_content_lock:
        last_content_data = last_content_tracker.get(user_id)
        last_content_id = last_content_data['content_id'] if last_content_data else None
    
    if not last_content_id:
        # No content found for feedback
        response = "Не удалось определить контент для отзыва"
        if settings.language == "kz":
            response = "Кері байланыс үшін контент анықталмады"
        elif settings.language == "en":
            response = "Could not identify content for feedback"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response,
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Проверяем существование контента и получаем объект Content
    try:
        content = await Content.objects.aget(content_id=last_content_id)
    except Content.DoesNotExist:
        response = "Контент для отзыва не найден"
        if settings.language == "kz":
            response = "Кері байланыс үшін контент табылмады"
        elif settings.language == "en":
            response = "Content for feedback not found"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response,
            reply_markup=ReplyKeyboardRemove()
        )
        return
    except Exception as e:
        print(f"Error getting content: {str(e)}")
        response = "Ошибка при получении контента"
        if settings.language == "kz":
            response = "Контентті алу кезінде қате"
        elif settings.language == "en":
            response = "Error getting content"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response,
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if feedback_text in ['👍', '👎']:
        # Save basic feedback
        feedback = await Feedback.objects.acreate(
            user_id=user_id,
            content=content,  # Передаем объект Content, а не ID
            is_positive=(feedback_text == '👍')
        )
        context.user_data['last_feedback'] = feedback.id
        
        # Ask for details based on language
        if settings.language == "ru":
            question = "Что именно вам понравилось?" if feedback_text == '👍' else "Что именно вам не понравилось?"
        elif settings.language == "kz":
            question = "Сізге не ұнады?" if feedback_text == '👍' else "Сізге не ұнамады?"
        else:
            question = "What did you like?" if feedback_text == '👍' else "What didn't you like?"
            
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=question
        )
    else:
        # Save detailed feedback
        feedback_id = context.user_data.get('last_feedback')
        if feedback_id:
            await Feedback.objects.filter(id=feedback_id).aupdate(details=feedback_text)
        
        # Response based on language
        if settings.language == "ru":
            response = "Спасибо за ваш отзыв!"
        elif settings.language == "kz":
            response = "Пікіріңіз үшін рақмет!"
        else:
            response = "Thank you for your feedback!"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response,
            reply_markup=ReplyKeyboardRemove()
        )

async def handle_inline_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    settings = await get_or_create_user_settings(user_id)
    
    # Получаем последний отправленный контент
    async with last_content_lock:
        last_content_data = last_content_tracker.get(user_id)
        last_content_id = last_content_data['content_id'] if last_content_data else None

    if not last_content_id:
        await query.edit_message_text("Контент для отзыва не найден")
        return

    try:
        content = await Content.objects.aget(content_id=last_content_id)
    except Content.DoesNotExist:
        await query.edit_message_text("Контент не найден")
        return

    is_positive = data == "feedback_positive"
    feedback = await Feedback.objects.acreate(
        user_id=user_id,
        content=content,
        is_positive=is_positive
    )
    context.user_data['last_feedback'] = feedback.id

    if settings.language == "ru":
        question = "Что именно вам понравилось?" if is_positive else "Что именно вам не понравилось?"
    elif settings.language == "kz":
        question = "Сізге не ұнады?" if is_positive else "Сізге не ұнамады?"
    else:
        question = "What did you like?" if is_positive else "What didn't you like?"

    await query.edit_message_reply_markup(reply_markup=None)  # удаляем кнопки
    await context.bot.send_message(chat_id=query.message.chat_id, text=question)

def main():
    # application = ApplicationBuilder().token("7606408596:AAHr_-mSFqscilp_-SHQxqioRXOrpYe9Sf0").build()
    application = ApplicationBuilder().token("8904957569:AAEvSVLno_2Qje82SNpLdt2hCXXKFKz1FEY").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_session_select, pattern="^session_"))
    application.add_handler(CallbackQueryHandler(language_selection, pattern="^lang_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback))
    application.add_handler(CallbackQueryHandler(handle_inline_feedback, pattern="^feedback_"))
    application.add_handler(
        CallbackQueryHandler(handle_change_session, pattern="^change_session_")
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.create_task(content_scheduler(application))
        application.run_polling()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    finally:
        loop.close()

if __name__ == "__main__":
    main()