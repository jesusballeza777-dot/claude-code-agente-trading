"""Centro de Mando: API de solo lectura respecto al dinero (ADR-014 y ADR-015).

La única escritura es la de las notas del diario (no toca riesgo ni ejecución) y la sesión.
No hay ninguna ruta que envíe órdenes, active LIVE_TRADING, cree claves o cambie límites; un
test lo comprueba recorriendo todas las rutas.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Final

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from trading.api import copilot
from trading.api.reports import REPORTS, ReportService
from trading.api.security import SECURITY_HEADERS, SessionSigner, verify_password, verify_totp
from trading.api.services import Services, demo_decisions
from trading.api.settings import ApiSettings

SESSION_COOKIE: Final = "brujula_sesion"
CSRF_HEADER: Final = "x-brujula"
WRITE_ROUTES: Final = frozenset(
    {("POST", "/api/sesion"), ("DELETE", "/api/sesion"), ("POST", "/api/diario/notas")}
)
PUBLIC_ROUTES: Final = frozenset({("GET", "/api/sesion"), ("POST", "/api/sesion")})


class Login(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    totp: str = Field(pattern=r"^\d{6}$")


class Note(BaseModel):
    referencia: str = Field(default="", max_length=80)
    texto: str = Field(min_length=1, max_length=2000)


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    settings = settings or ApiSettings.from_env()
    services = Services(settings.repo_root, settings.data_root, settings.app_state)
    reports = ReportService(services, settings.app_state)
    signer = SessionSigner(settings.session_key) if settings.auth_enabled else None
    failed_logins: list[float] = []
    app = FastAPI(
        title="Centro de Mando",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def guard(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path, method = request.url.path, request.method
        if path.startswith("/api/"):
            if method not in ("GET", "HEAD") and request.headers.get(CSRF_HEADER) != "1":
                return _headers(JSONResponse({"detalle": "falta la cabecera anti-CSRF"}, 403))
            needs_session = (method, path) not in PUBLIC_ROUTES
            if signer and needs_session and not signer.valid(request.cookies.get(SESSION_COOKIE)):
                return _headers(JSONResponse({"detalle": "inicia sesión"}, 401))
        response = await call_next(request)
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return _headers(response)

    # --- sesión --------------------------------------------------------------------------------

    @app.get("/api/sesion")
    def session_status(request: Request) -> dict[str, Any]:
        active = signer is None or signer.valid(request.cookies.get(SESSION_COOKIE))
        return {"autenticacion": settings.auth_enabled, "activa": active}

    @app.post("/api/sesion")
    def login(body: Login, response: Response) -> dict[str, Any]:
        if signer is None:
            return {"autenticacion": False, "activa": True}
        now = time.time()
        failed_logins[:] = [t for t in failed_logins if now - t < 300]
        if len(failed_logins) >= 5:
            raise HTTPException(429, "demasiados intentos; espera 5 minutos")
        if not (
            verify_password(body.password, settings.password_hash)
            and verify_totp(settings.totp_secret, body.totp)
        ):
            failed_logins.append(now)
            raise HTTPException(401, "contraseña o código incorrectos")
        response.set_cookie(
            SESSION_COOKIE,
            signer.issue(),
            httponly=True,
            samesite="strict",
            secure=settings.secure_cookie,
            max_age=12 * 3600,
        )
        return {"autenticacion": True, "activa": True}

    @app.delete("/api/sesion")
    def logout(response: Response) -> dict[str, Any]:
        response.delete_cookie(SESSION_COOKIE)
        return {"activa": False}

    # --- lectura -------------------------------------------------------------------------------

    @app.get("/api/estado")
    def status() -> dict[str, Any]:
        return services.status()

    @app.get("/api/hoy")
    def today() -> dict[str, Any]:
        return services.today()

    @app.get("/api/laboratorio")
    def lab() -> dict[str, Any]:
        return services.lab_overview()

    @app.get("/api/laboratorio/{hypothesis}")
    def lab_detail(hypothesis: str) -> dict[str, Any]:
        detail = services.lab_detail(hypothesis)
        if detail is None:
            raise HTTPException(404, "hipótesis sin resultados")
        return detail

    @app.get("/api/mercado/simbolos")
    def symbols() -> dict[str, Any]:
        return services.symbols()

    @app.get("/api/mercado/velas")
    def candles(
        simbolo: str = Query(pattern=r"^[A-Z0-9]{2,20}USDT$"),
        intervalo: str = Query("4h", pattern=r"^(4h|1d)$"),
        dias: int = Query(120, ge=7, le=2000),
    ) -> dict[str, Any]:
        try:
            return services.candles(simbolo, intervalo, dias)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/mercado/regimenes")
    def regimes() -> dict[str, Any]:
        return services.regimes()

    @app.get("/api/mercado/correlaciones")
    def correlations() -> dict[str, Any]:
        return services.correlations()

    @app.get("/api/riesgo/limites")
    def limits() -> dict[str, Any]:
        return services.limits()

    @app.get("/api/riesgo/calculadora")
    def calculator(
        simbolo: str = Query("BTCUSDT", pattern=r"^[A-Z0-9]{2,20}USDT$"),
        lado: str = Query("LONG", pattern=r"^(LONG|SHORT)$"),
        entrada: str = Query(max_length=30),
        stop: str = Query(max_length=30),
        apalancamiento: str = Query("3", max_length=10),
        capital: str = Query("1500", max_length=20),
        mercado: str = Query("PERPETUAL", pattern=r"^(PERPETUAL|SPOT)$"),
    ) -> dict[str, Any]:
        try:
            return services.calculator(
                symbol=simbolo,
                side=lado,
                entry=entrada,
                stop=stop,
                exchange_leverage=apalancamiento,
                capital=capital,
                market=mercado,
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/riesgo/vetos")
    def vetoes() -> dict[str, Any]:
        return services.veto_history()

    @app.get("/api/en-vivo")
    def live() -> dict[str, Any]:
        return services.live()

    @app.get("/api/decisiones")
    def decisions() -> dict[str, Any]:
        return demo_decisions()

    @app.get("/api/diario")
    def journal() -> dict[str, Any]:
        return services.journal()

    @app.post("/api/diario/notas")
    def add_note(note: Note) -> dict[str, Any]:
        try:
            return services.add_note(note.referencia, note.texto)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/proyecto")
    def project() -> dict[str, Any]:
        return services.project()

    @app.get("/api/glosario")
    def glossary() -> dict[str, Any]:
        return {
            "copiloto": copilot.NAME,
            "terminos": copilot.GLOSSARY,
            "vacios": copilot.EMPTY_STATES,
        }

    @app.get("/api/reportes")
    def report_list() -> dict[str, Any]:
        return reports.catalog()

    @app.get("/api/reportes/{kind}/{fmt}")
    def report(kind: str, fmt: str, hipotesis: str = Query("H2-v1", max_length=20)) -> Response:
        if (kind, fmt) not in REPORTS:
            raise HTTPException(404, "reporte desconocido")
        try:
            content, media, filename = reports.build(kind, fmt, hypothesis=hipotesis)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        return Response(
            content,
            media_type=media,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    _mount_web(app, settings.web_dist)
    return app


def _mount_web(app: FastAPI, dist: Path) -> None:
    """Sirve el frontend compilado (si existe) con vuelta a index.html para las rutas del SPA."""
    if not (dist / "index.html").exists():
        return
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")


def _headers(response: Response) -> Response:
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response
