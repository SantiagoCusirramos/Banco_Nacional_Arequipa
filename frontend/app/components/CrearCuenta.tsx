"use client";

import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { crearCuenta, mensajeDeError, REGIMENES, ROLES_TITULAR, type Cuenta } from "@/lib/cuentas";
import { CuentaResumen } from "./CuentaResumen";

const requerido = (mensaje: string) => z.string().trim().min(1, mensaje);

const esquema = z
  .object({
    id_cliente: requerido("Ingresa el ID del cliente."),
    id_producto_ahorro: requerido("Ingresa el ID del producto de ahorro."),
    id_agencia: requerido("Ingresa el ID de la agencia."),
    regimen: z.enum(REGIMENES),
    rol_principal: z.enum(ROLES_TITULAR),
    titulares: z.array(
      z.object({ id_cliente: requerido("Ingresa el ID del titular."), rol_titular: z.enum(ROLES_TITULAR) }),
    ),
  })
  .superRefine((valores, ctx) => {
    const vistos = new Set([valores.id_cliente]);
    valores.titulares.forEach((titular, i) => {
      if (vistos.has(titular.id_cliente)) {
        ctx.addIssue({ code: "custom", path: ["titulares", i, "id_cliente"], message: "Este cliente ya figura como titular." });
      }
      vistos.add(titular.id_cliente);
    });
    // RGN-16: una cuenta mancomunada requiere al menos dos titulares
    const mancomunada = valores.rol_principal === "MANCOMUNADO" || valores.titulares.some((t) => t.rol_titular === "MANCOMUNADO");
    if (mancomunada && valores.titulares.length < 1) {
      ctx.addIssue({ code: "custom", path: ["titulares"], message: "Una cuenta mancomunada requiere al menos dos titulares (RGN-16)." });
    }
  });

type Valores = z.infer<typeof esquema>;

const VALORES_INICIALES: Valores = {
  id_cliente: "",
  id_producto_ahorro: "",
  id_agencia: "",
  regimen: "LIBRE",
  rol_principal: "TITULAR",
  titulares: [],
};

type Props = {
  onNotice: (mensaje: string) => void;
  onModificar: (cuenta: Cuenta) => void;
};

