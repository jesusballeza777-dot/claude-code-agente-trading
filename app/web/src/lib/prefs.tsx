// Preferencias del visitante (tema, modo explicativo, bienvenida vista). Se guardan en el
// navegador solo por comodidad: si el almacenamiento falla, la app funciona igual.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Theme = "dark" | "light";

interface Prefs {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  explain: boolean;
  setExplain: (on: boolean) => void;
  welcomed: boolean;
  setWelcomed: (seen: boolean) => void;
}

const PrefsContext = createContext<Prefs | null>(null);

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* almacenamiento no disponible: la preferencia dura lo que dure la pestaña */
  }
}

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => (read("cm.tema") === "light" ? "light" : "dark"));
  const [explain, setExplainState] = useState(() => read("cm.explicar") === "1");
  const [welcomed, setWelcomedState] = useState(() => read("cm.bienvenida") === "1");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  const setTheme = useCallback((value: Theme) => {
    setThemeState(value);
    write("cm.tema", value);
  }, []);
  const setExplain = useCallback((value: boolean) => {
    setExplainState(value);
    write("cm.explicar", value ? "1" : "0");
  }, []);
  const setWelcomed = useCallback((value: boolean) => {
    setWelcomedState(value);
    write("cm.bienvenida", value ? "1" : "0");
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, explain, setExplain, welcomed, setWelcomed }),
    [theme, setTheme, explain, setExplain, welcomed, setWelcomed],
  );
  return <PrefsContext.Provider value={value}>{children}</PrefsContext.Provider>;
}

export function usePrefs(): Prefs {
  const prefs = useContext(PrefsContext);
  if (!prefs) throw new Error("usePrefs fuera de PrefsProvider");
  return prefs;
}
