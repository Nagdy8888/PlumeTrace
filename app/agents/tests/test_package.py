"""Smoke tests for the agents package installation."""


def test_agents_package_imports_and_has_version() -> None:
    """The agents package is installed in the workspace and exposes its version."""
    import plumetrace_agents

    assert plumetrace_agents.__version__ == "0.1.0"
