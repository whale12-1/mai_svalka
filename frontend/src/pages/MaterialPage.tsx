import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getMaterial } from "../api";

export default function MaterialPage() {
  const { id } = useParams();
  const [m, setM] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      getMaterial(Number(id))
        .then(setM)
        .catch(() => setError("Не удалось загрузить материал."));
    }
  }, [id]);

  if (error) return <div className="p-10 text-center text-red-500 font-medium">{error}</div>;
  if (!m) return <div className="p-10 text-center text-gray-500">Загрузка…</div>;

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <Link to="/" className="text-blue-600 hover:underline mb-6 inline-block">&larr; Назад к поиску</Link>
      
      <div className="bg-white border border-gray-200 rounded-xl p-8 shadow-sm">
        <h1 className="text-3xl font-bold mb-2">{m.title}</h1>
        <div className="flex gap-3 text-sm text-gray-500 mb-6">
          <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full">{m.discipline || "Общее"}</span>
          <span className="bg-gray-100 px-3 py-1 rounded-full">{m.type}</span>
          {m.teacher && <span>Преподаватель: {m.teacher}</span>}
        </div>

        {m.description && (
          <p className="text-gray-700 mb-8 whitespace-pre-wrap">{m.description}</p>
        )}

        <h3 className="text-lg font-semibold mb-4 border-b pb-2">Прикрепленные файлы</h3>
        <ul className="space-y-3">
          {m.files.map((f: any) => (
            <li key={f.id} className="flex items-center justify-between bg-gray-50 p-4 rounded-lg border border-gray-100">
              <div className="flex items-center gap-3">
                <span className="text-2xl">📄</span>
                <div>
                  <a href={f.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 font-medium hover:underline">
                    {f.filename}
                  </a>
                  <div className="text-xs text-gray-400">{(f.size / 1024).toFixed(1)} KB</div>
                </div>
              </div>
              <a 
                href={f.url} 
                download
                className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                Скачать
              </a>
            </li>
          ))}
          {m.files.length === 0 && <p className="text-gray-500 text-sm">Файлы отсутствуют.</p>}
        </ul>
      </div>
    </div>
  );
}