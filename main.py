from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# 🔐 ВСТАНОВИ СВІЙ ТОКЕН
TOKEN = 'YOUR_BOT_TOKEN_HERE'

# 🔧 ID адміністраторів (в числовому форматі)
ADMIN_CHAT_IDS = [424594836, 855759233]

# Словники для зберігання даних
user_data = {}         # user_id: {'topic': '...'}
dialog_history = {}    # user_id: [ (topic, text) ]
reply_targets = {}     # admin_id: user_id (поточна сесія для відповіді)

# /start — Привітання та вибір теми
def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📣 Надіслати новину", callback_data='news')],
        [InlineKeyboardButton("❓ Задати питання", callback_data='question')],
        [InlineKeyboardButton("💬 Інше", callback_data='general')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("👋 Вітаємо в боті ПЕТРІВСЬКОЇ ГРОМАДИ!\nОберіть тему звернення:", reply_markup=reply_markup)

# Обробка кнопки вибору теми
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {'topic': query.data}
    context.bot.send_message(chat_id=user_id, text="✏️ Надішліть ваше звернення по обраній темі.")

# Пересилання звернень адміністраторам з кнопкою "Відповісти"
def forward_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id
    username = user.username or user.first_name or "Користувач"

    # Перевірка на вибір теми
    if user_id not in user_data:
        update.message.reply_text("❗ Будь ласка, спочатку натисніть /start і оберіть тему.")
        return

    topic = user_data[user_id]['topic']
    message_text = update.message.text or "[Медіа-повідомлення]"

    dialog_history.setdefault(user_id, []).append((topic, message_text))

    for admin_id in ADMIN_CHAT_IDS:
        if update.message.text:
            fwd = update.message.forward(chat_id=admin_id)
        else:
            fwd = context.bot.forward_message(
                chat_id=admin_id,
                from_chat_id=user_id,
                message_id=update.message.message_id
            )

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Відповісти", callback_data=f"reply_{user_id}")]
        ])

        context.bot.send_message(
            chat_id=admin_id,
            text=f"💬 Звернення від @{username}\nТема: {topic}",
            reply_to_message_id=fwd.message_id,
            reply_markup=reply_markup
        )

    update.message.reply_text("✅ Ваше звернення надіслано адміністраторам. Очікуйте відповідь.")

# Callback кнопки "Відповісти" — вибір користувача для відповіді
def select_reply_user(update: Update, context: CallbackContext):
    query = update.callback_query
    admin_id = query.from_user.id

    if admin_id not in ADMIN_CHAT_IDS:
        query.answer("⛔ У вас немає прав адміністратора.")
        return

    query.answer("🔁 Режим відповіді активовано.")
    user_id = int(query.data.split("_")[1])
    reply_targets[admin_id] = user_id

    context.bot.send_message(chat_id=admin_id, text=f"✍️ Тепер ви відповідаєте користувачу ID {user_id}. Надішліть повідомлення.")

# Обробка текстової відповіді адміністратора
def handle_admin_reply(update: Update, context: CallbackContext):
    admin_id = update.message.from_user.id

    if admin_id not in ADMIN_CHAT_IDS:
        return  # Неадмін

    if admin_id not in reply_targets:
        update.message.reply_text("❗ Спочатку натисніть кнопку '💬 Відповісти' під зверненням.")
        return

    user_id = reply_targets[admin_id]
    admin_name = update.message.from_user.full_name or "Адміністратор"
    response_text = f"📩 Відповідь від адміністратора {admin_name}:\n\n{update.message.text}"

    try:
        context.bot.send_message(chat_id=user_id, text=response_text)
        update.message.reply_text("✅ Відповідь надіслано.")
    except Exception as e:
        update.message.reply_text("❗ Не вдалося надіслати повідомлення користувачу.")

# Команда для перегляду останніх звернень
def last(update: Update, context: CallbackContext):
    if update.message.chat_id not in ADMIN_CHAT_IDS:
        return

    text = "🗂️ Останні звернення:\n"
    for uid, msgs in dialog_history.items():
        last_topic, last_msg = msgs[-1]
        short = (last_msg[:30] + "...") if len(last_msg) > 30 else last_msg
        text += f"👤 ID: {uid}, Тема: {last_topic} — {short}\n"
    update.message.reply_text(text or "Немає звернень.")

# Запуск бота
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("last", last))

    dp.add_handler(CallbackQueryHandler(button, pattern="^(news|question|general)$"))
    dp.add_handler(CallbackQueryHandler(select_reply_user, pattern="^reply_"))

    dp.add_handler(MessageHandler(Filters.reply & Filters.text, handle_admin_reply))
    dp.add_handler(MessageHandler(Filters.private & (Filters.text | Filters.photo | Filters.video | Filters.document | Filters.voice), forward_message))

    print("🤖 Бот запущено")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
