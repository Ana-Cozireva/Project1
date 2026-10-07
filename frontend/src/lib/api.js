export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const img = (url) => (url ? (url.startsWith("http") ? url : API + url) : null);
export const money = (v) => Number(v).toLocaleString("ru-RU") + " €";
export const STATUS = { available: "В продаже", reserved: "Забронировано", sold: "Продано" };
export const RES_STATUS = { pending: "Ожидает", confirmed: "Подтверждено", cancelled: "Отменено" };
export const CONDITION = { excellent: "Отличное", good: "Хорошее", fair: "Удовлетворительное", restored: "Реставрация" };

export async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) headers.Authorization = "Bearer " + token;
  let payload;
  if (form) payload = form;
  else if (body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(API + "/api" + path, { method, headers, body: payload });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const d = data && data.detail;
    throw new Error(
      typeof d === "string" ? d : Array.isArray(d) ? d.map((e) => e.msg).join("; ") : "Ошибка " + res.status
    );
  }
  return data;
}
