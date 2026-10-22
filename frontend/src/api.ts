export async function search(q: string, params: Record<string, string | number | undefined> = {}) {
  const usp = new URLSearchParams({ q, ...Object.fromEntries(Object.entries(params).filter(([,v]) => v != null && v !== "").map(([k,v]) => [k, String(v)])) });
  const r = await fetch(`/api/search?${usp}`, { credentials: "include" });
  return r.json();
}
export async function getMaterial(id: number) {
  const r = await fetch(`/api/materials/${id}`, { credentials: "include" });
  return r.json();
}

export async function uploadMaterial(formData: FormData) {
  const res = await fetch('/api/materials', {
    method: 'POST',
    body: formData,
    // ВАЖНО: credentials: 'include' заставляет браузер прикрепить 
    // HttpOnly cookie (наш анонимный токен), иначе бэкенд выдаст 403 или 401
    credentials: 'include',
    
    // ВАЖНО: Мы НЕ ставим заголовок 'Content-Type': 'multipart/form-data'.
    // Fetch API сделает это автоматически и добавит правильный boundary.
  });

  if (!res.ok) {
    // Пытаемся вытащить текст ошибки из JSON, который возвращает FastAPI
    let errorMessage = `Ошибка сервера: ${res.status}`;
    try {
      const errorData = await res.json();
      if (errorData.detail) {
        // Если FastAPI вернул детальную ошибку валидации (Pydantic)
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((e: any) => e.msg).join(', ');
        }
      }
    } catch (e) {
      // Если ответ не JSON (например, HTML страница с ошибкой 500)
      errorMessage = `Ошибка ${res.status}: ${res.statusText}`;
    }
    
    throw new Error(errorMessage);
  }

  return res.json();
}

// --- ФОРУМ ---

export async function getThreads(category?: string) {
  const url = category ? `/api/threads?category=${category}` : '/api/threads';
  const res = await fetch(url, { credentials: 'include' });
  if (!res.ok) throw new Error('Failed to fetch threads');
  return res.json();
}

export async function getThread(id: number) {
  const res = await fetch(`/api/threads/${id}`, { credentials: 'include' });
  if (!res.ok) throw new Error('Thread not found');
  return res.json();
}

export async function createThread(data: { title: string; category: string; first_post: string }) {
  const res = await fetch('/api/threads', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to create thread');
  return res.json();
}

export async function createPost(threadId: number, content: string) {
  const res = await fetch(`/api/threads/${threadId}/posts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to create post');
  return res.json();
}