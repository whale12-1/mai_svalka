import { useState } from "react";
import { Link } from "react-router-dom";
import { search } from "../api";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await search(q);
      setItems(data.items);
    } finally { setLoading(false); }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 pt-20 pb-10">
      <h1 className="text-4xl font-extrabold text-center mb-8 text-gray-900">
        Найди то, что нужно
      </h1>
      
      <form onSubmit={run} className="flex gap-2 mb-12">
        <input 
          value={q} 
          onChange={e => setQ(e.target.value)} 
          placeholder="Лабораторная по матанализу, билет по физике..."
          className="flex-1 px-5 py-4 text-lg border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
        />
        <button 
          type="submit" 
          disabled={loading}
          className="px-8 py-4 bg-gray-900 text-white text-lg font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
        >
          {loading ? "..." : "Найти"}
        </button>
      </form>

      <div className="space-y-4">
        {items.length === 0 && !loading && q && (
          <p className="text-center text-gray-500 py-10">Ничего не найдено. Попробуйте изменить запрос.</p>
        )}
        
        {items.map((m: any) => (
          <Link 
            to={`/m/${m.id}`} 
            key={m.id} 
            className="block p-5 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
          >
            <h2 className="text-xl font-semibold text-blue-600 mb-1">{m.title}</h2>
            <div className="text-sm text-gray-500 flex gap-3">
              <span className="bg-gray-100 px-2 py-1 rounded">{m.discipline || "Без дисциплины"}</span>
              <span className="bg-gray-100 px-2 py-1 rounded">{m.type}</span>
              <span>Рейтинг: {m.score}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}