import type { Metadata } from "next";
import "./sol.css";

export const metadata: Metadata = {
  title: "Solicitud de Crédito · BNA",
  description:
    "Prototipo académico de Solicitud de Crédito del Banco Nacional de Arequipa.",
};

export default function SolLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sol" lang="es">
      {children}
    </div>
  );
}
