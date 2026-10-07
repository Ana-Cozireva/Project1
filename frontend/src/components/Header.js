"use client";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Header() {
  const { user, logout } = useAuth();
  return (
    <header className="header">
      <Link href="/" className="logo">ArtGallery</Link>
      <nav>
        <Link href="/">Каталог</Link>
        {user ? (
          <>
            <Link href="/favorites">Избранное</Link>
            <Link href="/messages">Сообщения</Link>
            <Link href="/my">{user.role === "buyer" ? "Мои брони" : "Брони и объявления"}</Link>
            {user.role !== "buyer" && <Link href="/sell">Добавить</Link>}
            {user.role === "admin" && <Link href="/admin">Админ</Link>}
            <button className="light" onClick={logout}>Выйти</button>
          </>
        ) : (
          <>
            <Link href="/login">Войти</Link>
            <Link href="/register">Регистрация</Link>
          </>
        )}
      </nav>
    </header>
  );
}
