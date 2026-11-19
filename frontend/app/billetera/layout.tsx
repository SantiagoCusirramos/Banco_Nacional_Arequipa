import type { Metadata } from "next";
import "../solicitud-credito/sol.css";

export const metadata: Metadata = {
  title: "Billetera Chaski · BNA",
  description: "Afiliación de clientes y comercios a la billetera digital Chaski, sobre COREDB.",
};

export default function BilleteraLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sol" lang="es">
      {children}
    </div>
  );
}
