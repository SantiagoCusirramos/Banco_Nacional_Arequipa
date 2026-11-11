"use client";

import { useEffect, useState } from "react";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { nombreCompleto, obtenerCliente, type Cliente } from "@/lib/clientes";
import { listarAgencias, type Agencia } from "@/lib/catalogos";
import { abrirCuenta, mensajeDeError, MONEDAS, REGIMENES, type Cuenta } from "@/lib/cuentas";
import { CuentaResumen } from "./CuentaResumen";

const requerido = (mensaje: string) => z.string().trim().min(1, mensaje);

const esquema = z
  .object({
    cod_cliente: requerido("Busca y selecciona el cliente titular."),
    moneda: z.enum(MONEDAS),
    id_agencia: requerido("Selecciona una agencia."),
    regimen: z.enum(REGIMENES),
    titulares: z.array(z.object({ cod_cliente: requerido("Busca y selecciona el cliente titular.") })),
  })
  .superRefine((valores, ctx) => {
    const vistos = new Set([valores.cod_cliente]);
    valores.titulares.forEach((titular, i) => {
      if (titular.cod_cliente && vistos.has(titular.cod_cliente)) {
        ctx.addIssue({ code: "custom", path: ["titulares", i, "cod_cliente"], message: "Este cliente ya figura como titular." });
      }
      vistos.add(titular.cod_cliente);
    });
    const mancomunada = valores.regimen !== "INDIVIDUAL";
    if (mancomunada && valores.titulares.length < 1) {
      ctx.addIssue({ code: "custom", path: ["titulares"], message: "Una cuenta mancomunada requiere al menos dos titulares (RGN-16)." });
    }
    if (!mancomunada && valores.titulares.length > 0) {
      ctx.addIssue({ code: "custom", path: ["titulares"], message: "Una cuenta individual tiene un solo titular." });
    }
  });

type Valores = z.infer<typeof esquema>;

const VALORES_INICIALES: Valores = {
  cod_cliente: "",
  moneda: "PEN",
  id_agencia: "",
  regimen: "INDIVIDUAL",
  titulares: [],
};

type Props = {
  onNotice: (mensaje: string) => void;
  onModificar: (cuenta: Cuenta) => void;
};

type ClienteSelectorProps = {
  id: string;
  label: string;
  value: string;
  onChange: (codCliente: string) => void;
  error?: string;
};

// El CORE no busca clientes por documento ni por nombre: se consulta por su código.
function ClienteSelector({ id, label, value, onChange, error }: ClienteSelectorProps) {
  const [codigo, setCodigo] = useState("");
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [errorBusqueda, setErrorBusqueda] = useState("");

  async function buscar() {
    const consulta = codigo.trim().toUpperCase();
    if (!consulta) {
      setErrorBusqueda("Ingresa el código del cliente para buscar.");
      return;
    }
    setBuscando(true);
    setErrorBusqueda("");
    try {
      const encontrado = await obtenerCliente(consulta);
      setCliente(encontrado);
      if (encontrado.permite_operar) {
        onChange(encontrado.cod_cliente);
      } else {
        onChange("");
        setErrorBusqueda(`El cliente está ${encontrado.estado_cliente} y no puede operar.`);
      }
    } catch (err) {
      setCliente(null);
      setErrorBusqueda(mensajeDeError(err));
      onChange("");
    } finally {
      setBuscando(false);
    }
  }

  return (
    <div className="fx-field">
      <label htmlFor={id}>{label}</label>
      <div className="fx-search">
        <div className="fx-field fx-grow">
          <input
            id={id}
            autoComplete="off"
            placeholder="Código del cliente, por ejemplo CLI000000001"
            maxLength={12}
            value={codigo}
            aria-invalid={!!error}
            onChange={(event) => {
              setCodigo(event.target.value);
              setCliente(null);
              setErrorBusqueda("");
              onChange("");
            }}
          />
        </div>
        <button className="outline-button" type="button" aria-label={"Buscar " + id} onClick={buscar} disabled={buscando}>
          {buscando ? "Buscando..." : "Buscar"}
        </button>
      </div>
      {cliente && value && (
        <span className="fx-hint">
          Cliente seleccionado: {nombreCompleto(cliente)} · {cliente.tipo_documento} {cliente.numero_documento} · {cliente.estado_cliente}
        </span>
      )}
      {errorBusqueda && <span className="fx-error" role="status">{errorBusqueda}</span>}
      {error && <span className="fx-error">{error}</span>}
    </div>
  );
}

