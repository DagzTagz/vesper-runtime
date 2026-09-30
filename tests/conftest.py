"""Keep tests off the operator's workspace and off the network."""

import pytest


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VESPER_WORKSPACE", raising=False)
