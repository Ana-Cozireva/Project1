"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Card from "@/components/Card";

export default function Favorites() {
  const { user, ready } = useAuth();
  const [items, setItems] = useState(null);
  useEffect(() => { if (user) api("/favorites").then(setItems); }, [user]);
  if (!ready) return null;
  if (!user) return <p><Link href="/login">Войдите</Link>, чтобы увидеть избранное.</p>;
  return (
    <>
      <h1>Избранное</h1>
      {items && items.length === 0 && <p>Пока пусто. Нажмите «☆ В избранное» на странице произведения.</p>}
      <div className="grid">{items?.map((f) => <Card key={f.artwork.id} a={f.artwork} />)}</div>
    </>
  );
}