export function CrearCuenta({ onNotice, onModificar }: Props) {
  const [creada, setCreada] = useState<Cuenta | null>(null);
  const [errorServidor, setErrorServidor] = useState("");
  const [errorCatalogos, setErrorCatalogos] = useState("");
  const [agencias, setAgencias] = useState<Agencia[]>([]);
  const [cargandoCatalogos, setCargandoCatalogos] = useState(true);
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Valores>({ resolver: zodResolver(esquema), defaultValues: VALORES_INICIALES });
  const { fields, append, remove } = useFieldArray({ control, name: "titulares" });

  useEffect(() => {
    let activo = true;
    listarAgencias()
      .then((disponibles) => {
        if (!activo) return;
        setAgencias(disponibles);
        if (disponibles.length === 0) setErrorCatalogos("No hay agencias para seleccionar.");
      })
      .catch((err) => {
        if (activo) setErrorCatalogos(mensajeDeError(err));
      })
      .finally(() => {
        if (activo) setCargandoCatalogos(false);
      });
    return () => {
      activo = false;
    };
  }, []);

  async function enviar(valores: Valores) {
    setErrorServidor("");
    try {
      const cuenta = await abrirCuenta({
        moneda: valores.moneda,
        regimen: valores.regimen,
        id_agencia: valores.id_agencia,
        titulares: [valores.cod_cliente, ...valores.titulares.map((t) => t.cod_cliente)],
      });
      setCreada(cuenta);
      onNotice("Cuenta " + cuenta.num_cuenta + " creada correctamente.");
    } catch (err) {
      setErrorServidor(mensajeDeError(err));
    }
  }

  if (creada) {
    return (
      <div className="fx-stack">
        <CuentaResumen cuenta={creada} titulo="Cuenta creada" />
        <div className="fx-actions">
          <button className="outline-button" onClick={() => onModificar(creada)}>Ver el estado de esta cuenta</button>
          <button className="primary-button" onClick={() => { setCreada(null); reset(VALORES_INICIALES); onNotice(""); }}>Abrir otra cuenta</button>
        </div>
      </div>
    );
  }

  const errorTitulares = errors.titulares?.root?.message ?? errors.titulares?.message;

  return (
    <div className="form-card">
      <div className="form-intro">
        <span className="form-icon">+</span>
        <div>
          <h2>Abrir cuenta de ahorros</h2>
          <p>Busca al cliente por su código y elige la moneda, la agencia y el régimen de la cuenta.</p>
        </div>
      </div>

      {cargandoCatalogos && <p className="fx-hint" role="status">Cargando agencias...</p>}
      {errorCatalogos && <div className="fx-alert" role="alert">{errorCatalogos}</div>}

      <form className="fx-form" onSubmit={handleSubmit(enviar)} noValidate>
        <Controller
          name="cod_cliente"
          control={control}
          render={({ field }) => (
            <ClienteSelector
              id="cod_cliente"
              label="Cliente titular"
              value={field.value}
              onChange={field.onChange}
              error={errors.cod_cliente?.message}
            />
          )}
        />

        <div className="fx-grid">
          <div className="fx-field">
            <label htmlFor="moneda">Moneda</label>
            <select id="moneda" {...register("moneda")}>
              {MONEDAS.map((moneda) => <option key={moneda} value={moneda}>{moneda}</option>)}
            </select>
          </div>
          <div className="fx-field">
            <label htmlFor="id_agencia">Agencia</label>
            <select id="id_agencia" disabled={cargandoCatalogos || agencias.length === 0} aria-invalid={!!errors.id_agencia} {...register("id_agencia")}>
              <option value="">Selecciona una agencia...</option>
              {agencias.map((agencia) => (
                <option key={agencia.id_agencia} value={agencia.id_agencia}>
                  {agencia.nombre} · {agencia.id_agencia}
                </option>
              ))}
            </select>
            {errors.id_agencia && <span className="fx-error">{errors.id_agencia.message}</span>}
          </div>
        </div>

        <div className="fx-field">
          <label htmlFor="regimen">Régimen</label>
          <select id="regimen" {...register("regimen")}>
            {REGIMENES.map((regimen) => <option key={regimen} value={regimen}>{regimen}</option>)}
          </select>
          <span className="fx-hint">Una cuenta mancomunada necesita al menos dos titulares.</span>
        </div>

        <div className="fx-section">
          <div className="fx-section-head">
            <div>
              <strong>Titulares adicionales</strong>
              <p className="fx-hint">Solo para cuentas mancomunadas.</p>
            </div>
            <button type="button" className="text-button" onClick={() => append({ cod_cliente: "" })}>+ Agregar titular</button>
          </div>

          {fields.map((campo, i) => (
            <div className="fx-titular-row" key={campo.id}>
              <Controller
                name={`titulares.${i}.cod_cliente`}
                control={control}
                render={({ field }) => (
                  <ClienteSelector
                    id={"titular_" + (i + 2)}
                    label={"Titular " + (i + 2)}
                    value={field.value}
                    onChange={field.onChange}
                    error={errors.titulares?.[i]?.cod_cliente?.message}
                  />
                )}
              />
              <button type="button" className="fx-remove" aria-label={"Quitar titular " + (i + 2)} onClick={() => remove(i)}>×</button>
            </div>
          ))}
          {errorTitulares && <span className="fx-error" role="alert">{errorTitulares}</span>}
        </div>

        {errorServidor && <div className="fx-alert" role="alert">{errorServidor}</div>}

        <button className="primary-button" type="submit" disabled={isSubmitting || cargandoCatalogos || !!errorCatalogos}>
          {isSubmitting ? "Creando cuenta..." : "Crear cuenta"} <span>→</span>
        </button>
      </form>
    </div>
  );
}
