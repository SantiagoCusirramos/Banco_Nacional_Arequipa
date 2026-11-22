"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { mensajeError } from "@/lib/api";
import { cerrarSesion, obtenerMiPerfil, type Usuario } from "@/lib/auth";
import {
  NOMBRE_ROL, PERMISO_USUARIOS, ROLES, cambiarEstado, cambiarRol, crearUsuario, desbloquearIngreso, listarUsuarios,
  renovarClave, type UsuarioBanco,
} from "@/lib/usuarios";

// Usuarios del personal (hallazgos B1 y B2 de la prueba «solo con el mouse»). La contraseña
// inicial y la renovada las genera COREDB: se muestran una sola vez para entregarlas, y la
// persona debe cambiarlas en su primer ingreso.

type Aviso = { texto: string; error: boolean };
type Entrega = { username: string; nombre: string; clave: string; motivo: "alta" | "renovacion" };

const nombreRol = (rol: string) => NOMBRE_ROL[rol] ?? rol;

function ClaveParaEntregar({ entrega, onListo }: { entrega: Entrega; onListo: () => void }) {
  const [copiada, setCopiada] = useState(false);
  async function copiar() {
    try {
      await navigator.clipboard.writeText(entrega.clave);
      setCopiada(true);
    } catch {
      setCopiada(false);
    }
  }
  return (
    <section className="sol-card" role="region" aria-labelledby="titulo-clave" style={{ marginBottom: "24px", borderColor: "#c9a227" }}>
      <div className="sol-card-title">
        <div>
          <h2 id="titulo-clave">Contraseña inicial de {entrega.username}</h2>
          <p>
            {entrega.motivo === "alta" ? `Usuario creado para ${entrega.nombre}.` : `Contraseña renovada para ${entrega.nombre}; la anterior ya no sirve.`}
            {" "}Entrégasela en persona. Al entrar, el sistema le pedirá cambiarla.
          </p>
        </div>
      </div>
      <p style={{ fontFamily: "monospace", fontSize: "24px", letterSpacing: "2px", margin: "8px 0 16px" }}>{entrega.clave}</p>
      <p role="note"><strong>No se volverá a mostrar.</strong> Si se pierde, usa «Renovar contraseña».</p>
      <div className="sol-actions" style={{ display: "flex", gap: "12px", marginTop: "12px" }}>
        <button type="button" className="sol-button secondary" onClick={copiar}>Copiar</button>
        <button type="button" className="sol-button" onClick={onListo}>Ya la entregué</button>
        {copiada && <span role="status">Copiada.</span>}
      </div>
    </section>
  );
}

