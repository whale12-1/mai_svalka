import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getThreads } from "../api";

const CATEGORIES = [
  { id: "free", label: "Свободное общение" },
  { id: "teachers", label: "Преподаватели" },
  { id: "solutions", label: "Разбор решений" },
  { id: "specific_people", label: "Конкретные люди" },
];

export default function ForumPage() {
  const [threads, setThreads] = useState<any[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>("free");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getThreads(activeCategory)
      .then(setThreads)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [activeCategory]);

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 flex gap-8">
      
      {/* Боковая панель с категориями */}
      <div className="w-64 flex-shrink-0">
        <h2 className="text-xl font-bold mb-4">Разделы</h2>
        <ul className="space-y-2">
          {CATEGORIES.map(c => (
            <li key={c.id}>
              <button
                onClick={() => setActiveCategory(c.id)}
                className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                  activeCategory === c.id 
                    ? "bg-blue-50 text-blue-700 font-medium" 
                    : "hover:bg-gray-100 text-gray-700"
                }`}
              >
                {c.label}
              </button>
            </li>
          ))}
        </ul>
        
        <Link 
          to="/forum/new" 
          className="mt-8 block w-full text-center bg-blue-600 text-white px-4 py-3 rounded-lg hover:bg-blue-700 font-medium transition-colors shadow-sm"
        >
          + Создать тему
        </Link>
      </div>

      {/* Список веток */}
      <div className="flex-1">
        <h1 className="text-3xl font-bold mb-6">
          {CATEGORIES.find(c => c.id === activeCategory)?.label}
        </h1>
        
        {loading ? (
          <p className="text-gray-500">Загрузка тем...</p>
        ) : threads.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-500">
            В этом разделе пока нет тем. Станьте первым!
          </div>
        ) : (
          <div className="space-y-3">
            {threads.map(t => (
              <Link 
                key={t.id} 
                to={`/forum/${t.id}`}
                className="block bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
              >
                <h3 className="text-lg font-semibold text-blue-600 mb-1">{t.title}</h3>
                <div className="text-sm text-gray-500 flex justify-between">
                  <span>Создано: {new Date(t.created_at).toLocaleDateString("ru-RU")}</span>
                  <span>{t.posts?.length || 0} ответов</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}