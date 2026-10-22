import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getMaterial } from "../api";

export default function MaterialPage() {
  const { id } = useParams();
  const [m, setM] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      getMaterial(Number(id))
        .then(setM)
        .catch((err) => {
          console.error(err);
          setError("Не удалось загрузить материал. Возможно, бэкенд упал.");
        });
    }
  }, [id]);

  if (error) return <div style={{ padding: 40, color: 'red' }}>{error}</div>;
  if (!m) return <div style={{ padding: 40 }}>Загрузка…</div>;

  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>{m.title}</h1>
      <p style={{ color: "#666" }}>{m.discipline} · {m.type} · {m.teacher}</p>
      <p>{m.description}</p>
      <h3>Файлы</h3>
      <ul>
        {m.files.map((f: any) => (
          <li key={f.id}>
            <a href={f.url} target="_blank" rel="noopener noreferrer">{f.filename}</a> ({f.size} B)
          </li>
        ))}
      </ul>
    </div>
  );
}