import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import SearchPage from "./pages/SearchPage";
import MaterialPage from "./pages/MaterialPage";
import UploadPage from "./pages/UploadPage";
import ForumPage from "./pages/ForumPage";           // <-- ДОБАВИТЬ
import CreateThreadPage from "./pages/CreateThreadPage"; // <-- ДОБАВИТЬ
import ThreadPage from "./pages/ThreadPage";         // <-- ДОБАВИТЬ

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
          <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-8">
              <Link to="/" className="text-xl font-bold tracking-tight text-blue-600 hover:text-blue-700">
                Студенческий хаб
              </Link>
              <div className="flex gap-4">
                <Link to="/" className="text-gray-600 hover:text-black font-medium transition-colors">
                  Файлы
                </Link>
                <Link to="/forum" className="text-gray-600 hover:text-black font-medium transition-colors">
                  Форум
                </Link>
              </div>
            </div>
            <Link to="/upload" className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 font-medium transition-colors shadow-sm">
              + Загрузить
            </Link>
          </div>
        </nav>

        <main>
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/m/:id" element={<MaterialPage />} />
            <Route path="/upload" element={<UploadPage />} />
            
            {/* Новые роуты для форума */}
            <Route path="/forum" element={<ForumPage />} />
            <Route path="/forum/new" element={<CreateThreadPage />} />
            <Route path="/forum/:id" element={<ThreadPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}