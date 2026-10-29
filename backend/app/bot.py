import os
import logging
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://backend:8000"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Состояния ---
class UploadStates(StatesGroup):
    waiting_for_file = State()
    waiting_for_title = State()
    waiting_for_discipline = State()
    waiting_for_type = State()

class FilterStates(StatesGroup):
    waiting_for_discipline = State()
    waiting_for_teacher = State()
    waiting_for_institute = State()

FILTER_MAP = {
    "🌐 Все": "all",
    "🧪 Лабы": "lab",
    "📖 Лекции": "lecture",
    "📝 Тесты": "test"
}

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="🌐 Все"), KeyboardButton(text="🧪 Лабы")],
        [KeyboardButton(text="📖 Лекции"), KeyboardButton(text="📝 Тесты")],
        [KeyboardButton(text="🔍 Фильтры"), KeyboardButton(text="📤 Загрузить файл")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Введите название...")

def get_filter_keyboard(data: dict):
    """Создает меню фильтров с отображением текущих значений."""
    disc = data.get("f_discipline", "Любой")
    teacher = data.get("f_teacher", "Любой")
    inst = data.get("f_institute", "Любая")
    course = data.get("f_course", "Любой")
    
    kb = [
        [InlineKeyboardButton(text=f"Предмет: {disc}", callback_data="set_f_discipline")],
        [InlineKeyboardButton(text=f"Преподаватель: {teacher}", callback_data="set_f_teacher")],
        [InlineKeyboardButton(text=f"Кафедра: {inst}", callback_data="set_f_institute")],
        [InlineKeyboardButton(text=f"Курс: {course}", callback_data="set_f_course")],
        [InlineKeyboardButton(text="❌ Сбросить фильтры", callback_data="reset_filters")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_course_keyboard():
    kb = [
        [InlineKeyboardButton(text="1", callback_data="c_1"), InlineKeyboardButton(text="2", callback_data="c_2"), InlineKeyboardButton(text="3", callback_data="c_3")],
        [InlineKeyboardButton(text="4", callback_data="c_4"), InlineKeyboardButton(text="5", callback_data="c_5"), InlineKeyboardButton(text="6", callback_data="c_6")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_filters")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_type_keyboard():
    kb = [
        [InlineKeyboardButton(text="Лабораторная", callback_data="type_lab")],
        [InlineKeyboardButton(text="Лекция", callback_data="type_lecture")],
        [InlineKeyboardButton(text="Тест", callback_data="type_test")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_upload")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(active_filter="all")
    await message.answer(
        "Привет! Я бот Студенческого хаба. 🎓\n"
        "Ищи файлы или настрой фильтры, чтобы найти точную дисциплину.",
        reply_markup=get_main_keyboard()
    )

# --- ОСНОВНОЙ ОБРАБОТЧИК (Поиск и меню) ---
@dp.message(F.text, StateFilter(None))
async def handle_message(message: types.Message, state: FSMContext):
    text = message.text

    if text == "📤 Загрузить файл":
        await state.set_state(UploadStates.waiting_for_file)
        await message.answer("Отправьте мне PDF-файл, который хотите загрузить.")
        return

    if text == "🔍 Фильтры":
        data = await state.get_data()
        await message.answer("Настройте параметры поиска:", reply_markup=get_filter_keyboard(data))
        return

    if text in FILTER_MAP:
        new_filter = FILTER_MAP[text]
        await state.update_data(active_filter=new_filter)
        await message.answer(f"Раздел изменен на: {text}")
        return

    # Логика поиска
    data = await state.get_data()
    params = {"q": text}
    
    if data.get("active_filter") and data["active_filter"] != "all":
        params["type"] = data["active_filter"]
    if data.get("f_discipline"): params["discipline"] = data["f_discipline"]
    if data.get("f_teacher"): params["teacher"] = data["f_teacher"]
    if data.get("f_institute"): params["institute"] = data["f_institute"]
    if data.get("f_course"): params["course"] = data["f_course"]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            resp = await client.get(f"{API_URL}/search", params=params)
            data = resp.json()
            items = data.get("items", [])
            warning_msg = data.get("message", "") # Получаем сообщение об отмене фильтров

            response_text = f"🔎 Поиск: *{text}*\n"
            
            # Выводим активные фильтры
            active_filters = []
            if params.get("discipline"): active_filters.append(f"Предмет: {params['discipline']}")
            if params.get("teacher"): active_filters.append(f"Препод: {params['teacher']}")
            if params.get("course"): active_filters.append(f"Курс: {params['course']}")
            if params.get("type"): active_filters.append(f"Тип: {params['type']}")
            
            if active_filters:
                response_text += " | ".join(active_filters) + "\n\n"
            else:
                response_text += "\n"

            # Если бэкенд вернул предупреждение (что это не 100% совпадение)
            if warning_msg:
                response_text += f"ℹ️ _Совпадение не по всем параметрам, показаны ближайшие варианты._\n\n"

            if not items:
                response_text += "Ничего не найдено 😔"
            else:
                for i, item in enumerate(items[:5], 1):
                    web_url = f"http://localhost:5173/m/{item['id']}"
                    response_text += f"{i}. 📄 **{item['title']}**\n   🔗 `{web_url}`\n\n"

            await message.answer(response_text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logging.error(f"Ошибка API: {e}")
            await message.answer("Ошибка сервера.")

# --- ОБРАБОТЧИКИ ФИЛЬТРОВ (Инлайн-кнопки) ---
@dp.callback_query(F.data.startswith("set_f_"))
async def choose_filter_text(callback: types.CallbackQuery, state: FSMContext):
    filter_type = callback.data.replace("set_f_", "")
    
    prompts = {
        "discipline": ("Введите название предмета (или напишите 'Сброс'):", FilterStates.waiting_for_discipline),
        "teacher": ("Введите ФИО преподавателя (или 'Сброс'):", FilterStates.waiting_for_teacher),
        "institute": ("Введите название кафедры (или 'Сброс'):", FilterStates.waiting_for_institute)
    }
    
    if filter_type in prompts:
        text, next_state = prompts[filter_type]
        await state.set_state(next_state)
        await callback.message.edit_text(text)
    elif filter_type == "course":
        await callback.message.edit_text("Выберите курс:", reply_markup=get_course_keyboard())

@dp.callback_query(F.data.startswith("c_"))
async def save_course(callback: types.CallbackQuery, state: FSMContext):
    course = int(callback.data.split("_")[1])
    await state.update_data(f_course=course)
    data = await state.get_data()
    await callback.message.edit_text("Фильтры обновлены:", reply_markup=get_filter_keyboard(data))

@dp.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text("Настройте параметры поиска:", reply_markup=get_filter_keyboard(data))

@dp.callback_query(F.data == "reset_filters")
async def reset_filters(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(f_discipline=None, f_teacher=None, f_institute=None, f_course=None)
    data = await state.get_data()
    await callback.message.edit_text("Все фильтры сброшены:", reply_markup=get_filter_keyboard(data))

# Обработка текстового ввода для фильтров
@dp.message(FilterStates.waiting_for_discipline, F.text)
async def save_discipline(message: types.Message, state: FSMContext):
    val = None if message.text.lower() == "сброс" else message.text
    await state.update_data(f_discipline=val)
    await state.set_state(None)
    data = await state.get_data()
    await message.answer("Фильтр обновлен.", reply_markup=get_main_keyboard())
    await message.answer("Текущие фильтры:", reply_markup=get_filter_keyboard(data))

@dp.message(FilterStates.waiting_for_teacher, F.text)
async def save_teacher(message: types.Message, state: FSMContext):
    val = None if message.text.lower() == "сброс" else message.text
    await state.update_data(f_teacher=val)
    await state.set_state(None)
    data = await state.get_data()
    await message.answer("Фильтр обновлен.", reply_markup=get_main_keyboard())
    await message.answer("Текущие фильтры:", reply_markup=get_filter_keyboard(data))

@dp.message(FilterStates.waiting_for_institute, F.text)
async def save_institute(message: types.Message, state: FSMContext):
    val = None if message.text.lower() == "сброс" else message.text
    await state.update_data(f_institute=val)
    await state.set_state(None)
    data = await state.get_data()
    await message.answer("Фильтр обновлен.", reply_markup=get_main_keyboard())
    await message.answer("Текущие фильтры:", reply_markup=get_filter_keyboard(data))

# --- ЗАГРУЗКА ФАЙЛОВ (Без изменений) ---
@dp.message(UploadStates.waiting_for_file, F.document)
async def process_file(message: types.Message, state: FSMContext):
    doc = message.document
    if not doc.file_name.endswith(".pdf"):
        await message.answer("Пожалуйста, отправьте файл в формате PDF.")
        return
    await state.update_data(file_id=doc.file_id, file_name=doc.file_name)
    await state.set_state(UploadStates.waiting_for_title)
    await message.answer(f"Файл '{doc.file_name}' принят.\n\nШаг 1 из 3: Введите **Название** материала.")

@dp.message(UploadStates.waiting_for_title, F.text)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(UploadStates.waiting_for_discipline)
    await message.answer("Шаг 2 из 3: Введите **Предмет / Дисциплину**.")

@dp.message(UploadStates.waiting_for_discipline, F.text)
async def process_discipline(message: types.Message, state: FSMContext):
    await state.update_data(discipline=message.text)
    await state.set_state(UploadStates.waiting_for_type)
    await message.answer("Шаг 3 из 3: Выберите тип материала:", reply_markup=get_type_keyboard())

@dp.callback_query(UploadStates.waiting_for_type, F.data.startswith("type_"))
async def process_type(callback: types.CallbackQuery, state: FSMContext):
    mat_type = callback.data.replace("type_", "")
    data = await state.get_data()
    await callback.message.edit_text("Загрузка на сервер...")
    
    file_info = await bot.get_file(data["file_id"])
    file_bytes = await bot.download_file(file_info.file_path)
    
    async with httpx.AsyncClient(trust_env=False) as client:
        files = {'files': (data["file_name"], file_bytes.read(), 'application/pdf')}
        payload = {"title": data["title"], "discipline": data["discipline"], "type": mat_type}
        
        try:
            resp = await client.post(f"{API_URL}/materials", data=payload, files=files)
            if resp.status_code == 201:
                await callback.message.edit_text(f"✅ Файл '{data['title']}' успешно загружен!")
            else:
                await callback.message.edit_text(f"❌ Ошибка сервера: {resp.status_code}")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка соединения: {e}")
            
    await state.clear()
    await message.answer("Вы вернулись в главное меню.", reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "cancel_upload")
async def cancel_upload(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Загрузка отменена.")
    await callback.message.answer("Вы вернулись в главное меню.", reply_markup=get_main_keyboard())

if __name__ == "__main__":
    logging.info("Бот запущен...")
    dp.run_polling(bot)