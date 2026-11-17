import type { Metadata } from "next";
import "./desembolso.css";
import { ConSesion } from "./_componentes/ConSesion";

export const metadata: Metadata = {
  title: "Desembolso de Créditos · BNA",
  description: "Módulo 13 Desembolso de la Línea de Créditos: preparación, validación, confirmación y seguimiento.",
};

export default function DesembolsoLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="desembolso min-h-screen bg-slate-100 text-slate-800 antialiased" lang="es-PE">
      <ConSesion>{children}</ConSesion>
    </div>
  );
}
