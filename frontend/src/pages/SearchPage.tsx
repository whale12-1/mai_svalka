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
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>Студенческий хаб</h1>
      <form onSubmit={run} style={{ display: "flex", gap: 8 }}>
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Найти лабораторную, билет, отчёт…"
               style={{ flex: 1, padding: 12, fontSize: 16, border: "1px solid #ccc", borderRadius: 6 }} />
        <button type="submit" disabled={loading} style={{ padding: "12px 24px", fontSize: 16 }}>Найти</button>
      </form>
      <ul style={{ listStyle: "none", padding: 0, marginTop: 24 }}>
        {items.map((m: any) => (
          <li key={m.id} style={{ padding: "12px 0", borderBottom: "1px solid #eee" }}>
            <Link to={`/m/${m.id}`} style={{ fontSize: 18 }}>{m.title}</Link>
            <div style={{ color: "#666", fontSize: 13 }}>
              {m.discipline} · {m.type} · score: {m.score}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}