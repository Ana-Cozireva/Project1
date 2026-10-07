"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Page() {
  const { login, register } = useAuth();
  const router = useRouter();
  const isLogin = "register" === "login";
  const [f, setF] = useState({ email: "", password: "", full_name: "", role: "buyer" });
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      if (isLogin) await login(f.email, f.password);
      else await register(f);
      router.push("/");
    } catch (err) { setError(err.message); }
  }

  return (
    <>
      <h1>Регистрация</h1>
      <form className="form" onSubmit={submit}>
        {!isLogin && <input placeholder="Имя" value={f.full_name} onChange={set("full_name")} />}
        <input type="email" required placeholder="Email" value={f.email} onChange={set("email")} />
        <input type="password" required minLength={isLogin ? 1 : 8} placeholder={isLogin ? "Пароль" : "Пароль (от 8 символов)"} value={f.password} onChange={set("password")} />
        {!isLogin && (
          <select value={f.role} onChange={set("role")}>
            <option value="buyer">Я покупатель</option>
            <option value="seller">Я продавец (галерея / художник)</option>
          </select>
        )}
        {error && <div className="error">{error}</div>}
        <button>Регистрация</button>
        <Link href={isLogin ? "/register" : "/login"} className="muted">{isLogin ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}</Link>
        {isLogin && <p className="muted">Демо: buyer@artgallery.md / buyer12345, gallery@artgallery.md / seller12345, admin@artgallery.md / admin12345</p>}
      </form>
    </>
  );
}
