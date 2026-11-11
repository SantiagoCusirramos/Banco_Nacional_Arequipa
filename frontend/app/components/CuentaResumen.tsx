import { formatoMoneda, type Cuenta } from "@/lib/cuentas";

const claseEstado: Record<string, string> = {
  ACTIVA: "",
  BLOQUEADA: "pill-danger",
  BLOQUEADA_PREVENTIVA: "pill-warn",
  CANCELADA: "pill-muted",
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
      <div className="detail-row"><span>CCI</span><strong className="mono">{cuenta.cci}</strong></div>
      <div className="detail-row"><span>Agencia</span><strong className="mono">{cuenta.id_agencia ?? "—"}</strong></div>
      <div className="detail-row detail-titulares">
        <span>Titulares</span>
        <ul>
          {cuenta.titulares.map((codigo) => (
            <li key={codigo}><strong className="mono">{codigo}</strong></li>
          ))}
        </ul>
      </div>
    </article>
  );
}
