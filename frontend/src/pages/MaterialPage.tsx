import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getMaterial } from "../api";

export default function MaterialPage() {
  const { id } = useParams();
  const [m, setM] = useState<any>(null);
  useEffect(() => { if (id) getMaterial(Number(id)).then(setM); }, [id]);
  if (!m) return <div style={{ padding: 40 }}>Загрузка…</div>;
  return (
    <div style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>{m.title}</h1>
      <p style={{ color: "#666" }}>{m.discipline} · {m.type} · {m.teacher}</p>
      <p>{m.description}</p>
      <h3>Файлы</h3>
      <ul>{m.files.map((f: any) => <li key={f.id}><a href={f.url}>{f.filename}</a> ({f.size} B)</li>)}</ul>
    </div>
  );
}