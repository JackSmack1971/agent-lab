"""Nox sessions for testing Agent Lab across Python versions."""

import nox

# Test against all supported Python versions
PYTHON_VERSIONS = ["3.11", "3.12", "3.13"]
LINT_PYTHON = "3.12"


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Run test suite with pytest."""
    session.install("-r", "requirements.lock")
    session.install("pytest>=8.0", "pytest-cov>=6.0", "pytest-asyncio>=0.24.0")
    session.install("pytest-xdist>=3.6", "pytest-randomly>=3.15", "pytest-mock>=3.14")
    session.install("hypothesis>=6.100")
    
    # Run tests with coverage
    session.run(
        "pytest",
        "-v",
        "-n", "auto",  # Parallel execution
        "--cov=agents",
        "--cov=services", 
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        *session.posargs,  # Allow passing extra args
    )


@nox.session(python=PYTHON_VERSIONS)
def tests_unit(session):