export default function UsuariosPage() {
  const [usuario, setUsuario] = useState<Usuario | null | undefined>(undefined);
  const [lista, setLista] = useState<UsuarioBanco[] | null>(null);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [entrega, setEntrega] = useState<Entrega | null>(null);
  const [formulario, setFormulario] = useState(false);
  const [nombre, setNombre] = useState("");
  const [username, setUsername] = useState("");
  const [rol, setRol] = useState<string>("ASESOR");
  const [enviando, setEnviando] = useState(false);
  const [porRenovar, setPorRenovar] = useState<UsuarioBanco | null>(null);

  const puede = !!usuario?.acciones?.includes(PERMISO_USUARIOS);
  const puedeRoles = !!usuario?.acciones?.includes("ASIGNAR_ROLES");

  useEffect(() => {
    obtenerMiPerfil().then(setUsuario).catch(() => setUsuario(null));
  }, []);

  const recargar = useCallback(async () => {
    try {
      setLista(await listarUsuarios());
    } catch (err) {
      setAviso({ texto: mensajeError(err), error: true });
    }
  }, []);

  useEffect(() => {
    // Primera carga de la lista al confirmar el permiso; recargar solo actualiza el estado al responder.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (puede) void recargar();
  }, [puede, recargar]);

  async function crear(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (enviando) return;
    setEnviando(true);
    setAviso(null);
    try {
      const creado = await crearUsuario({ username: username.trim(), nombre: nombre.trim(), rol });
      if (creado.clave_inicial)
        setEntrega({ username: creado.username, nombre: creado.nombre, clave: creado.clave_inicial, motivo: "alta" });
      setFormulario(false);
      setNombre(""); setUsername(""); setRol("ASESOR");
      await recargar();
    } catch (err) {
      setAviso({ texto: mensajeError(err), error: true });
    } finally {
      setEnviando(false);
    }
  }

  async function accion(texto: string, tarea: () => Promise<unknown>) {
    setAviso(null);
    try {
      await tarea();
      setAviso({ texto, error: false });
      await recargar();
    } catch (err) {
      setAviso({ texto: mensajeError(err), error: true });
    }
  }

  async function confirmarRenovacion() {
    const u = porRenovar;
    setPorRenovar(null);
    if (!u) return;
    try {
      const r = await renovarClave(u.id_usuario);
      setEntrega({ username: u.username, nombre: u.nombre, clave: r.clave_inicial, motivo: "renovacion" });
      await recargar();
    } catch (err) {
      setAviso({ texto: mensajeError(err), error: true });
    }
  }

  return (
    <div className="sol-shell">
      <aside className="sol-sidebar">
        <div className="sol-brand light">
          <div>
            <strong>BNA<span>®</span></strong>
            <small>Banco Nacional de Arequipa</small>
          </div>
        </div>
        <nav aria-label="Navegación Usuarios" style={{ marginTop: "32px" }}>
          <p>ADMINISTRACIÓN</p>
          <span className="tj-enlace-nav active" aria-current="page">Usuarios</span>
          <Link href="/" className="tj-enlace-nav">Volver al portal</Link>
        </nav>
        {usuario && (
          <div className="sol-sidebar-bottom">
            <div className="sol-profile">
              <span className="sol-avatar">{usuario.nombre.trim()[0]?.toUpperCase()}</span>
              <div>
                <strong>{usuario.nombre}</strong>
                <small>{nombreRol(usuario.rol)}</small>
              </div>
            </div>
            <Link href="/login" onClick={cerrarSesion} className="tj-enlace-nav">Cerrar sesión</Link>
          </div>
        )}
      </aside>

      <div className="sol-work">
        <header className="sol-topbar">
          <div><span>Administración</span><b>/</b>Usuarios</div>
          <div className="sol-topbar-right">
            <Link href="/" style={{ color: "#15324f", fontWeight: 600, textDecoration: "none", fontSize: "13px" }}>Volver al portal</Link>
          </div>
        </header>

        <main className="sol-main">
          <div className="sol-heading">
            <div>
              <h1>Usuarios</h1>
              <p className="tj-sub">Altas del personal, roles y contraseñas. La contraseña inicial la genera el sistema y se muestra una sola vez.</p>
            </div>
            {puede && !formulario && (
              <button type="button" className="sol-button" onClick={() => { setFormulario(true); setAviso(null); }}>Nuevo usuario</button>
            )}
          </div>

          {usuario === undefined && <p role="status">Comprobando tu sesión…</p>}

          {usuario === null && (
            <div role="alert" className="sol-alert error">
              Tu sesión no está iniciada o ya venció.
              <Link href="/login" onClick={cerrarSesion} style={{ marginLeft: "auto", fontWeight: 600, color: "inherit" }}>Iniciar sesión</Link>
            </div>
          )}

          {usuario && !puede && (
            <section className="sol-card">
              <div className="sol-empty" role="status">
                <h3>Esta pantalla es para administradores.</h3>
                <p>Tu rol ({nombreRol(usuario.rol)}) no puede crear usuarios. Si necesitas una cuenta para alguien, pídesela a un administrador.</p>
                <Link className="sol-button secondary" href="/">Volver al portal</Link>
              </div>
            </section>
          )}

          {usuario && puede && (
            <>
              {aviso && <div role={aviso.error ? "alert" : "status"} className={`sol-alert ${aviso.error ? "error" : "success"}`}>{aviso.texto}</div>}

              {entrega && <ClaveParaEntregar entrega={entrega} onListo={() => setEntrega(null)} />}

              {formulario && (
                <section className="sol-card" style={{ marginBottom: "24px" }}>
                  <div className="sol-card-title"><div><h2>Nuevo usuario</h2><p>El sistema genera la contraseña inicial: no hace falta inventarla.</p></div></div>
                  <form onSubmit={crear} className="tj-form" style={{ display: "grid", gap: "12px", maxWidth: "480px" }}>
                    <label htmlFor="nu-nombre">Nombre completo</label>
                    <input id="nu-nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required maxLength={100} />
                    <label htmlFor="nu-usuario">Usuario</label>
                    <input id="nu-usuario" value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} maxLength={40}
                      placeholder="Por ejemplo, ana.quispe" autoComplete="off" />
                    <label htmlFor="nu-rol">Rol</label>
                    <select id="nu-rol" value={rol} onChange={(e) => setRol(e.target.value)}>
                      {ROLES.map((r) => <option key={r} value={r}>{nombreRol(r)}</option>)}
                    </select>
                    <div style={{ display: "flex", gap: "12px" }}>
                      <button type="submit" className="sol-button" disabled={enviando}>{enviando ? "Creando…" : "Crear usuario"}</button>
                      <button type="button" className="sol-button secondary" onClick={() => setFormulario(false)}>Cancelar</button>
                    </div>
                  </form>
                </section>
              )}

              <section className="sol-card">
                <div className="sol-card-title"><div><h2>Personal con acceso</h2><p>{lista ? `${lista.length} usuarios` : "Cargando…"}</p></div></div>
                {lista && (
                  <div style={{ overflowX: "auto" }}>
                    <table className="sol-table">
                      <thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
                      <tbody>
                        {lista.map((u) => {
                          const servicio = u.rol === "SERVICIO";
                          return (
                            <tr key={u.id_usuario}>
                              <td>{u.username}</td>
                              <td>{u.nombre}</td>
                              <td>
                                {servicio || !puedeRoles ? nombreRol(u.rol) : (
                                  <select aria-label={`Rol de ${u.username}`} value={u.rol}
                                    onChange={(e) => accion(`Rol de ${u.username} cambiado a ${nombreRol(e.target.value)}.`, () => cambiarRol(u.id_usuario, e.target.value))}>
                                    {ROLES.map((r) => <option key={r} value={r}>{nombreRol(r)}</option>)}
                                  </select>
                                )}
                              </td>
                              <td>
                                {u.activo ? "Activo" : "Desactivado"}
                                {u.debe_cambiar_clave && <><br /><small>Debe cambiar su contraseña</small></>}
                              </td>
                              <td style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                                {!servicio && (
                                  <button type="button" className="sol-button secondary" onClick={() => setPorRenovar(u)}>Renovar contraseña</button>
                                )}
                                {u.id_usuario !== usuario.id_usuario && (
                                  <button type="button" className="sol-button secondary"
                                    onClick={() => accion(u.activo ? `${u.username} ya no puede entrar.` : `${u.username} puede volver a entrar.`,
                                      () => cambiarEstado(u.id_usuario, !u.activo))}>
                                    {u.activo ? "Desactivar" : "Activar"}
                                  </button>
                                )}
                                {!servicio && (
                                  <button type="button" className="sol-button secondary"
                                    onClick={() => accion(`Ingreso de ${u.username} desbloqueado.`, () => desbloquearIngreso(u.id_usuario))}>
                                    Desbloquear ingreso
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          )}

          {porRenovar && (
            <div role="dialog" aria-modal="true" aria-labelledby="titulo-renovar" className="tj-modal-fondo"
              style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.35)", display: "grid", placeItems: "center" }}>
              <div className="sol-card" style={{ maxWidth: "440px" }}>
                <h2 id="titulo-renovar">¿Renovar la contraseña de {porRenovar.username}?</h2>
                <p>La actual dejará de servir. Verás una contraseña temporal para entregarle, y tendrá que cambiarla al entrar.</p>
                <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
                  <button type="button" className="sol-button" onClick={confirmarRenovacion}>Sí, renovar</button>
                  <button type="button" className="sol-button secondary" onClick={() => setPorRenovar(null)}>Cancelar</button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
