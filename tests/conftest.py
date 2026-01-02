"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import MagicMock, patch
from typing import Generator


@pytest.fixture
def mock_tshark_path() -> str:
    """Mock tshark path for testing."""
    return "tshark"


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run for testing."""
    mock_run = MagicMock()
    mock_run.return_value.stdout = "test output"
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 0
    monkeypatch.setattr("subprocess.run", mock_run)
    return mock_run


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for testing."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.text = "192.168.1.1\n10.0.0.1\n"
        mock_response.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        yield mock_client

