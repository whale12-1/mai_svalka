export async function search(q: string, params: Record<string, string | number | undefined> = {}) {
  const usp = new URLSearchParams({ q, ...Object.fromEntries(Object.entries(params).filter(([,v]) => v != null && v !== "").map(([k,v]) => [k, String(v)])) });
  const r = await fetch(`/api/search?${usp}`, { credentials: "include" });
  return r.json();
}
export async function getMaterial(id: number) {
  const r = await fetch(`/api/materials/${id}`, { credentials: "include" });
  return r.json();
}