"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, money } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function Stats({ title, rows }) {
  return (
    <>
      <h2>{title}</h2>
      <table>
        <thead><tr><th>Название</th><th>Объявлений</th><th>Продано</th><th>Средняя цена</th><th>Сумма продаж</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.name}</td><td>{r.artworks_count}</td><td>{r.sold_count}</td><td>{money(r.avg_price)}</td><td>{money(r.sold_value)}</td></tr>)}</tbody>
      </table>
    </>
  );
}

export default function Admin() {
  const { user, ready } = useAuth();
  const [d, setD] = useState(null);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const isAdmin = user?.role === "admin";

  const load = useCallback(async () => {
    const [overview, artist, style, city, month, u] = await Promise.all([
      api("/analytics/overview"), api("/analytics/by-artist?limit=10"), api("/analytics/by-style"),
      api("/analytics/by-city"), api("/analytics/by-month?months=6"), api("/users?page_size=100"),
    ]);
    setD({ overview, artist, style, city, month });
    setUsers(u.items);
  }, []);
  useEffect(() => { if (isAdmin) load().catch((e) => setError(e.message)); }, [isAdmin, load]);

  async function changeRole(id, role) {
    try { await api(`/users/${id}/role`, { method: "PATCH", body: { role } }); load(); } catch (e) { setError(e.message); }
  }
  async function removeUser(id) {
    if (!confirm("Удалить пользователя вместе с его объявлениями?")) return;
    try { await api("/users/" + id, { method: "DELETE" }); load(); } catch (e) { setError(e.message); }
  }

  if (!ready) return null;
  if (!isAdmin) return <p>Раздел доступен администратору. <Link href="/login">Войти</Link></p>;
  const o = d?.overview;
  return (
    <>
      <h1>Аналитика</h1>
      {error && <p className="error">{error}</p>}
      {o && (
        <div className="stats">
          <div><b>{o.users_total}</b>пользователей</div>
          <div><b>{o.artworks_total}</b>объявлений</div>
          <div><b>{o.artworks_by_status.sold}</b>продано</div>
          <div><b>{o.reservations_by_status.pending}</b>броней ожидают</div>
          <div><b>{money(o.sold_value)}</b>сумма продаж</div>
        </div>
      )}
      {d && <>
        <Stats title="По художникам (топ-10)" rows={d.artist} />
        <Stats title="По стилям" rows={d.style} />
        <Stats title="По городам" rows={d.city} />
        <h2>По месяцам</h2>
        <table>
          <thead><tr><th>Месяц</th><th>Размещено</th><th>Броней</th><th>Продано</th><th>Сумма</th></tr></thead>
          <tbody>{d.month.map((m) => <tr key={m.month}><td>{m.month}</td><td>{m.listed_count}</td><td>{m.reservations_count}</td><td>{m.sold_count}</td><td>{money(m.sold_value)}</td></tr>)}</tbody>
        </table>
      </>}
      <h2>Пользователи</h2>
      <table>
        <thead><tr><th>Email</th><th>Роль</th><th></th></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>
                <select value={u.role} disabled={u.id === user.id} onChange={(e) => changeRole(u.id, e.target.value)}>
                  <option value="buyer">buyer</option><option value="seller">seller</option><option value="admin">admin</option>
                </select>
              </td>
              <td>{u.id !== user.id && <button className="light" onClick={() => removeUser(u.id)}>Удалить</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
