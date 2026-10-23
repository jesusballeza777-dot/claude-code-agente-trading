"""Fixtures de la API: repositorio sintético con datos y cliente sin autenticación."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api_fixtures import build_repo, client_for


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return build_repo(tmp_path, with_data=True)


@pytest.fixture
def client(repo: Path) -> TestClient:
    return client_for(repo)
