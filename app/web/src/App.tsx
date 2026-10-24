import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useState, type FormEvent, type ReactNode } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";
import { BrujulaAvatar } from "./components/Brujula";
import { Layout } from "./components/Layout";
import { Button, ErrorState, Loading } from "./components/ui";
import { api } from "./lib/api";

// Cada página se carga al visitarla: el primer pintado no espera a las librerías de gráficas.
const Hoy = lazy(() => import("./pages/Hoy").then((m) => ({ default: m.Hoy })));
const Mercado = lazy(() => import("./pages/Mercado").then((m) => ({ default: m.Mercado })));
const Laboratorio = lazy(() => import("./pages/Laboratorio").then((m) => ({ default: m.Laboratorio })));
const Riesgo = lazy(() => import("./pages/Riesgo").then((m) => ({ default: m.Riesgo })));
const Estilo = lazy(() => import("./pages/Estilo").then((m) => ({ default: m.Estilo })));
const Decisiones = lazy(() => import("./pages/Otras").then((m) => ({ default: m.Decisiones })));
const Diario = lazy(() => import("./pages/Otras").then((m) => ({ default: m.Diario })));
const Proyecto = lazy(() => import("./pages/Otras").then((m) => ({ default: m.Proyecto })));
const Reportes = lazy(() => import("./pages/Otras").then((m) => ({ default: m.Reportes })));
const Ajustes = lazy(() => import("./pages/Otras").then((m) => ({ default: m.Ajustes })));

const page = (element: ReactNode) => <Suspense fallback={<Loading />}>{element}</Suspense>;

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: page(<Hoy />) },
      { path: "mercado", element: page(<Mercado />) },
      { path: "laboratorio", element: page(<Laboratorio />) },
      { path: "decisiones", element: page(<Decisiones />) },
      { path: "riesgo", element: page(<Riesgo />) },
      { path: "diario", element: page(<Diario />) },
      { path: "proyecto", element: page(<Proyecto />) },
      { path: "reportes", element: page(<Reportes />) },
      { path: "ajustes", element: page(<Ajustes />) },
      { path: "estilo", element: page(<Estilo />) },
    ],
  },
]);

interface Sesion {
  autenticacion: boolean;
  activa: boolean;
}

function Login() {
  const client = useQueryClient();
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const login = useMutation({
    mutationFn: () => api.post<Sesion>("/api/sesion", { password, totp }),
    onSuccess: () => void client.invalidateQueries(),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate();
  };
  return (
    <main className="grid min-h-dvh place-items-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl border border-line bg-surface p-6 shadow-card" aria-label="Iniciar sesión">
        <div className="flex items-center gap-3">
          <BrujulaAvatar size={48} />
          <div>
            <h1 className="text-xl font-bold">Centro de Mando</h1>
            <p className="text-sm text-ink-muted">Solo para el propietario. Contraseña y código TOTP.</p>
          </div>
        </div>
        <label className="block text-sm">
          Contraseña
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2" />
        </label>
        <label className="block text-sm">
          Código de 6 dígitos
          <input inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" value={totp} onChange={(e) => setTotp(e.target.value)} className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 tabular" />
        </label>
        {login.error && <ErrorState error={login.error} />}
        <Button type="submit" className="w-full" disabled={login.isPending}>
          Entrar
        </Button>
      </form>
    </main>
  );
}

export function App() {
  const session = useQuery({ queryKey: ["sesion"], queryFn: () => api.get<Sesion>("/api/sesion"), retry: false });
  if (session.isLoading) {
    return (
      <div className="p-6">
        <Loading label="Comprobando la sesión…" />
      </div>
    );
  }
  if (session.data && !session.data.activa) return <Login />;
  return <RouterProvider router={router} />;
}
