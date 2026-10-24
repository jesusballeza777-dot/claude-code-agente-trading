// Cliente de la API del Centro de Mando. Solo GET, salvo la sesión y las notas del diario.

export type Origen = "real" | "backtest" | "demo";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json", "X-Brujula": "1" } : {}),
      ...(init?.method && init.method !== "GET" ? { "X-Brujula": "1" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown; detalle?: unknown };
      detail = String(body.detail ?? body.detalle ?? detail);
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export interface Fase {
  id: string;
  nombre: string;
  estado: string;
}

export interface Pendiente {
  tarea: string;
  documento: string;
}

export interface Estado {
  origen: Origen;
  fase_actual: string;
  fases: Fase[];
  live_trading: boolean;
  holdout: { desde: string; sellado: boolean };
  datos: {
    disponible: boolean;
    dataset_id?: string;
    ficheros?: number;
    ultima_vela?: string;
    completitud?: number;
  };
  motor_de_riesgo: { limites: string; version_limites: string; reglas_v1: string; estado: string };
  intentos: { principales: number; total: number };
  pendientes_propietario: Pendiente[];
}

export interface Cuenta {
  origen: Origen;
  capital: string;
  maximo: string;
  drawdown: number;
  umbrales: { parada: number; corte_duro: number };
  presupuesto: {
    diario: { usado: number; limite: number; texto: string };
    semanal: { usado: number; limite: number };
  };
  curva: { t: string; capital: number }[];
}

export interface Hoy {
  estado: Estado;
  parte_del_dia: { autor: string; texto: string; validado: boolean };
  cuenta: Cuenta;
  posiciones: { origen: Origen; items: unknown[]; vacio: string };
  eventos_macro: { origen: Origen; items: unknown[]; vacio: string };
}

export interface Resumen {
  operaciones: number;
  esperanza_r: number;
  ic90_r: [number, number];
  pf: number | null;
  sharpe_por_operacion: number;
  tasa_acierto: number;
  max_dd_curva?: number;
  por_direccion: Record<string, { n: number; esperanza_r: number }>;
  por_semestre: Record<string, { n: number; esperanza_r: number }>;
  por_regimen: Record<string, { n: number; esperanza_r: number }>;
  max_peso_mes: number | null;
  senales: Record<string, number>;
  vetos: Record<string, number>;
  salidas: Record<string, number>;
}

export interface Etapa {
  etapa: string;
  estado: string;
}

export interface HipotesisResumen {
  id: string;
  titulo: string;
  evaluada: boolean;
  ciclo: Etapa[];
  resumen: Resumen | null;
  gate: { pasa_sin_holdout: boolean; criterios: Record<string, boolean> } | null;
  pista: string | null;
  corridas: number;
}

export interface Laboratorio {
  origen: Origen;
  hipotesis: HipotesisResumen[];
  intentos: { principales: number; total: number; explicacion: string };
  prereg_commit: string;
}

export interface Gate {
  hipotesis: string;
  criterios: Record<string, boolean>;
  pasa_gate_sin_holdout: boolean;
  holdout: string;
  valores: {
    operaciones: number;
    esperanza_r: number;
    ic90_r: [number, number];
    pf: number | null;
    dsr: number;
    pbo: number;
    maxdd_p95_mc: number;
    "variantes_±20%": Record<string, number>;
    "costes_x1.5_ic90": [number, number];
    regimenes_positivos: string[];
    max_peso_mes: number | null;
    c16_cortos: string;
  };
}

export interface Operacion {
  id?: string;
  hipotesis?: string;
  simbolo: string;
  lado: string;
  senal: string;
  entrada: string;
  precio_entrada: string;
  stop: string;
  cantidad: string;
  riesgo_planificado: string;
  salida: string;
  precio_salida: string;
  motivo_salida: string;
  comisiones: string;
  funding: string;
  pnl: string;
  r: number;
  regimen: string;
}

export interface VetoContado {
  codigo: string;
  titulo: string;
  explicacion: string;
  veces: number;
}

export interface DetalleHipotesis {
  origen: Origen;
  id: string;
  titulo: string;
  trial_id: string;
  parametros: Record<string, number>;
  codigo_commit: string;
  dataset_id: string;
  resumen: Resumen;
  gate: Gate | null;
  curva: { t: string; capital: number }[];
  underwater: { t: string; dd: number }[];
  distribucion_r: { desde: number; hasta: number; n: number }[];
  mapa_mensual: { mes: string; r: number }[];
  abanico_monte_carlo: { operacion: number; p5: number; p25: number; p50: number; p75: number; p95: number }[];
  sensibilidad: {
    parametro: string;
    base: number;
    valores: { valor: number; esperanza_r: number; operaciones: number }[];
  }[];
  variantes_extra: { variante: string; tipo: string; resumen: Resumen }[];
  h4: Record<string, number | null> | null;
  vetos: VetoContado[];
  operaciones: Operacion[];
}

export interface Velas {
  origen: Origen;
  simbolo: string;
  intervalo: string;
  velas: { t: string; o: number; h: number; l: number; c: number }[];
  indicadores: Record<string, (number | null)[]>;
  marcadores: { t: string; tipo: string; lado?: string; motivo?: string; r: number }[];
  funding: { t: string; tasa_8h: number }[];
}

export interface Veto {
  code: string;
  title: string;
  message: string;
}

export interface Calculo {
  origen: Origen;
  motor: string;
  aprobada: boolean;
  cantidad: string;
  nocional: string;
  riesgo_usd: string | null;
  presupuesto_usd: string;
  apalancamiento_efectivo: string | null;
  precio_liquidacion: string | null;
  costes: { comision: string; slippage: string };
  vetos: Veto[];
}

export interface Limites {
  origen: Origen;
  editable: boolean;
  aviso: string;
  vigentes: { nombre: string; valor: string; techo_plan: string; unidad: string; adr: string }[];
  grupos_correlacionados: string[][];
  propuestos_adr_013: Record<string, string | number | string[]>;
}

export interface Decision {
  t: string;
  accion: string;
  nivel: string;
  motivo: string;
  evidencia: string[];
  veto: string | null;
  json: Record<string, unknown>;
}

export interface Decisiones {
  origen: Origen;
  vacio: string;
  decisiones: Decision[];
  libros: { libro: string; operaciones: number; esperanza_r: number | null }[];
}

export interface Nota {
  id: string;
  fecha_utc: string;
  referencia: string;
  texto: string;
}

export interface Diario {
  origen: Origen;
  aviso: string;
  vacio: string;
  operaciones: Operacion[];
  notas: Nota[];
}

export interface Proyecto {
  origen: Origen;
  fases: Fase[];
  adr: { id: string; titulo: string; estado: string }[];
  riesgos: { id: string; riesgo: string; probabilidad: string; impacto: string }[];
  pendientes_propietario: Pendiente[];
  costes: {
    conceptos: { concepto: string; usd_mes: string; estado: string }[];
    tipo_de_cambio: { mxn_por_usd: string; estado: string };
    uso_api_claude: { origen: Origen; nota: string; meses: { mes: string; tokens: number; usd: string }[] };
  };
}

export interface Reportes {
  origen: Origen;
  reportes: { tipo: string; formato: string; nombre: string; mime: string }[];
  historial: { fecha_utc: string; tipo: string; formato: string; archivo: string; demo: boolean; sha256: string }[];
}

export interface Glosario {
  copiloto: string;
  terminos: Record<string, string>;
  vacios: Record<string, string>;
}
