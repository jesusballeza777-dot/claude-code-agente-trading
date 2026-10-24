import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

afterEach(() => vi.restoreAllMocks());

function mockFetch(status: number, body: unknown) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
    ),
  );
}

describe("cliente de la API", () => {
  it("las lecturas no envían la cabecera anti-CSRF", async () => {
    const spy = mockFetch(200, { ok: true });
    await expect(api.get("/api/estado")).resolves.toEqual({ ok: true });
    const headers = spy.mock.calls[0]?.[1]?.headers as Record<string, string>;
    expect(headers["X-Brujula"]).toBeUndefined();
  });

  it("las escrituras llevan la cabecera anti-CSRF y JSON", async () => {
    const spy = mockFetch(200, { id: "1" });
    await api.post("/api/diario/notas", { texto: "hola" });
    const init = spy.mock.calls[0]?.[1];
    const headers = init?.headers as Record<string, string>;
    expect(init?.method).toBe("POST");
    expect(headers["X-Brujula"]).toBe("1");
    expect(headers["Content-Type"]).toBe("application/json");
    await api.delete("/api/sesion");
    expect((spy.mock.calls[1]?.[1]?.headers as Record<string, string>)["X-Brujula"]).toBe("1");
  });

  it("convierte los errores en ApiError con el detalle del backend", async () => {
    mockFetch(422, { detail: "los importes deben ser positivos" });
    const error = await api.get("/api/riesgo/calculadora").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(422);
    expect((error as ApiError).message).toBe("los importes deben ser positivos");
  });
});
