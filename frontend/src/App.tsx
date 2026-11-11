import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import SearchPage from "./pages/SearchPage";
import MaterialPage from "./pages/MaterialPage";
import UploadPage from "./pages/UploadPage";
import ForumPage from "./pages/ForumPage";
import CreateThreadPage from "./pages/CreateThreadPage";
import ThreadPage from "./pages/ThreadPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="site-header">
          <nav className="site-nav">
            <Link to="/" className="brand-lockup">
              <span className="brand-mark">SD</span>
              <span className="brand-name">STUDENT <b>DUMP</b></span>
            </Link>
            <div className="nav-links">
              <Link to="/">Библиотека</Link>
              <Link to="/forum">Форум</Link>
            </div>
            <Link to="/upload" className="nav-upload"><span>＋</span> Загрузить материал</Link>
          </nav>
        </header>
        <main className="site-main">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/m/:id" element={<MaterialPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/forum" element={<ForumPage />} />
            <Route path="/forum/new" element={<CreateThreadPage />} />
            <Route path="/forum/:id" element={<ThreadPage />} />
          </Routes>
        </main>
        <footer className="site-footer">
          <span>STUDENT DUMP</span>
          <span>МАИ · СТУДЕНЧЕСКАЯ БИБЛИОТЕКА</span>
        </footer>
      </div>
    </BrowserRouter>
  );
}
