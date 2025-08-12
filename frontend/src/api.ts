export const API_BASE = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
export async function fetchTopics() {
  const res = await fetch(`${API_BASE}/topics`);
  return res.json();
}