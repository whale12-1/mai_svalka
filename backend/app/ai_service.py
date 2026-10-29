import os
from sentence_transformers import SentenceTransformer
from gigachat import GigaChat
import traceback
import json
# --- 1. Локальная модель для эмбеддингов ---
# Загружаем легкую (34M) модель, которая отлично понимает русский язык
print("Загрузка модели эмбеддингов USER2-small...")
embed_model = SentenceTransformer('deepvk/USER2-small')

def get_embedding(text: str) -> list[float]:
    """Возвращает векторное представление текста (384 числа)."""
    return embed_model.encode(text).tolist()

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
        "Ты — ассистент студенческой платформы. Твоя задача — ответить на вопрос пользователя. "
        "Сначала ищи ответ в предоставленном контексте из учебников. "
        "Если в контексте есть точный ответ, используй его и сошлись на источник. "
        "Если в контексте НЕТ ответа, но ты знаешь его из своих общих знаний, ОБЯЗАТЕЛЬНО начни ответ со слов: "
        "'В загруженном учебнике нет этого, но я знаю следующее:' и дай ответ. "
        "Если ты вообще не знаешь, о чем речь, честно скажи об этом."
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