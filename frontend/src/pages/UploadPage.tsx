import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadMaterial } from "../api";

export default function UploadPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    title: "",
    description: "",
    discipline: "",
    type: "lab",
  });
  const [files, setFiles] = useState<FileList | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title) return setError("Введите название");
    setLoading(true);
    setError("");

    const data = new FormData();
    data.append("title", form.title);
    data.append("description", form.description);
    data.append("discipline", form.discipline);
    data.append("type", form.type);
    
    if (files) {
      for (let i = 0; i < files.length; i++) {
        data.append("files", files[i]);
      }
    }

    try {
      await uploadMaterial(data);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Ошибка при загрузке.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="bg-white border border-gray-200 rounded-xl p-8 shadow-sm">
        <h1 className="text-2xl font-bold mb-6">Загрузить материал</h1>
        {error && <div className="mb-6 p-4 bg-red-50 text-red-700 border border-red-200 rounded-lg">{error}</div>}
        
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Название *</label>
            <input 
              type="text" 
              value={form.title} 
              onChange={e => setForm({...form, title: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="Например: Лабораторная работа №3"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
            <textarea 
              value={form.description} 
              onChange={e => setForm({...form, description: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none min-h-[100px]"
              placeholder="Кратко опишите, что внутри..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Дисциплина</label>
              <input 
                type="text" 
                value={form.discipline} 
                onChange={e => setForm({...form, discipline: e.target.value})}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                placeholder="Матанализ"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Тип</label>
              <select 
                value={form.type} 
                onChange={e => setForm({...form, type: e.target.value})}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
              >
                <option value="lab">Лабораторная</option>
                <option value="lecture">Лекция</option>
                <option value="test">Тест</option>
                <option value="exam">Экзамен</option>
                <option value="report">Отчёт</option>
                <option value="other">Другое</option>
              </select>
            </div>
          </div>

          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:bg-gray-50 transition-colors">
            <label className="cursor-pointer">
              <span className="text-blue-600 font-medium">Нажмите, чтобы выбрать файлы</span>
              <span className="text-gray-500 block text-sm mt-1">(можно несколько)</span>
              <input 
                type="file" 
                multiple
                onChange={e => setFiles(e.target.files)}
                className="hidden"
              />
            </label>
            {files && <p className="mt-3 text-sm text-green-600 font-medium">Выбрано файлов: {files.length}</p>}
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors mt-2"
          >
            {loading ? "Загрузка..." : "Опубликовать"}
          </button>
        </form>
      </div>
    </div>
  );
}