export function CrearCuenta({ onNotice, onModificar }: Props) {
  const [creada, setCreada] = useState<Cuenta | null>(null);
  const [errorServidor, setErrorServidor] = useState("");
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Valores>({ resolver: zodResolver(esquema), defaultValues: VALORES_INICIALES });
  const { fields, append, remove } = useFieldArray({ control, name: "titulares" });

  async function enviar(valores: Valores) {
    setErrorServidor("");
    const vinculos = [{ id_cliente: valores.id_cliente, rol_titular: valores.rol_principal }, ...valores.titulares];
    // Si solo hay un titular con rol TITULAR el backend lo vincula por defecto.
    const enviarTitulares = valores.titulares.length > 0 || valores.rol_principal !== "TITULAR";
    try {
      const cuenta = await crearCuenta({
        id_cliente: valores.id_cliente,
        id_producto_ahorro: valores.id_producto_ahorro,
        id_agencia: valores.id_agencia,
        regimen: valores.regimen,
        titulares: enviarTitulares ? vinculos : undefined,
      });
      setCreada(cuenta);
      onNotice(`Cuenta ${cuenta.num_cuenta} creada correctamente.`);
    } catch (err) {
      setErrorServidor(mensajeDeError(err));
    }
  }

  if (creada) {
    return (
      <div className="fx-stack">
        <CuentaResumen cuenta={creada} titulo="Cuenta creada" />
        <div className="fx-actions">
          <button className="outline-button" onClick={() => onModificar(creada)}>Modificar estado de esta cuenta</button>
          <button className="primary-button" onClick={() => { setCreada(null); reset(VALORES_INICIALES); onNotice(""); }}>Abrir otra cuenta</button>
        </div>
      </div>
    );
  }

  const errorTitulares = errors.titulares?.root?.message ?? errors.titulares?.message;

  return (
    <div className="form-card">
      <div className="form-intro">
        <span className="form-icon">＋</span>
        <div>
          <h2>Abrir cuenta de ahorros</h2>
          <p>La cuenta se crea activa y con saldo cero, vinculada a los titulares indicados.</p>
        </div>
      </div>

      <form className="fx-form" onSubmit={handleSubmit(enviar)} noValidate>
        <div className="fx-field">
          <label htmlFor="id_cliente">ID del cliente</label>
          <input id="id_cliente" autoComplete="off" placeholder="Identificador del cliente titular" aria-invalid={!!errors.id_cliente} {...register("id_cliente")} />
          {errors.id_cliente && <span className="fx-error">{errors.id_cliente.message}</span>}
        </div>

        <div className="fx-grid">
          <div className="fx-field">
            <label htmlFor="id_producto_ahorro">ID del producto de ahorro</label>
            <input id="id_producto_ahorro" autoComplete="off" placeholder="Identificador del producto" aria-invalid={!!errors.id_producto_ahorro} {...register("id_producto_ahorro")} />
            {errors.id_producto_ahorro && <span className="fx-error">{errors.id_producto_ahorro.message}</span>}
            <span className="fx-hint">La moneda de la cuenta la define el producto.</span>
          </div>
          <div className="fx-field">
            <label htmlFor="id_agencia">ID de la agencia</label>
            <input id="id_agencia" autoComplete="off" placeholder="Identificador de la agencia" aria-invalid={!!errors.id_agencia} {...register("id_agencia")} />
            {errors.id_agencia && <span className="fx-error">{errors.id_agencia.message}</span>}
          </div>
        </div>

        <div className="fx-field">
          <label htmlFor="regimen">Régimen</label>
          <select id="regimen" {...register("regimen")}>
            {REGIMENES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>

        <div className="fx-section">
          <div className="fx-section-head">
            <div>
              <strong>Titulares</strong>
              <p className="fx-hint">Opcional: agrega titulares adicionales o cambia el rol del cliente principal.</p>
            </div>
            <button type="button" className="text-button" onClick={() => append({ id_cliente: "", rol_titular: "TITULAR" })}>＋ Agregar titular</button>
          </div>

          <div className="fx-titular-row">
            <div className="fx-field">
              <label htmlFor="rol_principal">Rol del cliente principal</label>
              <select id="rol_principal" {...register("rol_principal")}>
                {ROLES_TITULAR.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>

          {fields.map((campo, i) => (
            <div className="fx-titular-row" key={campo.id}>
              <div className="fx-field">
                <label htmlFor={`titulares.${i}.id_cliente`}>{`ID del titular ${i + 2}`}</label>
                <input id={`titulares.${i}.id_cliente`} autoComplete="off" placeholder="Identificador del cliente" aria-invalid={!!errors.titulares?.[i]?.id_cliente} {...register(`titulares.${i}.id_cliente`)} />
                {errors.titulares?.[i]?.id_cliente && <span className="fx-error">{errors.titulares[i]?.id_cliente?.message}</span>}
              </div>
              <div className="fx-field">
                <label htmlFor={`titulares.${i}.rol_titular`}>{`Rol del titular ${i + 2}`}</label>
                <select id={`titulares.${i}.rol_titular`} {...register(`titulares.${i}.rol_titular`)}>
                  {ROLES_TITULAR.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
              <button type="button" className="fx-remove" aria-label={`Quitar titular ${i + 2}`} onClick={() => remove(i)}>×</button>
            </div>
          ))}
          {errorTitulares && <span className="fx-error" role="alert">{errorTitulares}</span>}
        </div>

        {errorServidor && <div className="fx-alert" role="alert">{errorServidor}</div>}

        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creando cuenta…" : "Crear cuenta"} <span>→</span>
        </button>
      </form>
    </div>
  );
}
