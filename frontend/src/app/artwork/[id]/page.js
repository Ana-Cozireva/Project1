"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, img, money, STATUS, CONDITION } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ArtworkPage() {
  const { id } = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const [a, setA] = useState(null);
  const [photo, setPhoto] = useState(0);
  const [text, setText] = useState("");
  const [msg, setMsg] = useState({ type: "", text: "" });

  const load = useCallback(() => api("/artworks/" + id).then(setA).catch((e) => setMsg({ type: "error", text: e.message })), [id]);
  useEffect(() => { load(); }, [load, user]);

  async function run(fn, okText) {
    if (!user) return router.push("/login");
    try { await fn(); setMsg({ type: "ok", text: okText }); await load(); }
    catch (e) { setMsg({ type: "error", text: e.message }); }
  }

  if (!a) return <p className={msg.type}>{msg.text || "Загрузка…"}</p>;
  const d = a.details || {};
  const size = [d.width_cm, d.height_cm, d.depth_cm].filter(Boolean).map(Number).join(" × ");
  const mine = user && user.id === a.seller_id;

  return (
    <div className="detail">
      <div>
        {a.photos.length ? <img className="main-img" src={img(a.photos[photo]?.url)} alt={a.title} /> : <div className="thumb" style={{ aspectRatio: "4/3" }}>нет фото</div>}
        <div className="thumbs">
          {a.photos.map((p, i) => <img key={p.id} src={img(p.url)} alt="" className={i === photo ? "on" : ""} onClick={() => setPhoto(i)} />)}
        </div>
      </div>
      <div>
        <h1 style={{ marginTop: 0 }}>{a.title}</h1>
        <p><b>{a.artist.name}</b>{a.year_created ? `, ${a.year_created}` : ""}</p>
        <p className="price" style={{ fontSize: 26 }}>{money(a.price)} <span className={`tag ${a.status}`}>{STATUS[a.status]}</span></p>
        <table><tbody>
          {a.style && <tr><th>Стиль</th><td>{a.style.name}</td></tr>}
          {a.technique && <tr><th>Техника</th><td>{a.technique.name}</td></tr>}
          {size && <tr><th>Размер, см</th><td>{size}</td></tr>}
          {a.condition && <tr><th>Состояние</th><td>{CONDITION[a.condition]}</td></tr>}
          {a.city && <tr><th>Город</th><td>{a.city.name}</td></tr>}
          <tr><th>Продавец</th><td>{a.seller?.full_name}</td></tr>
        </tbody></table>
        {d.description && <p>{d.description}</p>}

        {!mine && (
          <p style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="light" onClick={() => run(() => api("/favorites/" + a.id, { method: a.is_favorite ? "DELETE" : "PUT" }), a.is_favorite ? "Убрано из избранного" : "Добавлено в избранное")}>
              {a.is_favorite ? "★ В избранном" : "☆ В избранное"}
            </button>
            <button disabled={a.status !== "available"} onClick={() => run(() => api("/reservations", { method: "POST", body: { artwork_id: a.id } }), "Произведение забронировано. Ждите подтверждения продавца.")}>
              Забронировать
            </button>
          </p>
        )}
        {!mine && (
          <div className="box">
            <b>Написать продавцу</b>
            <div className="form" style={{ marginTop: 8 }}>
              <textarea rows="3" maxLength="2000" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ваш вопрос" />
              <button disabled={!text.trim()} onClick={() => run(async () => { await api("/conversations", { method: "POST", body: { artwork_id: a.id, content: text } }); setText(""); }, "Сообщение отправлено")}>Отправить</button>
            </div>
          </div>
        )}
        {msg.text && <p className={msg.type}>{msg.text}</p>}
      </div>
    </div>
  );
}
