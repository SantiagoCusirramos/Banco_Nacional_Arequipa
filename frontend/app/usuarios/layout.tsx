import type { Metadata } from "next";
import "../solicitud-credito/sol.css";
import "../tarjetas/tarjetas.css";

export const metadata: Metadata = {
  title: "Usuarios · BNA",
  description: "Usuarios del personal del Banco Nacional de Arequipa: altas, roles y contraseñas.",
};

export default function UsuariosLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sol" lang="es">
      {children}
    </div>
  );
}
