import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createThread } from "../api";

export default function CreateThreadPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("free");
  const [content, setContent] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return setError("Заполните название и текст сообщения");
    
    setLoading(true);
    setError("");

    try {
      const data = await createThread({ title, category, first_post: content });
      navigate(`/forum/${data.id}`);
    } catch (err: any) {
      setError(err.message || "Ошибка при создании темы");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="bg-white border border-gray-200 rounded-xl p-8 shadow-sm">
        <h1 className="text-2xl font-bold mb-6">Создать новую тему</h1>
        {error && <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg">{error}</div>}
        
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Раздел</label>
            <select 
              value={category} 
              onChange={e => setCategory(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
            >
              <option value="free">Свободное общение</option>
              <option value="teachers">Преподаватели</option>
              <option value="solutions">Разбор решений</option>
              <option value="specific_people">Конкретные люди</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Название темы</label>
            <input 
              type="text" 
              value={title} 
              onChange={e => setTitle(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="О чем хотите поговорить?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Первое сообщение</label>
            <textarea 
              value={content} 
              onChange={e => setContent(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none min-h-[150px]"
              placeholder="Напишите ваш вопрос или мысль..."
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Отправка..." : "Опубликовать тему"}
          </button>
        </form>
      </div>
    </div>
  );
}