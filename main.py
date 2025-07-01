import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMINS = [123456789, 987654321]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AnswerState(StatesGroup):
    waiting_for_reply = State()

admin_reply_map = {}

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📣 Надіслати НОВИНУ", "❓ Задати питання", "💬 Інше")
    await message.answer(
        "👋 Вітаємо в боті ПЕТРІВСЬКОЇ ГРОМАДИ!

Оберіть категорію свого звернення:",
        reply_markup=keyboard
    )

@dp.message_handler(lambda msg: msg.text in ["📣 Надіслати НОВИНУ", "❓ Задати питання", "💬 Інше"])
async def category_chosen(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("✉️ Тепер надішліть своє звернення (текст, фото, відео або документ).")

@dp.message_handler(content_types=types.ContentType.ANY)
async def handle_message(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    category = user_data.get("category", "Без категорії")
    sender = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    caption = f"📩 НОВЕ ЗВЕРНЕННЯ
Категорія: {category}
Від: {sender}"

    reply_button = InlineKeyboardMarkup()
    reply_button.add(InlineKeyboardButton("📩 Відповісти", callback_data=f"reply_{message.from_user.id}"))

    for admin_id in ADMINS:
        try:
            if message.content_type == "text":
                await bot.send_message(admin_id, f"{caption}

{message.text}", reply_markup=reply_button)
            elif message.content_type == "photo":
                await bot.send_photo(admin_id, message.photo[-1].file_id, caption=caption, reply_markup=reply_button)
            elif message.content_type == "video":
                await bot.send_video(admin_id, message.video.file_id, caption=caption, reply_markup=reply_button)
            elif message.content_type == "document":
                await bot.send_document(admin_id, message.document.file_id, caption=caption, reply_markup=reply_button)
            else:
                await bot.send_message(admin_id, f"{caption}

[Невідомий тип повідомлення]", reply_markup=reply_button)
        except Exception as e:
            logging.error(f"❌ Не вдалося надіслати повідомлення адміну {admin_id}: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith("reply_"))
async def process_reply_button(callback_query: types.CallbackQuery, state: FSMContext):
    admin_id = callback_query.from_user.id
    target_user_id = int(callback_query.data.split("_")[1])
    admin_reply_map[admin_id] = target_user_id

    await AnswerState.waiting_for_reply.set()
    await bot.send_message(admin_id, "✏️ Введіть відповідь, яка буде надіслана користувачу.")
    await callback_query.answer()

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
            f"📩 Відповідь від адміністрації громади:

{message.text}"
        )
        await message.answer("✅ Відповідь надіслана успішно.")
    except Exception as e:
        await message.answer("⚠️ Не вдалося надіслати відповідь користувачу.")
        logging.error(f"❗ Помилка при відповіді: {e}")

    await state.finish()

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)