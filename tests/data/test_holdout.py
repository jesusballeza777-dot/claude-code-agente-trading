"""Guardia del holdout (CLAUDE.md regla 7; auditoría A-01)."""

import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from trading.data.holdout import (
    HOLDOUT_START,
    UNLOCK_PATH,
    HoldoutSealedError,
    ensure_research_window,
    git_signature_ok,
    load_unlock,
    research_cutoff,
)

START = datetime(2020, 1, 1, tzinfo=UTC)
VALID = """\
fecha_utc = 2027-03-01T12:00:00Z
hipotesis = ["H1", "H2"]
prereg_commit = "4614d659247e57ef6f01614b4986c125fe5468f9"
aprobado_por = "propietario"
motivo = "gate de la F4"
"""


def _always(ok: bool) -> Callable[[Path], bool]:
    return lambda _path: ok


def test_the_repository_has_no_unlock_file() -> None:
    assert not UNLOCK_PATH.exists()


def test_research_period_is_allowed() -> None:
    ensure_research_window(START, HOLDOUT_START)


@pytest.mark.parametrize("extra", [timedelta(milliseconds=1), timedelta(days=400)])
def test_holdout_is_sealed_without_authorization(tmp_path: Path, extra: timedelta) -> None:
    with pytest.raises(HoldoutSealedError, match="holdout"):
        ensure_research_window(START, HOLDOUT_START + extra, unlock_path=tmp_path / "no.toml")


def test_signed_authorization_opens_only_the_listed_hypotheses(tmp_path: Path) -> None:
    unlock = tmp_path / "holdout_unlock.toml"
    unlock.write_text(VALID, encoding="utf-8")
    end = HOLDOUT_START + timedelta(days=30)
    ensure_research_window(
        START, end, hypothesis="H1", unlock_path=unlock, signature_ok=_always(True)
    )
    with pytest.raises(HoldoutSealedError, match="H4"):
        ensure_research_window(
            START, end, hypothesis="H4", unlock_path=unlock, signature_ok=_always(True)
        )
    with pytest.raises(HoldoutSealedError, match="None"):
        ensure_research_window(START, end, unlock_path=unlock, signature_ok=_always(True))


def test_unsigned_authorization_is_rejected(tmp_path: Path) -> None:
    unlock = tmp_path / "holdout_unlock.toml"
    unlock.write_text(VALID, encoding="utf-8")
    with pytest.raises(HoldoutSealedError, match="firmado"):
        load_unlock(unlock, signature_ok=_always(False))


def test_loaded_authorization(tmp_path: Path) -> None:
    unlock = tmp_path / "holdout_unlock.toml"
    unlock.write_text(VALID, encoding="utf-8")
    loaded = load_unlock(unlock, signature_ok=_always(True))
    assert loaded is not None
    assert loaded.hipotesis == {"H1", "H2"}
    assert loaded.fecha_utc == datetime(2027, 3, 1, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('motivo = "gate de la F4"', 'motivo = "gate de la F4"\nextra = 1'),
        ('motivo = "gate de la F4"', 'motivo = "  "'),
        ("fecha_utc = 2027-03-01T12:00:00Z", "fecha_utc = 2027-03-01T12:00:00"),
        ('hipotesis = ["H1", "H2"]', "hipotesis = []"),
        ('hipotesis = ["H1", "H2"]', 'hipotesis = "H1"'),
        ('"4614d659247e57ef6f01614b4986c125fe5468f9"', '"4614d65"'),
        ("aprobado_por = ", "aprobado_por = = "),
    ],
)
def test_malformed_authorization_is_an_error(tmp_path: Path, old: str, new: str) -> None:
    unlock = tmp_path / "holdout_unlock.toml"
    unlock.write_text(VALID.replace(old, new), encoding="utf-8")
    with pytest.raises(HoldoutSealedError):
        load_unlock(unlock, signature_ok=_always(True))


def test_research_cutoff(tmp_path: Path) -> None:
    assert research_cutoff(unlock_path=tmp_path / "no.toml") == HOLDOUT_START
    unlock = tmp_path / "holdout_unlock.toml"
    unlock.write_text(VALID, encoding="utf-8")
    assert research_cutoff(hypothesis="H2", unlock_path=unlock, signature_ok=_always(True)) is None


def test_window_validation() -> None:
    with pytest.raises(ValueError, match="zona"):
        ensure_research_window(datetime(2020, 1, 1), HOLDOUT_START)  # noqa: DTZ001
    with pytest.raises(ValueError, match="anterior"):
        ensure_research_window(HOLDOUT_START, START)


# --- firma con git ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    return tmp_path


def test_signature_check_without_allowed_signers_is_false(repo: Path) -> None:
    unlock = repo / "holdout_unlock.toml"
    unlock.write_text(VALID, encoding="utf-8")
    assert git_signature_ok(unlock, repo / "allowed_signers") is False


def test_unsigned_or_modified_files_do_not_pass(repo: Path) -> None:
    signers = repo / "allowed_signers"
    signers.write_text("", encoding="utf-8")
    unlock = repo / "holdout_unlock.toml"
    unlock.write_text(VALID, encoding="utf-8")
    assert git_signature_ok(unlock, signers) is False  # sin versionar
    _git(repo, "add", "holdout_unlock.toml")
    _git(repo, "commit", "-q", "-m", "sin firma")
    assert git_signature_ok(unlock, signers) is False  # versionado, sin firma
    unlock.write_text(VALID + "# cambio\n", encoding="utf-8")
    assert git_signature_ok(unlock, signers) is False  # cambios locales


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen no disponible")
def test_a_commit_signed_by_an_allowed_key_passes(repo: Path) -> None:
    key = repo.parent / "owner_key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
        capture_output=True,
    )
    public = key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    signers = repo.parent / "allowed_signers"
    signers.write_text(f"test@example.com {public}\n", encoding="utf-8")
    _git(repo, "config", "gpg.format", "ssh")
    _git(repo, "config", "user.signingkey", str(key))
    unlock = repo / "holdout_unlock.toml"
    unlock.write_text(VALID, encoding="utf-8")
    _git(repo, "add", "holdout_unlock.toml")
    _git(repo, "commit", "-q", "-S", "-m", "autorización firmada")
    assert git_signature_ok(unlock, signers) is True
    other = repo.parent / "other_signers"
    other.write_text("", encoding="utf-8")
    assert git_signature_ok(unlock, other) is False
