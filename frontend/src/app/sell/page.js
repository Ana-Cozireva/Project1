"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, CONDITION } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function Sell() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const [refs, setRefs] = useState({ artists: [], styles: [], techniques: [], cities: [] });
  const [f, setF] = useState({ title: "", artist_id: "", new_artist: "", style_id: "", technique_id: "", city_id: "", year_created: "", price: "", condition: "", width_cm: "", height_cm: "", description: "" });
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  useEffect(() => {
    Promise.all(["artists", "styles", "techniques", "cities"].map((k) => api("/" + k)))
      .then(([artists, styles, techniques, cities]) => setRefs({ artists, styles, techniques, cities }));
  }, []);

  async function submit(e) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      let artistId = f.artist_id;
      if (f.new_artist.trim()) artistId = (await api("/artists", { method: "POST", body: { name: f.new_artist } })).id;
      if (!artistId) throw new Error("Выберите художника или введите нового");
      const num = (v) => (v === "" ? null : Number(v));
      const art = await api("/artworks", {
        method: "POST",
        body: {
          title: f.title, artist_id: Number(artistId), price: f.price,
          style_id: num(f.style_id), technique_id: num(f.technique_id), city_id: num(f.city_id),
          year_created: num(f.year_created), condition: f.condition || null,
          details: { width_cm: num(f.width_cm), height_cm: num(f.height_cm), description: f.description || null },
        },
      });
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        await api(`/artworks/${art.id}/photos`, { method: "POST", form });
      }
      router.push("/artwork/" + art.id);
    } catch (err) { setError(err.message); setBusy(false); }
  }

  if (!ready) return null;
  if (!user || user.role === "buyer") return <p>Размещать объявления могут продавцы. <Link href="/register">Зарегистрируйтесь как продавец</Link>.</p>;

  const sel = (k, label, list) => (
    <select value={f[k]} onChange={set(k)}><option value="">{label}</option>{list.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}</select>
  );
  return (
    <>
      <h1>Новое объявление</h1>
      <form className="form" onSubmit={submit}>
        <input required placeholder="Название" maxLength="200" value={f.title} onChange={set("title")} />
        {sel("artist_id", "Художник…", refs.artists)}
        <input placeholder="…или новый художник" value={f.new_artist} onChange={set("new_artist")} />
        {sel("style_id", "Стиль", refs.styles)}
        {sel("technique_id", "Техника", refs.techniques)}
        {sel("city_id", "Город", refs.cities)}
        <input type="number" placeholder="Год создания" value={f.year_created} onChange={set("year_created")} />
        <input type="number" required min="1" step="0.01" placeholder="Цена, €" value={f.price} onChange={set("price")} />
        <select value={f.condition} onChange={set("condition")}>
          <option value="">Состояние</option>
          {Object.entries(CONDITION).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <div style={{ display: "flex", gap: 8 }}>
          <input type="number" step="0.1" placeholder="Ширина, см" value={f.width_cm} onChange={set("width_cm")} style={{ flex: 1 }} />
          <input type="number" step="0.1" placeholder="Высота, см" value={f.height_cm} onChange={set("height_cm")} style={{ flex: 1 }} />
        </div>
        <textarea rows="4" maxLength="4000" placeholder="Описание" value={f.description} onChange={set("description")} />
        <label>Фотографии (JPEG, PNG, WEBP до 5 МБ)<br /><input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={(e) => setFiles([...e.target.files])} /></label>
        {error && <div className="error">{error}</div>}
        <button disabled={busy}>{busy ? "Сохранение…" : "Опубликовать"}</button>
      </form>
    </>
  );
}
