// PIN de la tarjeta (4 dígitos) y de Chaski (6): generados al azar en el navegador con
// crypto.getRandomValues, o escritos por la clienta. Nunca triviales.

/** Todos iguales (0000) o consecutivos subiendo o bajando (1234, 4321, 0123, 654321). */
export function esTrivial(pin: string): boolean {
  if (!/^\d+$/.test(pin)) return true;
  const d = [...pin].map(Number);
  const iguales = d.every((x) => x === d[0]);
  const sube = d.every((x, i) => i === 0 || x === d[i - 1] + 1);
  const baja = d.every((x, i) => i === 0 || x === d[i - 1] - 1);
  return iguales || sube || baja;
}

export function generarPin(digitos: number): string {
  for (;;) {
    const azar = crypto.getRandomValues(new Uint32Array(digitos));
    // 4294967296 % 10 = 6: el sesgo hacia 0–5 es de 1 en 429 millones, despreciable.
    const pin = Array.from(azar, (n) => String(n % 10)).join("");
    if (!esTrivial(pin)) return pin;
  }
}
