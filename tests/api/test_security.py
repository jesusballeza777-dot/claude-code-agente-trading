"""Autenticación de un solo usuario, TOTP, sesiones y configuración segura."""

# ruff: noqa: S106 - contraseñas y secretos de prueba, no reales

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_fixtures import build_repo
from trading.api.app import create_app
from trading.api.security import SessionSigner, hash_password, totp, verify_password, verify_totp
from trading.api.settings import ApiSettings, InsecureConfigError

RFC_SECRET = base64.b32encode(b"12345678901234567890").decode()
KEY = b"k" * 32


def test_password_hash_round_trip() -> None:
    stored = hash_password("correcta caballo batería", salt=b"s" * 16)
    assert stored.startswith("scrypt$32768$8$1$")
    assert verify_password("correcta caballo batería", stored)
    assert not verify_password("otra", stored)
    assert not verify_password("x", "md5$1$2")
    assert not verify_password("x", "basura")


def test_totp_matches_rfc_6238() -> None:
    assert totp(RFC_SECRET, 59, digits=8) == "94287082"
    assert totp(RFC_SECRET, 1111111109, digits=8) == "07081804"
    code = totp(RFC_SECRET, 1_000_000)
    assert verify_totp(RFC_SECRET, code, now=1_000_000 + 25)
    assert not verify_totp(RFC_SECRET, code, now=1_000_000 + 95)


def test_session_tokens() -> None:
    signer = SessionSigner(KEY)
    token = signer.issue(now=1000)
    assert signer.valid(token, now=1001)
    assert not signer.valid(token, now=1000 + 13 * 3600)
    assert not signer.valid(token[:-1] + ("0" if token[-1] != "0" else "1"), now=1001)
    assert not SessionSigner(b"o" * 32).valid(token, now=1001)
    assert not signer.valid(None)
    assert not signer.valid("a.b.c")
    forged = "propietario.notanumber.x"
    assert not signer.valid(f"{forged}.{signer._sign(forged)}")


def test_settings_refuse_insecure_configurations(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(InsecureConfigError, match="SOPS"):
        ApiSettings(auth_enabled=True)
    with pytest.raises(InsecureConfigError, match="32 bytes"):
        ApiSettings(password_hash="h", totp_secret="t", session_key=b"corta")
    with pytest.raises(InsecureConfigError, match=r"127\.0\.0\.1"):
        ApiSettings(auth_enabled=False, host="0.0.0.0")  # noqa: S104 - caso que debe fallar
    monkeypatch.setenv("TRADING_API_AUTH", "disabled")
    monkeypatch.setenv("TRADING_API_PORT", "8123")
    settings = ApiSettings.from_env()
    assert (settings.auth_enabled, settings.port, settings.host) == (False, 8123, "127.0.0.1")
    assert "password_hash" not in repr(
        ApiSettings(password_hash="h", totp_secret="t", session_key=KEY)
    )


def test_login_flow(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, with_data=False)
    settings = ApiSettings(
        password_hash=hash_password("secreto"),
        totp_secret=RFC_SECRET,
        session_key=KEY,
        repo_root=repo,
        data_root=repo / "data",
        app_state=repo / "app",
        web_dist=repo / "dist",
    )
    client = TestClient(create_app(settings))
    headers = {"x-brujula": "1"}
    assert client.get("/api/estado").status_code == 401
    assert client.get("/api/sesion").json() == {"autenticacion": True, "activa": False}
    assert (
        client.post("/api/sesion", json={"password": "secreto", "totp": "123456"}).status_code
        == 403
    )
    bad = client.post("/api/sesion", json={"password": "mal", "totp": "123456"}, headers=headers)
    assert bad.status_code == 401
    import time

    good = client.post(
        "/api/sesion",
        json={"password": "secreto", "totp": totp(RFC_SECRET, time.time())},
        headers=headers,
    )
    assert good.status_code == 200
    assert "httponly" in good.headers["set-cookie"].lower()
    assert "samesite=strict" in good.headers["set-cookie"].lower()
    assert client.get("/api/estado").status_code == 200
    assert client.delete("/api/sesion", headers=headers).json() == {"activa": False}
    for _ in range(5):
        client.post("/api/sesion", json={"password": "mal", "totp": "000000"}, headers=headers)
    assert (
        client.post(
            "/api/sesion", json={"password": "mal", "totp": "000000"}, headers=headers
        ).status_code
        == 429
    )


def test_login_without_auth_is_a_no_op(tmp_path: Path) -> None:
    repo = build_repo(tmp_path, with_data=False)
    settings = ApiSettings(
        auth_enabled=False, repo_root=repo, data_root=repo / "data", app_state=repo / "app"
    )
    client = TestClient(create_app(settings))
    response = client.post(
        "/api/sesion", json={"password": "x", "totp": "000000"}, headers={"x-brujula": "1"}
    )
    assert response.json() == {"autenticacion": False, "activa": True}
