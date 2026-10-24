import os
from sentence_transformers import SentenceTransformer
from gigachat import GigaChat

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
        "Ты — ассистент студенческой платформы. Отвечай на вопрос, опираясь ТОЛЬКО на предоставленный контекст. "
        "Если в контексте нет ответа, вежливо скажи, что не знаешь. Старайся цитировать источники."
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