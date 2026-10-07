"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Messages() {
  const { user, ready } = useAuth();
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(null);
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  const loadList = useCallback(() => api("/conversations").then(setList).catch((e) => setError(e.message)), []);
  useEffect(() => { if (user) loadList(); }, [user, loadList]);

  async function show(id) {
    setOpen(await api("/conversations/" + id));
    loadList();
  }
  async function send(e) {
    e.preventDefault();
    try { await api(`/conversations/${open.id}/messages`, { method: "POST", body: { content: text } }); setText(""); show(open.id); }
    catch (err) { setError(err.message); }
  }

  if (!ready) return null;
  if (!user) return <p><Link href="/login">Войдите</Link>, чтобы увидеть сообщения.</p>;
  return (
    <>
      <h1>Сообщения</h1>
      {error && <p className="error">{error}</p>}
      {list.length === 0 && <p>Диалогов пока нет. Напишите продавцу со страницы произведения.</p>}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(220px,1fr) 2fr", gap: 20 }}>
        <div>
          {list.map((c) => (
            <div key={c.id} className="box" style={{ cursor: "pointer", padding: 10 }} onClick={() => show(c.id)}>
              <b>{c.artwork.title}</b> {c.unread_count > 0 && <span className="tag reserved">{c.unread_count} нов.</span>}
              <div className="muted">{user.id === c.buyer.id ? c.seller.full_name : c.buyer.full_name}</div>
              <div className="muted">{c.last_message?.content.slice(0, 50)}</div>
            </div>
          ))}
        </div>
        {open && (
          <div className="box">
            <b>{open.artwork.title}</b>
            <div style={{ margin: "10px 0" }}>
              {open.messages.map((m) => <div key={m.id} className={"msg" + (m.sender_id === user.id ? " me" : "")}>{m.content}</div>)}
            </div>
            <form onSubmit={send} style={{ display: "flex", gap: 8 }}>
              <input style={{ flex: 1 }} required maxLength="2000" value={text} onChange={(e) => setText(e.target.value)} placeholder="Сообщение" />
              <button>Отправить</button>
            </form>
          </div>
        )}
      </div>
    </>
  );
}
