# main.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

TOKEN = '7996564047:AAFJzRYg8ICsUVzOe6oYOZt3v2EVG7UIC_Y'
ADMIN_CHAT_IDS = [424594836, 855759233]  # Адміни

user_data = {}
dialog_history = {}

# Старт бота з вибором теми

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📣 Надіслати НОВИНУ", callback_data='news')],
        [InlineKeyboardButton("❓ Задати питання", callback_data='question')],
        [InlineKeyboardButton("💬 Інше", callback_data='general')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("👋 Вітаємо в боті ПЕТРІВСЬКОЇ ГРОМАДИ", reply_markup=reply_markup)

# Обробка натискання кнопки теми

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {'topic': query.data}
    context.bot.send_message(chat_id=user_id, text=f"✏️ Надішліть своє звернення по темі: {query.data}")

# Пересилання звернень адміністраторам

def forward_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_data:
        update.message.reply_text("❗ Спочатку натисніть /start та виберіть тему звернення.")
        return

    topic = user_data[user_id]['topic']
    message_text = update.message.text or "[Медіа]"

    if user_id not in dialog_history:
        dialog_history[user_id] = []
    dialog_history[user_id].append((topic, message_text))

    for admin_id in ADMIN_CHAT_IDS:
        if update.message.text:
            fwd = update.message.forward(chat_id=admin_id)
        else:
            fwd = context.bot.forward_message(chat_id=admin_id, from_chat_id=user_id, message_id=update.message.message_id)

        username = update.message.from_user.username or update.message.from_user.first_name or str(user_id)
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("💬 Відповісти", callback_data=f"reply_{user_id}")]])

        context.bot.send_message(
            chat_id=admin_id,
            text=f"💬 Звернення від @{username}\nТема: {topic}",
            reply_to_message_id=fwd.message_id,
            reply_markup=reply_markup
        )

    update.message.reply_text("✅ Ваше звернення надіслано. Очікуйте відповідь.")

# Обробка відповіді від адміністратора

def handle_reply(update: Update, context: CallbackContext):
    if update.message.reply_to_message:
        for line in update.message.reply_to_message.text.split("\n"):
            if line.startswith("💬 Звернення від"):
                try:
                    user_line = line.split("@")[1].strip()
                    for user_id in user_data:
                        chat = context.bot.get_chat(user_id)
                        if user_line.lower() in [
                            (chat.username or '').lower(),
                            (chat.first_name or '').lower()
                        ]:
                            context.bot.send_message(chat_id=user_id, text=f"📩 Відповідь від адміністратора: {update.message.text}")
                            return
                except Exception:
                    continue
    update.message.reply_text("❗ Не вдалося знайти користувача для відповіді.")

# Панель адміністратора

def admin(update: Update, context: CallbackContext):
    if update.message.chat_id in ADMIN_CHAT_IDS:
        update.message.reply_text("🔐 Панель адміністратора: /last")

# Перегляд останніх звернень

def last(update: Update, context: CallbackContext):
    if update.message.chat_id in ADMIN_CHAT_IDS:
        text = "🗂️ Останні звернення:\n"
        for uid, msgs in dialog_history.items():
            latest = msgs[-1][1]
            topic = msgs[-1][0]
            short_text = latest[:30] + "..." if len(latest) > 30 else latest
            text += f"👤 ID: {uid}, {topic} — {short_text}\n"
        update.message.reply_text(text or "Немає звернень.")

# Головна функція запуску

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin))
    dp.add_handler(CommandHandler("last", last))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.reply & Filters.text, handle_reply))
    dp.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.video | Filters.document | Filters.voice, forward_message))

    print("🤖 Бот запущено")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
