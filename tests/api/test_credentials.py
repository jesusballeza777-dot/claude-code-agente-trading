"""Generador de credenciales del Centro de Mando (ADR-015)."""

# ruff: noqa: S105 - contraseña de prueba, no real

import io

import pytest

from trading.api import credentials
from trading.api.security import totp, verify_password, verify_totp
from trading.api.settings import ApiSettings

PASSWORD = "frase-de-prueba-solo-para-tests"


def test_generated_values_satisfy_the_settings() -> None:
    values = credentials.generate(PASSWORD)
    assert verify_password(PASSWORD, values["TRADING_API_PASSWORD_HASH"])
    secret = values["TRADING_API_TOTP_SECRET"]
    assert verify_totp(secret, totp(secret, 1_000_000.0), now=1_000_000.0)
    settings = ApiSettings(
        auth_enabled=True,
        password_hash=values["TRADING_API_PASSWORD_HASH"],
        totp_secret=secret,
        session_key=values["TRADING_API_SESSION_KEY"].encode("utf-8"),
    )
    assert settings.auth_enabled
    assert credentials.generate(PASSWORD) != values  # sal, TOTP y clave nuevos cada vez


def test_short_password_is_rejected() -> None:
    with pytest.raises(ValueError, match="al menos 12"):
        credentials.generate("corta")


def test_main_prints_yaml_and_the_otpauth_uri() -> None:
    out = io.StringIO()
    assert credentials.main(ask=lambda _prompt: PASSWORD, out=out) == 0
    lines = out.getvalue().splitlines()
    names = [line.split(":", 1)[0] for line in lines if line.startswith("TRADING_API_")]
    assert names == [
        "TRADING_API_PASSWORD_HASH",
        "TRADING_API_TOTP_SECRET",
        "TRADING_API_SESSION_KEY",
    ]
    assert "otpauth://totp/Centro%20de%20Mando%3Apropietario?secret=" in lines[-1]


def test_main_refuses_mismatch_and_short_passwords(capsys: pytest.CaptureFixture[str]) -> None:
    answers = iter([PASSWORD, "otra-cosa-distinta-larga"])
    out = io.StringIO()
    assert credentials.main(ask=lambda _prompt: next(answers), out=out) == 1
    assert credentials.main(ask=lambda _prompt: "corta", out=out) == 1
    assert out.getvalue() == ""
    assert "no se generó nada" in capsys.readouterr().err
