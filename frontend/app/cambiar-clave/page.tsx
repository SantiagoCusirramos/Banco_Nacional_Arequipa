"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { mensajeError } from "@/lib/api";
import { cambiarClave, cerrarSesion, obtenerMiPerfil, obtenerToken, type Usuario } from "@/lib/auth";

const LARGO_MINIMO = 8;

// Cambio de contraseña. Obligatorio con la contraseña inicial o una renovada por un
// administrador: COREDB no deja hacer nada más hasta cambiarla (403 CAMBIO_CLAVE_OBLIGATORIO).
export default function CambiarClavePage() {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetir, setRepetir] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (!obtenerToken()) {
      router.replace("/login");
      return;
    }
    obtenerMiPerfil().then(setUsuario).catch(() => {
      cerrarSesion();
      router.replace("/login");
    });
  }, [router]);

  async function guardar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (nueva !== repetir) {
      setError("Las dos contraseñas nuevas no coinciden.");
      return;
    }
    if (nueva.length < LARGO_MINIMO) {
      setError(`La contraseña nueva debe tener al menos ${LARGO_MINIMO} caracteres.`);
      return;
    }
    if (nueva === actual) {
      setError("La contraseña nueva debe ser distinta de la actual.");
      return;
    }
    setCargando(true);
    try {
      await cambiarClave(actual, nueva);
      router.replace("/");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setCargando(false);
    }
  }

  const obligatoria = usuario?.debe_cambiar_clave !== false;
  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-mark">B</div>
          <div><strong>BNA</strong><span>Banco Nacional de Arequipa</span></div>
        </div>
        <div className="auth-heading">
          <span className="auth-eyebrow">{usuario ? usuario.username : "TU CUENTA"}</span>
          <h1>Cambia tu contraseña</h1>
          <p>{obligatoria
            ? "Estás usando una contraseña temporal que te dio un administrador. Elige una propia para continuar; nadie más la conocerá."
            : "Elige una contraseña nueva. La actual dejará de servir."}</p>
        </div>

        {error && <div className="auth-alert auth-error" role="alert">{error}</div>}

        <form className="auth-form" onSubmit={guardar}>
          <label htmlFor="actual">Contraseña actual</label>
          <input id="actual" type="password" value={actual} onChange={(e) => setActual(e.target.value)} required maxLength={128} autoComplete="current-password" />
          <label htmlFor="nueva">Contraseña nueva</label>
          <input id="nueva" type="password" value={nueva} onChange={(e) => setNueva(e.target.value)} required maxLength={128} autoComplete="new-password" placeholder={`Al menos ${LARGO_MINIMO} caracteres`} />
          <label htmlFor="repetir">Repite la contraseña nueva</label>
          <input id="repetir" type="password" value={repetir} onChange={(e) => setRepetir(e.target.value)} required maxLength={128} autoComplete="new-password" />
          <button className="auth-submit" type="submit" disabled={cargando || !usuario}>
            {cargando ? "Guardando..." : "Guardar contraseña"}
            <span>→</span>
          </button>
        </form>

        <div className="auth-bottom">
          {!obligatoria && <Link href="/">Volver al portal</Link>}
          <Link href="/login" onClick={cerrarSesion}>Cerrar sesión</Link>
        </div>
      </section>
      <aside className="auth-aside">
        <div className="auth-aside-content">
          <span className="auth-aside-kicker">BANCO NACIONAL DE AREQUIPA</span>
          <h2>Tu contraseña es solo tuya.</h2>
          <p>El banco nunca te la pedirá por teléfono ni por correo.</p>
        </div>
      </aside>
    </main>
  );
}
