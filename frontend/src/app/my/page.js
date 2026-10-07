"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, money, RES_STATUS } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function Reservations({ title, items, onAction, canConfirm }) {
  return (
    <>
      <h2>{title}</h2>
      {items.length === 0 ? <p className="muted">Нет записей</p> : (
        <table>
          <thead><tr><th>Произведение</th><th>{canConfirm ? "Покупатель" : "Продавец"}</th><th>Цена</th><th>Статус</th><th></th></tr></thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.id}>
                <td><Link href={`/artwork/${r.artwork.id}`}><u>{r.artwork.title}</u></Link></td>
                <td>{canConfirm ? r.buyer.full_name : r.seller.full_name}</td>
                <td>{money(r.artwork.price)}</td>
                <td>{RES_STATUS[r.status]}</td>
                <td style={{ display: "flex", gap: 6 }}>
                  {r.status === "pending" && canConfirm && <button onClick={() => onAction(r.id, "confirm")}>Подтвердить</button>}
                  {r.status === "pending" && <button className="light" onClick={() => onAction(r.id, "cancel")}>Отменить</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

export default function My() {
  const { user, ready } = useAuth();
  const [mine, setMine] = useState([]);
  const [incoming, setIncoming] = useState([]);
  const [artworks, setArtworks] = useState([]);
  const [error, setError] = useState("");
  const isSeller = user && user.role !== "buyer";

  const load = useCallback(async () => {
    setMine((await api("/reservations?as=buyer")).items);
    if (isSeller) {
      setIncoming((await api("/reservations?as=seller")).items);
      setArtworks((await api("/artworks/mine")).items);
    }
  }, [isSeller]);
  useEffect(() => { if (user) load().catch((e) => setError(e.message)); }, [user, load]);

  async function act(id, what) {
    try { await api(`/reservations/${id}/${what}`, { method: "POST" }); await load(); setError(""); }
    catch (e) { setError(e.message); }
  }
  async function remove(id) {
    if (!confirm("Удалить объявление?")) return;
    try { await api("/artworks/" + id, { method: "DELETE" }); await load(); setError(""); }
    catch (e) { setError(e.message); }
  }

  if (!ready) return null;
  if (!user) return <p><Link href="/login">Войдите</Link>, чтобы продолжить.</p>;
  return (
    <>
      {error && <p className="error">{error}</p>}
      <Reservations title="Мои брони" items={mine} onAction={act} />
      {isSeller && (
        <>
          <Reservations title="Брони на мои произведения" items={incoming} onAction={act} canConfirm />
          <h2>Мои объявления</h2>
          <p><Link href="/sell" className="btn">+ Добавить объявление</Link></p>
          <table>
            <thead><tr><th>Название</th><th>Цена</th><th>Статус</th><th></th></tr></thead>
            <tbody>
              {artworks.map((a) => (
                <tr key={a.id}>
                  <td><Link href={`/artwork/${a.id}`}><u>{a.title}</u></Link></td>
                  <td>{money(a.price)}</td><td>{a.status}</td>
                  <td><button className="light" onClick={() => remove(a.id)}>Удалить</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </>
  );
}
