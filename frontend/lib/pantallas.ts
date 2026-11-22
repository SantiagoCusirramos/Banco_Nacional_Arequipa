import type { Usuario } from "@/lib/auth";

export type Pantalla = {
  href: string;
  label: string;
  icon: string;
  descripcion: string;
  /** Al menos uno de estos permisos habilita la pantalla (según COREDB/permisos.py y routers). */
  permisos: string[];
  /** Texto breve para el aviso cuando el rol no tiene permiso. */
  rolesPermitidos: string;
};

export const PANTALLAS: Pantalla[] = [
  {
    href: "/cuenta",
    label: "Cuentas",
    icon: "▤",
    descripcion: "Abrir y consultar cuentas, depósitos, retiros, transferencias y movimientos",
    permisos: ["VER_CUENTA", "CREAR_CUENTA", "MODIFICAR_CUENTA", "REGISTRAR_MOVIMIENTO"],
    rolesPermitidos: "operadores, administradores, analistas, auditores y asesores con acceso a cuentas",
  },
  {
    href: "/tarjetas",
    label: "Tarjetas",
    icon: "▭",
    descripcion: "Emitir, activar, bloquear tarjetas y autorizar débitos",
    permisos: ["VER_TARJETA", "CREAR_TARJETA", "BLOQUEAR_TARJETA"],
    rolesPermitidos: "operadores, administradores y auditores con acceso a tarjetas",
  },
  {
    href: "/tarjetas/desbloqueo",
    label: "Desbloqueo de tarjetas",
    icon: "🔓",
    descripcion: "Operadores y administradores: desbloquear una tarjeta tras verificar al titular",
    permisos: ["BLOQUEAR_TARJETA"],
    rolesPermitidos: "operadores y administradores",
  },
  {
    href: "/billetera",
    label: "Billetera Chaski",
    icon: "◎",
    descripcion: "Afiliar clientes y comercios a la billetera digital",
    permisos: ["AFILIAR_BILLETERA", "REGISTRAR_COMERCIO"],
    rolesPermitidos: "asesores, operadores y administradores con acceso a billetera",
  },
  {
    href: "/captacion",
    label: "Captación",
    icon: "📋",
    descripcion: "Registrar solicitantes y habilitarlos como clientes",
    permisos: ["CREAR_CLIENTE", "MODIFICAR_CLIENTE", "VALIDAR_IDENTIDAD"],
    rolesPermitidos: "asesores, operadores y administradores con acceso a captación",
  },
  {
    href: "/solicitud-credito",
    label: "Solicitud de crédito",
    icon: "📝",
    descripcion: "El asesor arma y envía la solicitud (SOL)",
    permisos: ["CREAR_SOLICITUD_CREDITO"],
    rolesPermitidos: "asesores y administradores",
  },
  {
    href: "/evaluacion",
    label: "Evaluación",
    icon: "⚖",
    descripcion: "El analista evalúa y decide las solicitudes",
    permisos: ["EVALUAR_CREDITO", "APROBAR_CREDITO"],
    rolesPermitidos: "analistas y administradores",
  },
  {
    href: "/desembolso",
    label: "Desembolso",
    icon: "⇣",
    descripcion: "Órdenes de desembolso, confirmación y conciliación",
    permisos: ["DESEMBOLSAR_CREDITO", "GENERAR_REPORTES"],
    rolesPermitidos: "operadores, administradores y auditores con acceso a desembolso",
  },
  {
    href: "/pagar-cuota",
    label: "Pagar cuota",
    icon: "⎘",
    descripcion: "Pago de cuotas de un crédito (Cobranza, CR-INT-08)",
    permisos: ["REGISTRAR_PAGO", "CONSULTAR_DEUDA"],
    rolesPermitidos: "operadores, administradores, analistas y auditores con acceso a cobranza",
  },
  {
    href: "/usuarios",
    label: "Usuarios",
    icon: "👤",
    descripcion: "Altas del personal, roles y contraseñas",
    permisos: ["CREAR_USUARIO"],
    rolesPermitidos: "administradores",
  },
  {
    href: "/homebanking/index.html",
    label: "Home Banking",
    icon: "⌂",
    descripcion: "Prototipo de Home Banking sobre las mismas rutas",
    permisos: ["VER_CUENTA", "VER_TARJETA", "CONSULTAR_DEUDA", "VER_AUDITORIA", "REGISTRAR_MOVIMIENTO"],
    rolesPermitidos: "personal con acceso a cuentas, tarjetas, créditos o auditoría",
  },
];

export function puedeVerPantalla(acciones: string[] | undefined | null, href: string): boolean {
  const pantalla = PANTALLAS.find((p) => p.href === href);
  if (!pantalla) return false;
  const set = new Set(acciones ?? []);
  return pantalla.permisos.some((permiso) => set.has(permiso));
}

export function pantallaPorHref(href: string): Pantalla | undefined {
  return PANTALLAS.find((p) => p.href === href);
}

export function pantallasParaUsuario(usuario: Pick<Usuario, "acciones"> | null | undefined): Pantalla[] {
  const acciones = usuario?.acciones ?? [];
  return PANTALLAS.filter((p) => p.permisos.some((permiso) => acciones.includes(permiso)));
}
