"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Card from "@/components/Card";

const EMPTY = { q: "", artist_id: "", style_id: "", technique_id: "", city_id: "", price_min: "", price_max: "", sort: "newest" };

export default function Catalog() {
  const [f, setF] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const [refs, setRefs] = useState({ artists: [], styles: [], techniques: [], cities: [] });
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all(["artists", "styles", "techniques", "cities"].map((k) => api("/" + k)))
      .then(([artists, styles, techniques, cities]) => setRefs({ artists, styles, techniques, cities }))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams({ page, page_size: 12 });
    Object.entries(f).forEach(([k, v]) => v && params.set(k, v));
    const t = setTimeout(() => api("/artworks?" + params).then(setData).catch((e) => setError(e.message)), 250);
    return () => clearTimeout(t);
  }, [f, page]);

  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setPage(1); };
  const select = (k, label, list) => (
    <select value={f[k]} onChange={set(k)}>
      <option value="">{label}</option>
      {list.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
    </select>
  );

  return (
    <>
      <div className="catalog-header">
        <h1 className="catalog-title">Каталог</h1>
      </div>
      <div className="filters">
        <input placeholder="Поиск по названию или художнику" value={f.q} onChange={set("q")} />
        {select("artist_id", "Все художники", refs.artists)}
        {select("style_id", "Все стили", refs.styles)}
        {select("technique_id", "Все техники", refs.techniques)}
        {select("city_id", "Все города", refs.cities)}
        <input type="number" min="0" placeholder="Цена от" style={{ width: 100 }} value={f.price_min} onChange={set("price_min")} />
        <input type="number" min="0" placeholder="до" style={{ width: 100 }} value={f.price_max} onChange={set("price_max")} />
        <select value={f.sort} onChange={set("sort")}>
          <option value="newest">Сначала новые</option>
          <option value="price_asc">Дешевле</option>
          <option value="price_desc">Дороже</option>
          <option value="title">По названию</option>
        </select>
        <button className="light" onClick={() => { setF(EMPTY); setPage(1); }}>Сбросить</button>
      </div>
      {error && <p className="error">{error}</p>}
      {data && (data.items.length === 0 ? <p>Ничего не найдено. Измените фильтры.</p> : (
        <div className="grid">{data.items.map((a) => <Card key={a.id} a={a} />)}</div>
      ))}
      {data && data.pages > 1 && (
        <div className="pager">
          <button className="light" disabled={page <= 1} onClick={() => setPage(page - 1)}>Назад</button>
          <span>{page} из {data.pages}</span>
          <button className="light" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Вперёд</button>
        </div>
      )}
    </>
  );
}
