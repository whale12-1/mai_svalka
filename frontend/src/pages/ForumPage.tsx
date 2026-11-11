import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getThreads } from "../api";

const CATEGORIES = [
  { id: "free", label: "Свободное общение", short: "ОБЩЕНИЕ", icon: "✳", code: "01", color: "cyan", description: "Обсуждения обо всём" },
  { id: "teachers", label: "Преподаватели", short: "ПРЕПОДАВАТЕЛИ", icon: "⌁", code: "02", color: "violet", description: "Вопросы и отзывы" },
  { id: "solutions", label: "Разбор решений", short: "РАЗБОР РЕШЕНИЙ", icon: "⌘", code: "03", color: "orange", description: "Задачи вместе" },
  { id: "specific_people", label: "Конкретные люди", short: "ЛЮДИ", icon: "◎", code: "04", color: "green", description: "Поиск и обсуждения" },
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

  const active = CATEGORIES.find(c => c.id === activeCategory);

  return (
    <div className="forum-page">
      <div className="forum-heading-row">
        <div>
          <div className="forum-kicker"><span /> STUDENT DUMP / COMMUNITY</div>
          <h1>Форум <span>сообщества</span></h1>
          <p>Выбирай направление и подключайся к обсуждению.</p>
        </div>
        <Link to="/forum/new" className="forum-create-button"><span>＋</span> Создать тему</Link>
      </div>

      <section className="forum-categories" aria-label="Разделы форума">
        {CATEGORIES.map(c => (
          <button
            key={c.id}
            type="button"
            onClick={() => setActiveCategory(c.id)}
            aria-pressed={activeCategory === c.id}
            className={`forum-category-tile tile-${c.color}${activeCategory === c.id ? " is-active" : ""}`}
          >
            <span className="tile-topline"><span>РАЗДЕЛ / {c.code}</span><span className="tile-indicator" /></span>
            <span className="tile-icon" aria-hidden="true">{c.icon}</span>
            <span className="tile-title">{c.label}</span>
            <span className="tile-description">{c.description}</span>
            <span className="tile-arrow" aria-hidden="true">↗</span>
          </button>
        ))}
      </section>

      <section className="forum-topics">
        <div className="forum-topics-heading">
          <div>
            <div className="forum-kicker">АКТИВНЫЙ РАЗДЕЛ / {active?.code}</div>
            <h2>{active?.label}</h2>
          </div>
          <span className="forum-topic-count">{loading ? "ЗАГРУЗКА…" : `${threads.length} ТЕМ`}</span>
        </div>

        {loading ? (
          <div className="forum-empty-state">Загружаем обсуждения…</div>
        ) : threads.length === 0 ? (
          <div className="forum-empty-state">
            <span className="empty-state-symbol">＋</span>
            <strong>Пока здесь тихо</strong>
            <span>В этом разделе ещё нет тем. Создай первую и начни обсуждение.</span>
            <Link to="/forum/new">Создать первую тему <span>↗</span></Link>
          </div>
        ) : (
          <div className="forum-thread-list">
            {threads.map(t => (
              <Link key={t.id} to={`/forum/${t.id}`} className="forum-thread-card">
                <span className="thread-mark">↗</span>
                <span className="thread-content">
                  <strong>{t.title}</strong>
                  <span>Создано: {new Date(t.created_at).toLocaleDateString("ru-RU")}</span>
                </span>
                <span className="thread-replies">{t.posts?.length || 0} ответов</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
