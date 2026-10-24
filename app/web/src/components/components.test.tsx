import * as Tooltip from "@radix-ui/react-tooltip";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { PrefsProvider, usePrefs } from "../lib/prefs";
import { BrujulaAvatar, BrujulaSays } from "./Brujula";
import { DrawdownGauge, MonthlyHeatmap } from "./charts/Charts";
import { Check, ExplainLine, OrigenBadge, Switch } from "./ui";

function wrap(children: ReactNode) {
  return render(
    <PrefsProvider>
      <Tooltip.Provider>{children}</Tooltip.Provider>
    </PrefsProvider>,
  );
}

function ExplainToggle() {
  const { explain, setExplain } = usePrefs();
  return <Switch checked={explain} onChange={setExplain} label="Explicar" />;
}

describe("honestidad visual", () => {
  it("lo demo se rotula siempre con texto, no solo con color", () => {
    wrap(<OrigenBadge origen="demo" />);
    expect(screen.getByText("DATOS DE DEMOSTRACIÓN")).toBeInTheDocument();
  });

  it("sí/no llevan icono y texto", () => {
    wrap(
      <>
        <Check ok />
        <Check ok={false} />
        <Check ok={null} />
      </>,
    );
    expect(screen.getByText("sí")).toBeInTheDocument();
    expect(screen.getByText("no")).toBeInTheDocument();
    expect(screen.getByText("pendiente")).toBeInTheDocument();
  });
});

describe("Brújula y modo explicativo", () => {
  it("muestra el avatar accesible y el aviso de cifras verificadas", () => {
    wrap(<BrujulaSays validated>Hoy no hubo señales.</BrujulaSays>);
    expect(screen.getAllByRole("img", { name: "Brújula, tu copiloto" })).toHaveLength(1);
    expect(screen.getByText("cifras verificadas con los datos")).toBeInTheDocument();
    render(<BrujulaAvatar size={20} />);
  });

  it("las explicaciones aparecen al activar el modo explicativo", async () => {
    wrap(
      <>
        <ExplainToggle />
        <ExplainLine text="El drawdown mide el peor momento." />
      </>,
    );
    expect(screen.queryByText("El drawdown mide el peor momento.")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("switch", { name: "Explicar" }));
    expect(screen.getByText("El drawdown mide el peor momento.")).toBeInTheDocument();
  });
});

describe("gráficas propias", () => {
  it("el medidor de drawdown expone su valor a lectores de pantalla", () => {
    wrap(<DrawdownGauge value={0.06} halt={0.15} hard={0.2} />);
    const meter = screen.getByRole("meter", { name: "Drawdown actual" });
    expect(meter).toHaveAttribute("aria-valuenow", "0.06");
    expect(screen.getByText("parada 15%")).toBeInTheDocument();
  });

  it("el mapa mensual escribe la cifra en cada celda", () => {
    wrap(<MonthlyHeatmap data={[{ mes: "2024-01", r: 2.5 }, { mes: "2024-02", r: -1 }]} />);
    expect(screen.getByText("2.5")).toBeInTheDocument();
    expect(screen.getByText("-1.0")).toBeInTheDocument();
  });
});
