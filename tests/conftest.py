import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "ollama: mark test as an Ollama integration test"
    )
