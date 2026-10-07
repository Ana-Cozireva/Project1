import Link from "next/link";
import { img, money, STATUS } from "@/lib/api";

export default function Card({ a }) {
  return (
    <Link href={`/artwork/${a.id}`} className="card">
      <div className="thumb">{a.cover_url ? <img src={img(a.cover_url)} alt={a.title} /> : <span>нет фото</span>}</div>
      <div className="info">
        <b>{a.title}</b>
        <div>{a.artist.name}{a.year_created ? `, ${a.year_created}` : ""}</div>
        <div className="muted">{[a.technique?.name, a.city?.name].filter(Boolean).join(" · ")}</div>
        <div className="row">
          <span className="price">{money(a.price)}</span>
          <span className={`tag ${a.status}`}>{STATUS[a.status]}</span>
        </div>
      </div>
    </Link>
  );
}
