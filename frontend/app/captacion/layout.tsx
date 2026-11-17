import type { Metadata } from "next";
import "../solicitud-credito/sol.css";
import "./captacion.css";

export const metadata: Metadata = {
  title: "Captación de clientes · BNA",
  description: "Registro, verificación y habilitación de solicitantes del Banco Nacional de Arequipa, sobre COREDB.",
};

export default function CaptacionLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sol cap" lang="es">
      {children}
    </div>
  );
}
