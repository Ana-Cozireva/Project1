"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("token")) return setReady(true);
    api("/auth/me")
      .then(setUser)
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setReady(true));
  }, []);

  async function enter(path, body) {
    const data = await api(path, { method: "POST", body });
    localStorage.setItem("token", data.access_token);
    setUser(data.user);
  }
  const login = (email, password) => enter("/auth/login", { email, password });
  const register = (body) => enter("/auth/register", body);
  const logout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return <Ctx.Provider value={{ user, ready, login, register, logout }}>{children}</Ctx.Provider>;
}
