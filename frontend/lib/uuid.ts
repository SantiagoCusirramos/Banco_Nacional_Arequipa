/**
 * UUID v4 para llaves de idempotencia y referencias.
 *
 * `crypto.randomUUID()` solo existe en contextos seguros (HTTPS o localhost). Cuando el producto
 * se abre desde otra máquina de la red (http://IP-del-servidor:3000) no está, y las páginas que lo
 * llaman fallarían. `crypto.getRandomValues()` sí está en cualquier contexto.
 */
export function nuevoUuid(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
