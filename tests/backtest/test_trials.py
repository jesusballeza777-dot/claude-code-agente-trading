"""Registro obligatorio de pruebas (append-only) y comprobación del pre-registro congelado."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading.backtest.trials import (
    HEADER,
    PREREG_COMMIT,
    TRIALS_PATH,
    TrialRegistry,
    TrialRegistryError,
    TrialRow,
    row_dict,
    verify_frozen_preregistration,
)
from trading.data.holdout import REPO_ROOT

PERIOD = (datetime(2020, 1, 1, tzinfo=UTC), datetime(2024, 12, 31, tzinfo=UTC))


@pytest.fixture
def trials(tmp_path: Path) -> Path:
    path = tmp_path / "trials.csv"
    path.write_text(",".join(HEADER) + "\n", encoding="utf-8")
    return path


def _record(
    registry: TrialRegistry, results: Path, sample: str = "principal", **kw: object
) -> TrialRow:
    return registry.record_run(
        hypothesis=str(kw.get("hypothesis", "H1-v1")),
        variant="base",
        params={"L": 7},
        dataset_id="d" * 64,
        period=PERIOD,
        sample=sample,
        trades=3,
        result={"expectancy": 0.1},
        results_dir=results,
        prereg="p;aclaraciones=a",
    )


def test_the_repository_registry_has_the_expected_header() -> None:
    assert TRIALS_PATH.read_text(encoding="utf-8").split("\n", 1)[0] == ",".join(HEADER)


def test_record_run_writes_result_and_row(trials: Path, tmp_path: Path) -> None:
    registry = TrialRegistry(trials)
    row = _record(registry, tmp_path / "results")
    assert row.trial_id == "T0001"
    assert registry.rows()[0]["parametros_json"] == '{"L":7}'
    payload = json.loads((tmp_path / "results" / "T0001.json").read_text("utf-8"))
    assert payload == {"trial_id": "T0001", "expectancy": 0.1}
    assert row_dict(row)["n_operaciones"] == 3
    assert _record(registry, tmp_path / "results", "robustez").trial_id == "T0002"
    assert len(registry.principal_rows()) == 1


def test_registry_is_append_only(trials: Path, tmp_path: Path) -> None:
    registry = TrialRegistry(trials)
    _record(registry, tmp_path)
    trials.write_text(trials.read_text("utf-8").replace("H1-v1", "H9-v9"), encoding="utf-8")
    with pytest.raises(TrialRegistryError, match="cambió"):
        _record(registry, tmp_path)
    assert not (tmp_path / "T0002.json").exists()


def test_holdout_can_be_used_once_per_hypothesis(trials: Path, tmp_path: Path) -> None:
    registry = TrialRegistry(trials)
    _record(registry, tmp_path, "holdout")
    with pytest.raises(TrialRegistryError, match="una vez"):
        _record(registry, tmp_path, "holdout")
    _record(registry, tmp_path, "holdout", hypothesis="H2-v1")


def test_invalid_registry_or_sample_type(tmp_path: Path, trials: Path) -> None:
    with pytest.raises(TrialRegistryError, match="no existe"):
        TrialRegistry(tmp_path / "missing.csv")
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n", encoding="utf-8")
    with pytest.raises(TrialRegistryError, match="cabecera"):
        TrialRegistry(bad)
    no_newline = tmp_path / "nl.csv"
    no_newline.write_text(",".join(HEADER), encoding="utf-8")
    with pytest.raises(TrialRegistryError, match="salto"):
        TrialRegistry(no_newline)
    with pytest.raises(TrialRegistryError, match="tipo_muestra"):
        _record(TrialRegistry(trials), tmp_path, "optimizada")


def _has_commit(commit: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.skipif(
    not _has_commit(PREREG_COMMIT), reason="historial sin el commit del pre-registro"
)
def test_the_preregistration_is_still_frozen() -> None:
    clarifications = verify_frozen_preregistration()
    assert len(clarifications) == 40


def test_frozen_check_detects_rule_changes(tmp_path: Path) -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True
        ).stdout

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    git("config", "commit.gpgsign", "false")
    folder = tmp_path / "research" / "preregistration"
    folder.mkdir(parents=True)
    from trading.backtest import trials as module

    for name in (*module.RULE_FILES, module.CLARIFICATIONS):
        (folder / name).write_text("- **Estado:** borrador\nregla: 7\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-q", "-m", "pre-registro")
    frozen = git("rev-parse", "HEAD").strip()
    original_dir = module.PREREG_DIR
    try:
        module.PREREG_DIR = folder  # type: ignore[misc]
        module_root = module.REPO_ROOT
        module.REPO_ROOT = tmp_path  # type: ignore[misc]
        status = folder / module.RULE_FILES[0]
        status.write_text("- **Estado:** FUSIONADO\nregla: 7\n", encoding="utf-8")
        git("commit", "-q", "-am", "estado")
        assert verify_frozen_preregistration(tmp_path, frozen) == frozen  # aclaraciones intactas
        status.write_text("- **Estado:** FUSIONADO\nregla: 8\n", encoding="utf-8")
        with pytest.raises(TrialRegistryError, match="sin commit"):
            verify_frozen_preregistration(tmp_path, frozen)
        git("commit", "-q", "-am", "cambio de regla")
        with pytest.raises(TrialRegistryError, match="cambió"):
            verify_frozen_preregistration(tmp_path, frozen)
        with pytest.raises(TrialRegistryError, match="git"):
            verify_frozen_preregistration(tmp_path, "0" * 40)
    finally:
        module.PREREG_DIR = original_dir  # type: ignore[misc]
        module.REPO_ROOT = module_root  # type: ignore[misc]
