/* =========================================================
   DATOS SIMULADOS DEL BNA  (mock – no hay Bus real disponible)
   Se usan para alimentar el prototipo de Home Banking.
   ========================================================= */

const DATOS_BNA = {
  /* -------- Clientes -------- */
  clientes: [
    {
      codCliente: "CL-0004821",
      nombres: "Rosa M. Quispe Salas",
      dni: "45871236",
      claveWeb: "246810",
      estado: "ACTIVO",
      intentosFallidos: 0
    },
    {
      codCliente: "CL-0009930",
      nombres: "Julio A. Ticona Rojas",
      dni: "41209877",
      claveWeb: "777777",
      estado: "ACTIVO",
      intentosFallidos: 0
    },
    {
      codCliente: "CL-0007712",
      nombres: "Miriam E. Farfan Ccahuana",
      dni: "48990112",
      claveWeb: "555555",
      estado: "BLOQUEADO",
      intentosFallidos: 3
    }
  ],

  /* -------- Tarjetas (módulo TARJETAS) -------- */
  tarjetas: [
    {
      numTarjeta: "4507193466204471",
      presentacion: "4507 1934 6620 4471",
      codCliente: "CL-0004821",
      marca: "Débito Visa BNA",
      tipo: "Débito",
      vencimiento: "07/29",
      estado: "ACTIVA",
      canalClave: "6 dígitos (banca por internet)"
    },
    {
      numTarjeta: "4507193466208890",
      presentacion: "4507 1934 6620 8890",
      codCliente: "CL-0004821",
      marca: "Crédito BNA Arequipa",
      tipo: "Crédito",
      vencimiento: "11/27",
      estado: "ACTIVA",
      canalClave: "6 dígitos (banca por internet)"
    },
    {
      numTarjeta: "4507193466201173",
      presentacion: "4507 1934 6620 1173",
      codCliente: "CL-0009930",
      marca: "Débito Visa BNA",
      tipo: "Débito",
      vencimiento: "03/26",
      estado: "VENCIDA",
      canalClave: "6 dígitos (banca por internet)"
    },
    {
      numTarjeta: "4507193466205502",
      presentacion: "4507 1934 6620 5502",
      codCliente: "CL-0009930",
      marca: "Débito Visa BNA",
      tipo: "Débito",
      vencimiento: "09/30",
      estado: "BLOQUEADA",
      canalClave: "6 dígitos (banca por internet)"
    }
  ],

  /* -------- Cuentas (módulo CUENTAS) -------- */
  cuentas: [
    {
      numCuenta: "0011-0458-01",
      codCliente: "CL-0004821",
      tipoCuenta: "Cuenta Corriente",
      moneda: "PEN",
      saldoContable: 8450.75,
      saldoDisponible: 8120.00,
      estado: "ACTIVA",
      titularidad: "Individual"
    },
    {
      numCuenta: "0011-0458-02",
      codCliente: "CL-0004821",
      tipoCuenta: "Cuenta de Ahorro",
      moneda: "USD",
      saldoContable: 2310.40,
      saldoDisponible: 2310.40,
      estado: "ACTIVA",
      titularidad: "Individual"
    },
    {
      numCuenta: "0011-0458-03",
      codCliente: "CL-0004821",
      tipoCuenta: "Cuenta de Ahorro Mancomunada",
      moneda: "PEN",
      saldoContable: 15200.00,
      saldoDisponible: 14980.00,
      estado: "ACTIVA",
      titularidad: "Mancomunada (2 titulares)"
    },
    {
      numCuenta: "0011-0458-04",
      codCliente: "CL-0004821",
      tipoCuenta: "Cuenta de Ahorro",
      moneda: "PEN",
      saldoContable: 0,
      saldoDisponible: 0,
      estado: "CERRADA",
      titularidad: "Individual"
    },
    {
      numCuenta: "0011-0993-01",
      codCliente: "CL-0009930",
      tipoCuenta: "Cuenta de Ahorro",
      moneda: "PEN",
      saldoContable: 4120.20,
      saldoDisponible: 4120.20,
      estado: "ACTIVA",
      titularidad: "Individual"
    }
  ],

  /* -------- Movimientos (módulo CUENTAS) -------- */
  movimientos: {
    "0011-0458-01": [
      { fecha: "18/10/2026", operacion: "ABONO NOMINA", glosa: "Pago de remuneraciones octubre", monto: 4800.00, saldo: 8450.75 },
      { fecha: "15/10/2026", operacion: "COMPRONET", glosa: "Pago de servicios - Gas de Arequipa", monto: -185.40, saldo: 3650.75 },
      { fecha: "12/10/2026", operacion: "TRANSF PROPIA", glosa: "Transferencia a 0011-0458-02", monto: -600.00, saldo: 3836.15 },
      { fecha: "05/10/2026", operacion: "ABONO PROPIA", glosa: "Ingreso de efectivo en agencia", monto: 1500.00, saldo: 4436.15 },
      { fecha: "03/10/2026", operacion: "PAGO CUOTA", glosa: "Crédito personal - cuota 14", monto: -920.00, saldo: 2936.15 }
    ],
    "0011-0458-02": [
      { fecha: "17/10/2026", operacion: "TRANSFERENCIA RECIBIDA", glosa: "Desde 0011-0458-01", monto: 600.00, saldo: 2310.40 },
      { fecha: "30/09/2026", operacion: "INTERESES", glosa: "Pago mensual de intereses", monto: 18.60, saldo: 1710.40 },
      { fecha: "22/09/2026", operacion: "COMPRA EXT.", glosa: "Compra en exterior - tipo de cambio oficial", monto: -320.00, saldo: 1691.80 }
    ],
    "0011-0458-03": [
      { fecha: "16/10/2026", operacion: "ABONO EFECTIVO", glosa: "Depósito en agencia Cayma", monto: 3200.00, saldo: 15200.00 },
      { fecha: "10/10/2026", operacion: "RETIRO ATM", glosa: "Retiro en cajero Av. Ejército", monto: -800.00, saldo: 12000.00 },
      { fecha: "01/10/2026", operacion: "ABONO NOMINA", glosa: "Depósito de nómina mancomunada", monto: 2600.00, saldo: 12800.00 }
    ],
    "0011-0993-01": [
      { fecha: "14/10/2026", operacion: "ABONO", glosa: "Ingreso de efectivo", monto: 900.00, saldo: 4120.20 },
      { fecha: "07/10/2026", operacion: "PAGO SERVICIOS", glosa: "Recibo de luz", monto: -142.30, saldo: 3220.20 }
    ]
  },

  /* -------- Parámetros del canal -------- */
  parametros: {
    canal: "HB_WEB",
    limiteDiarioPEN: 10000,
    limiteDiarioUSD: 3000,
    maxIntentos: 3,
    longClaveWeb: 6
  }
};
