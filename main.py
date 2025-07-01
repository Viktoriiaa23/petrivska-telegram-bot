import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔐 Токен бота (встав вручну або через .env)
BOT_TOKEN = '7996564047:AAFJzRYg8ICsUVzOe6oYOZt3v2EVG7UIC_Y'

# 🛡 ID адміністраторів
ADMINS = [424594836, 855759233]  # 🔁 Заміни на справжні

# 🔍 Логування
logging.basicConfig(level=logging.INFO)

# 🤖 Ініціалізація
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# 🧠 Стан відповіді
class AnswerState(StatesGroup):
    waiting_for_reply = State()

# 🔁 Кому відповідає адмін
admin_reply_map = {}

# 🔹 Команда /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📣 Надіслати новину", "❓ Поставити питання", "💬 Інше")
    await message.answer(
        "👋 Вітаємо в боті ПЕТРІВСЬКОЇ ГРОМАДИ!\n\nОберіть категорію свого звернення:",
        reply_markup=keyboard
    )

# 🔹 Обробка категорії
@dp.message_handler(lambda msg: msg.text in ["📣 Надіслати новину", "❓ Поставити питання", "💬 Інше"])
async def category_chosen(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("✉️ Тепер надішліть своє звернення — текст, фото, відео або документ.")

# 🔹 Повідомлення користувача
@dp.message_handler(content_types=types.ContentType.ANY)
async def handle_message(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    category = user_data.get("category", "Без категорії")
    sender = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    caption = f"📩 НОВЕ ЗВЕРНЕННЯ\nКатегорія: {category}\nВід: {sender}"

    # Кнопка відповіді — тільки для "Поставити питання"
    reply_markup = None
    if category == "❓ Поставити питання":
        reply_markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📩 Відповісти", callback_data=f"reply_{message.from_user.id}")
        )

    for admin_id in ADMINS:
        try:
            if message.content_type == "text":
                await bot.send_message(admin_id, f"{caption}\n\n{message.text}", reply_markup=reply_markup)
            elif message.content_type == "photo":
                await bot.send_photo(admin_id, message.photo[-1].file_id, caption=caption, reply_markup=reply_markup)
            elif message.content_type == "video":
                await bot.send_video(admin_id, message.video.file_id, caption=caption, reply_markup=reply_markup)
            elif message.content_type == "document":
                await bot.send_document(admin_id, message.document.file_id, caption=caption, reply_markup=reply_markup)
            else:
                await bot.send_message(admin_id, f"{caption}\n\n[Невідомий тип повідомлення]", reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"❌ Не вдалося надіслати повідомлення адміну {admin_id}: {e}")

# 🔹 Обробка натискання "📩 Відповісти"
@dp.callback_query_handler(lambda c: c.data.startswith("reply_"))
async def process_reply_button(callback_query: types.CallbackQuery, state: FSMContext):
    admin_id = callback_query.from_user.id
    target_user_id = int(callback_query.data.split("_")[1])
    admin_reply_map[admin_id] = target_user_id

    await AnswerState.waiting_for_reply.set()
    await bot.send_message(admin_id, "✏️ Введіть відповідь, яка буде надіслана користувачеві.")
    await callback_query.answer()

# 🔹 Надсилання відповіді
@dp.message_handler(state=AnswerState.waiting_for_reply, content_types=types.ContentType.TEXT)
async def send_admin_reply(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    target_user_id = admin_reply_map.get(admin_id)

    if not target_user_id:
        await message.answer("⚠️ Помилка: не знайдено користувача для відповіді.")
        await state.finish()
        return

    try:
        await bot.send_message(
            target_user_id,
            f"📩 Відповідь від адміністрації громади:\n\n{message.text}"
        )
        await message.answer("✅ Відповідь успішно надіслана.")
    except Exception as e:
        await message.answer("⚠️ Не вдалося надіслати відповідь користувачеві.")
        logging.error(f"❗ Помилка при надсиланні відповіді: {e}")

    await state.finish()

# ▶️ Запуск
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
