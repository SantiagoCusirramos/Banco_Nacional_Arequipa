import { formatoFecha, formatoMoneda, type Cuenta } from "@/lib/cuentas";

const claseEstado: Record<string, string> = {
  ACTIVA: "",
  INACTIVA: "pill-muted",
  BLOQUEADA: "pill-danger",
  EMBARGO: "pill-warn",
};

export function EstadoPill({ estado }: { estado: string }) {
  return (
    <span className={`status-pill ${claseEstado[estado] ?? "pill-muted"}`}>
      <i /> {estado}
    </span>
  );
}

export function CuentaResumen({ cuenta, titulo }: { cuenta: Cuenta; titulo?: string }) {
  return (
    <article className="account-card" aria-label={`Cuenta ${cuenta.num_cuenta}`}>
      <div className="account-card-top">
        <span className="product-icon">▤</span>
        <EstadoPill estado={cuenta.estado_cuenta} />
      </div>
      <p className="mini-label">CUENTA DE AHORROS · {cuenta.moneda} · {cuenta.regimen}</p>
      <h2>{titulo ?? "Detalle de la cuenta"}</h2>
      <p className="account-number">{cuenta.num_cuenta}</p>
      <div className="account-balance-label">Saldo disponible</div>
      <div className="account-balance">{formatoMoneda(cuenta.saldo_disponible, cuenta.moneda)}</div>
      <div className="detail-row"><span>Saldo contable</span><strong>{formatoMoneda(cuenta.saldo_contable, cuenta.moneda)}</strong></div>
      <div className="detail-row"><span>Saldo retenido</span><strong>{formatoMoneda(cuenta.saldo_retenido, cuenta.moneda)}</strong></div>
      <div className="detail-row"><span>Fecha de apertura</span><strong>{formatoFecha(cuenta.fecha_apertura)}</strong></div>
      <div className="detail-row"><span>Producto</span><strong className="mono">{cuenta.id_producto_ahorro}</strong></div>
      <div className="detail-row"><span>Agencia</span><strong className="mono">{cuenta.id_agencia}</strong></div>
      <div className="detail-row detail-titulares">
        <span>Titulares</span>
        <ul>
          {cuenta.titulares.map((t) => (
            <li key={t.id_cliente}><strong className="mono">{t.id_cliente}</strong> <small>{t.rol_titular}</small></li>
          ))}
        </ul>
      </div>
    </article>
  );
}
