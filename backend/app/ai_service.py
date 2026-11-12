import os
from sentence_transformers import SentenceTransformer, CrossEncoder 
from gigachat import GigaChat
import traceback
import json
import difflib
# --- 1. Локальная модель для эмбеддингов ---
# Загружаем легкую (34M) модель, которая отлично понимает русский язык
print("Загрузка модели эмбеддингов USER-bge-m3...")
embed_model = SentenceTransformer('deepvk/USER-bge-m3')


def get_embedding(text: str) -> list[float]:
    """Возвращает векторное представление текста (384 числа)."""
    return embed_model.encode(text).tolist()

print("Загрузка реранкера DiTy/cross-encoder-russian-msmarco...")
reranker_model = CrossEncoder('DiTy/cross-encoder-russian-msmarco', max_length=512)

# --- 2. GigaChat для генерации ответов ---
# Отключаем проверку SSL-сертификатов для упрощения тестов (в продакшене — только с сертификатами Минцифры)
giga = GigaChat(
    base_url="https://api.giga.chat/v1", # Явно указываем актуальный адрес
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    verify_ssl_certs=False,
    model="GigaChat-2", # <-- Меняем на актуальное название
)

async def ask_gigachat(question: str, context_chunks: list[str]) -> str:
    """Отправляет вопрос и найденный контекст в GigaChat."""
    context = "\n\n---\n\n".join(context_chunks)
    system_prompt = (
        "Ты — строгий академический ассистент. Твоя задача — ответить на вопрос, используя ТОЛЬКО предоставленный контекст.\n"
        "Правила:\n"
        "1. Если в контексте есть ответ, дай его и укажи, из какого документа он взят.\n"
        "2. Если в контексте нет прямого ответа, но есть куски, которые позволяют его вывести — сделай это.\n"
        "3. Если контекст не содержит нужной информации, честно напиши: 'В загруженных материалах нет ответа на этот вопрос. Но я знаю, что...' и дай ответ из своих знаний.\n"
        "4. Не выдумывай факты, которых нет в тексте."
    )
    user_prompt = f"Контекст:\n{context}\n\nВопрос: {question}"

    response = await giga.achat.create({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
    })
    return response.messages[0].content

async def extract_search_keywords(question: str) -> str:
    prompt = f"Напиши через запятую главные слова из этого вопроса, без лишних слов: {question}"
    
    try:
        response = await giga.achat.create({
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        })
        
        content = response.choices[0].message.content if hasattr(response, 'choices') else response.messages[0].content
        
        if isinstance(content, list):
            keywords = " ".join([str(item.get("text", "")) for item in content if isinstance(item, dict)])
        else:
            keywords = str(content)
            
        keywords = keywords.replace('"', '').replace("'", "").strip()
        
        if not keywords:
            return question
            
        print(f"DEBUG: GigaChat расширил: {keywords}")
        return keywords
        
    except Exception as e:
        return question

async def extract_metadata_from_text(text: str) -> dict:
    """Просит GigaChat извлечь метаданные из первых страниц документа."""
    prompt = (
        f"Проанализируй текст документа и извлеки метаданные. "
        f"Верни ответ СТРОГО в формате JSON, без markdown-разметки (без ```json). "
        f"Обязательные поля:\n"
        f"- title: краткое название документа (до 100 символов)\n"
        f"- discipline: название предмета (например, 'Математический анализ')\n"
        f"- teacher: ФИО преподавателя (если есть, иначе пустая строка '')\n"
        f"- course: номер курса (целое число от 1 до 6, если не удается определить - null)\n\n"
        f"Текст:\n{text[:3000]}"
    )
    
    try:
        response = await giga.achat.create({
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        })
        
        content = response.choices[0].message.content if hasattr(response, 'choices') else response.messages[0].content
        
        if isinstance(content, list):
            content = "".join([str(item.get("text", "")) for item in content if isinstance(item, dict)])
            
        # Очищаем от возможной markdown-разметки
        clean_json = str(content).replace("```json", "").replace("```", "").strip()
        
        data = json.loads(clean_json)
        print(f"DEBUG: ИИ извлек метаданные: {data}")
        return data
    except Exception as e:
        print(f"Ошибка извлечения метаданных: {e}")
        return {}


# --- СПИСОК ДОПУСТИМЫХ ПРЕДМЕТОВ (ВУЗ) ---
ALLOWED_DISCIPLINES = [
    "Математический анализ",
    "Линейная алгебра и геометрия",
    "Дискретная математика",
    "Теория вероятностей и математическая статистика",
    "Физика",
    "Информатика",
    "Программирование",
    "Базы данных",
    "Операционные системы",
    "Экономика",
    "История",
    "Другое" # Если предмет не подходит ни под одну категорию
]

def extract_metadata_sync(text: str) -> dict:
    import os
    from gigachat import GigaChat
    
    local_giga = GigaChat(
        base_url="https://api.giga.chat/v1",
        credentials=os.getenv("GIGACHAT_CREDENTIALS"),
        verify_ssl_certs=False,
        model="GigaChat-2",
    )
    
    # Формируем список для промпта
    disciplines_str = "\n".join([f"- {d}" for d in ALLOWED_DISCIPLINES])

    prompt = (
        f"Проанализируй текст документа. Верни строго 4 строки, без лишних слов и приветствий:\n"
        f"Название: [краткое название до 100 символов]\n"
        f"Предмет: [выбери строго ОДИН из списка ниже]\n"
        f"Преподаватель: [ФИО или пусто]\n"
        f"Курс: [номер или пусто]\n\n"
        f"СПИСОК ПРЕДМЕТОВ:\n{disciplines_str}\n\n"
        f"Если ни один предмет не подходит, выбери 'Другое'. Не придумывай свои названия!\n\n"
        f"Текст:\n{text[:3000]}"
    )
    
    try:
        response = local_giga.chat.create({
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        })
        
        content = response.choices[0].message.content if hasattr(response, 'choices') else response.messages[0].content
        if isinstance(content, list):
            content_str = "".join([str(getattr(c, 'text', '')) for c in content])
        else:
            content_str = str(content)

        data = {}
        for line in content_str.split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                k = k.strip().lower().replace('-', '').replace('*', '').replace('"', '').replace("'", "")
                v = v.strip()
                
                if v.lower() in ["не указано", "не указан", "пусто", "none", "null", "нет"]:
                    v = ""

                if 'название' in k: data['title'] = v
                elif 'предмет' in k or 'дисциплина' in k: data['discipline'] = v
                elif 'преподаватель' in k: data['teacher'] = v
                elif 'курс' in k: 
                    digits = ''.join(filter(str.isdigit, v))
                    if digits: data['course'] = int(digits)

        # --- ПРОВЕРКА И КОРРЕКТИРОВКА ПРЕДМЕТА ---
        if 'discipline' in data and data['discipline']:
            llm_disc = data['discipline']
            # Ищем максимально близкое совпадение из нашего списка (порог 0.4 для мягкости)
            matches = difflib.get_close_matches(llm_disc, ALLOWED_DISCIPLINES, n=1, cutoff=0.4)
            if matches:
                # Если нашли близкое (например, ИИ написал "Матан", а в списке "Математический анализ")
                data['discipline'] = matches[0]
            else:
                # Если совсем не то - ставим "Другое"
                data['discipline'] = "Другое"

        print(f"DEBUG: ИИ извлек метаданные: {data}")
        return data
    except Exception as e:
        print(f"Ошибка извлечения метаданных: {e}")
        return {}