import { useState } from "react";
import { Link } from "react-router-dom";
import { search } from "../api";

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setSearched(true);
    try {
      const data = await search(q.trim());
      setItems(data.items || []);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="home-page">
      <section className="hero-section">
        <div className="hero-copy">
          <div className="eyebrow"><span className="status-dot" /> ЦИФРОВАЯ СРЕДА СТУДЕНТОВ МАИ</div>
          <h1>ТВОЯ УЧЁБА.<br /><span>ТВОЯ ТЕРРИТОРИЯ.</span></h1>
          <p className="hero-description">
            Материалы, решения и знания — в одном месте. Находи нужное, делись своим и помогай другим проходить учёбу вместе.
          </p>
          <div className="hero-actions">
            <a href="#search" className="primary-action">Найти материал <span>↗</span></a>
            <Link to="/upload" className="secondary-action">＋ Поделиться материалом</Link>
          </div>
          <div className="hero-meta">
            <div><strong>01</strong><span>БИБЛИОТЕКА</span></div>
            <div><strong>02</strong><span>ОБМЕН ЗНАНИЯМИ</span></div>
            <div><strong>03</strong><span>СООБЩЕСТВО</span></div>
          </div>
        </div>
        <div className="hero-visual" aria-label="Неоновое изображение самолёта с гербом МАИ">
          <img src="/su57-hero.png" alt="Су-57 в неоновой сине-красной цифровой визуализации с гербом МАИ" />
          <div className="visual-vignette" />
          <span className="visual-cross cross-one">＋</span>
          <span className="visual-cross cross-two">＋</span>
          <span className="visual-index">МАИ / 01</span>
          <span className="visual-caption">ENGINEERED FOR<br />THE NEXT GENERATION</span>
        </div>
      </section>

      <section className="search-section" id="search">
        <div className="section-heading">
          <div><span className="section-kicker">ПОИСК ПО БАЗЕ</span><h2>Найди то, что нужно</h2></div>
          <p>Лекции, лабораторные, конспекты<br />и материалы от студентов.</p>
        </div>
        <form onSubmit={run} className="search-form">
          <span className="search-symbol">⌕</span>
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Например: лабораторная по матанализу..." aria-label="Поиск материалов" />
          <button type="submit" disabled={loading}>{loading ? "Ищем..." : "Найти материал"} <span>→</span></button>
        </form>
        <div className="results-list">
          {searched && items.length === 0 && !loading && (
            <div className="empty-state">Ничего не найдено. Попробуйте изменить запрос.</div>
          )}
          {items.map((m: any) => (
            <Link to={`/m/${m.id}`} key={m.id} className="material-result">
              <div className="result-icon">▤</div>
              <div className="result-main">
                <h3>{m.title}</h3>
                <div className="result-meta"><span>{m.discipline || "Без дисциплины"}</span><span>{m.type}</span><span>Рейтинг: {m.score}</span></div>
              </div>
              <span className="result-arrow">↗</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="feature-strip">
        <div><span>01 / БИБЛИОТЕКА</span><strong>Учебные материалы</strong><p>Собирай полезные материалы в одном месте.</p></div>
        <div><span>02 / СООБЩЕСТВО</span><strong>Форум студентов</strong><p>Обсуждай дисциплины и помогай друг другу.</p><Link to="/forum">Перейти на форум ↗</Link></div>
        <div><span>03 / ВКЛАД</span><strong>Общий архив</strong><p>Загружай свои наработки и делись опытом.</p><Link to="/upload">Добавить материал ↗</Link></div>
      </section>
    </div>
  );
}
