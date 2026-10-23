import os
import logging
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://backend:8000"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для перевода текста кнопок в значения для API
FILTER_MAP = {
    "🌐 Все": "all",
    "🧪 Лабы": "lab",
    "📖 Лекции": "lecture",
    "📝 Тесты": "test",
    "🎓 Экзамены": "exam"
}

def get_main_keyboard():
    """Нижнее меню с фильтрами."""
    kb = [
        [KeyboardButton(text="🌐 Все"), KeyboardButton(text="🧪 Лабы")],
        [KeyboardButton(text="📖 Лекции"), KeyboardButton(text="📝 Тесты")],
        [KeyboardButton(text="🎓 Экзамены")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Введите название...")

def get_results_inline_keyboard(current_filter: str):
    """Инлайн-кнопка под результатами для быстрого сброса фильтра."""
    if current_filter == "all":
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Искать во всех файлах", callback_data="reset_filter")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    # По умолчанию ставим фильтр "Все"
    await state.update_data(active_filter="all")
    await message.answer(
        "Привет! Я бот Студенческого хаба. 🎓\n"
        "Выбери нужный раздел на клавиатуре внизу и напиши название файла. Я найду его в базе.",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text)
async def handle_message(message: types.Message, state: FSMContext):
    text = message.text
    
    if text in FILTER_MAP:
        new_filter = FILTER_MAP[text]
        await state.update_data(active_filter=new_filter)
        await message.answer(f"Фильтр изменен на: {text}\nТеперь напиши название файла.")
        return

    data = await state.get_data()
    active_filter = data.get("active_filter", "all")
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    params = {"q": text}
    if active_filter != "all":
        params["type"] = active_filter

    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            resp = await client.get(f"{API_URL}/search", params=params)
            items = resp.json().get("items", [])

            filter_name = text if active_filter == "all" else f"{active_filter}"
            for k, v in FILTER_MAP.items():
                if v == active_filter:
                    filter_name = k
                    break
                    
            response_text = f"🔎 Поиск: *{text}* (Раздел: {filter_name})\n\n"

            if not items:
                response_text += "Ничего не найдено 😔 Попробуй изменить запрос или выбрать другой раздел."
            else:
                for i, item in enumerate(items[:5], 1):
                    title = item["title"]
                    disc = item["discipline"] or "Без дисциплины"
                    web_url = f"http://localhost:5173/m/{item['id']}"
                    # Выводим URL в обратных кавычках для быстрого копирования
                    response_text += f"{i}. 📄 **{title}**\n   {disc}\n   🔗 `{web_url}`\n\n"

                # Отправляем сообщение (disable_web_page_preview=True уберет огромный белый квадрат внизу)
                await message.answer(
                    response_text, 
                    reply_markup=get_results_inline_keyboard(active_filter),
                    parse_mode="Markdown", 
                    disable_web_page_preview=True 
                )
                return # Выходим, чтобы не отправить сообщение дважды

            # Если items пустой
            await message.answer(response_text, parse_mode="Markdown")

        except Exception as e:
            logging.error(f"Ошибка API: {e}")
            await message.answer("Ошибка сервера. Попробуйте позже.")
            
@dp.callback_query(F.data == "reset_filter")
async def reset_filter(callback: types.CallbackQuery, state: FSMContext):
    # Сбрасываем фильтр обратно на "Все"
    await state.update_data(active_filter="all")
    await callback.answer("Фильтр сброшен на 'Все'")
    
    # Убираем инлайн-кнопку из старого сообщения
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Теперь поиск идет по всем файлам. Напиши название заново.")

if __name__ == "__main__":
    logging.info("Бот запущен...")
    dp.run_polling(bot)