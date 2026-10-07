import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import Header from "@/components/Header";

export const metadata = { title: "ArtGallery", description: "Покупка и продажа предметов искусства" };

export default function RootLayout({ children }) {
  return (
    <html lang="ru">
      <body>
        <AuthProvider>
          <Header />
          <main className="main">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
