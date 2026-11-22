import type { Metadata } from "next";
import "./globals.css";
import VigilanteSesion from "./components/VigilanteSesion";

export const metadata: Metadata = {
  title: "Banco Nacional de Arequipa | Banca personal",
  description: "Portal de banca personal del Banco Nacional de Arequipa. Proyecto académico.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <VigilanteSesion />
        {children}
      </body>
    </html>
  );
}
