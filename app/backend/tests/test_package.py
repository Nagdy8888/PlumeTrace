"""Smoke tests for the backend package installation."""


def test_backend_package_imports_and_has_version() -> None:
    """The backend package is installed in the workspace and exposes its version."""
    import plumetrace

    assert plumetrace.__version__ == "0.1.0"


def test_backend_can_import_agents_package() -> None:
    """The dependency direction backend -> agents is installable."""
    import plumetrace_agents

    assert plumetrace_agents.__version__ == "0.1.0"
