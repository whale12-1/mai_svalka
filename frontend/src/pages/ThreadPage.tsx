import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getThread, createPost } from "../api";

export default function ThreadPage() {
  const { id } = useParams();
  const [thread, setThread] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  const [reply, setReply] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadThread = () => {
    if (id) {
      setLoading(true);
      getThread(Number(id))
        .then(setThread)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  };

  useEffect(() => {
    loadThread();
  }, [id]);

  const handleReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reply.trim() || !id) return;
    
    setIsSubmitting(true);
    try {
      await createPost(Number(id), reply);
      setReply("");
      loadThread(); // Перезагружаем ветку, чтобы увидеть новый пост
    } catch (err) {
      alert("Ошибка при отправке сообщения");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="p-10 text-center text-gray-500">Загрузка...</div>;
  if (!thread) return <div className="p-10 text-center text-red-500">Тема не найдена</div>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <Link to="/forum" className="text-blue-600 hover:underline mb-6 inline-block">&larr; Назад к форуму</Link>
      
      <div className="bg-white border border-gray-200 rounded-t-xl p-6 shadow-sm border-b-0">
        <h1 className="text-2xl font-bold mb-2">{thread.title}</h1>
        <div className="text-sm text-gray-500">
          Создано {new Date(thread.created_at).toLocaleString("ru-RU")}
        </div>
      </div>

      {/* Список сообщений */}
      <div className="bg-white border border-gray-200 rounded-b-xl shadow-sm divide-y divide-gray-100">
        {thread.posts.map((post: any, index: number) => (
          <div key={post.id} className={`p-6 ${index === 0 ? 'bg-blue-50/30' : ''}`}>
            <div className="flex justify-between items-start mb-3">
              <div className="font-medium text-gray-900 bg-gray-100 px-3 py-1 rounded text-sm">
                Аноним
              </div>
              <div className="text-xs text-gray-400">
                {new Date(post.created_at).toLocaleString("ru-RU")}
              </div>
            </div>
            <p className="text-gray-800 whitespace-pre-wrap">{post.content}</p>
          </div>
        ))}
      </div>

      {/* Форма ответа */}
      <div className="mt-8 bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h3 className="font-semibold mb-3">Ответить в теме</h3>
        <form onSubmit={handleReply}>
          <textarea
            value={reply}
            onChange={e => setReply(e.target.value)}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none min-h-[100px] mb-3"
            placeholder="Напишите ваше сообщение..."
          />
          <button 
            type="submit" 
            disabled={isSubmitting || !reply.trim()}
            className="px-6 py-2 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? "Отправка..." : "Отправить"}
          </button>
        </form>
      </div>
    </div>
  );
}