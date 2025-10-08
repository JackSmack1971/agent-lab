# Python Unit Testing + `pytest`: A Genius-Level Playbook

> Scope: everything essential for world-class Python tests—design principles, `pytest` mastery, mocking, property-based tests, coverage, speed, reliability, and CI. Sources are cited inline.

---

## 1) First Principles (Designing Great Unit Tests)

* **Pure functions first; side effects last.** Keep units small, deterministic, and isolated; push I/O and global state to edges.
* **Arrange–Act–Assert (AAA).** One behavior per test; name tests by **behavior + context + expectation**.
* **Fast, hermetic, repeatable.** No external network, clock, or filesystem unless **explicitly mocked** or redirected to temp paths. Use built-ins like `tmp_path`, `monkeypatch`, `capsys`, `caplog`. ([pytest][1])

---

## 2) Project Layout & Discovery

```
your_project/
?? src/your_package/...
?? tests/
?  ?? unit/
?  ?? integration/
?  ?? conftest.py
?? pyproject.toml
```

* `pytest` auto-discovers files named `test_*.py` or `*_test.py` under the working dir; use this convention consistently. ([pytest][2])

---

## 3) `pytest` Configuration (central, reproducible)

Prefer **`pyproject.toml`** with a `[tool.pytest.ini_options]` table. (Other supported files: `pytest.ini` [highest precedence], `tox.ini [pytest]`, `setup.cfg [tool:pytest]`). ([pytest][3])

```toml
# pyproject.toml
[tool.pytest.ini_options]
minversion = "8.0"
addopts = [
  "-q",
  "--import-mode=importlib",   # modern import mode
  "--strict-markers",          # fail on unknown marks
  "--strict-config"            # fail on bad config
]
testpaths = ["tests"]
filterwarnings = [
  "error::DeprecationWarning"
]
markers = [
  "unit: fast, hermetic tests",
  "integration: touches filesystem/network/etc.",
  "slow: long-running scenarios"
]
```

> Why: `pyproject.toml` is officially supported and `--import-mode=importlib` is the recommended modern import mode. Registering markers here prevents `PytestUnknownMarkWarning`. ([pytest][3])

---

## 4) Fixtures: the Engine of `pytest`

**Core ideas**

* Tests **declare** needed fixtures by name; `pytest` resolves, runs, and injects them. Scopes: `function` (default), `class`, `module`, `package`, `session`. ([pytest][4])
* Use **temporary paths** for file I/O: `tmp_path` (per-test) and `tmp_path_factory` (session-wide). ([pytest][1])
* **Monkeypatch** globals/env/attrs without leakage via `monkeypatch`. ([pytest][5])
* Capture **stdout/stderr** with `capsys`, **logs** with `caplog`. ([pytest][6])

**Examples**

```python
# tests/conftest.py
import os, pytest

@pytest.fixture(scope="session")
def data_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    (d / "users.json").write_text("[]")
    return d

@pytest.fixture
def no_net(monkeypatch):
    def _block(*args, **kwargs):
        raise RuntimeError("network disabled")
    monkeypatch.setattr("socket.socket.connect", _block)
```

---

## 5) Parametrization (Generate Many Focused Cases)

* Use `@pytest.mark.parametrize` to run a test over multiple inputs; customize readable IDs; route parameters through fixtures via **`indirect=True`** when setup should happen at runtime. ([pytest][7])

```python
import pytest

CASES = [(2, 3, 6), (10, 0, 0), (-2, -3, 6)]
@pytest.mark.parametrize(("a","b","expected"), CASES, ids=["2x3","10x0","-2x-3"])
def test_mul(a, b, expected):
    assert a*b == expected

@pytest.fixture
def tripled(request):           # becomes request.param * 3
    return request.param * 3

@pytest.mark.parametrize("tripled", ["a", "b"], indirect=True)
def test_indirect_fixture(tripled):
    assert len(tripled) == 3
```

> Tip: Use marks/IDs on individual parameter sets for edge cases; see docs for indirect parametrization and IDs. ([pytest][8])

---

## 6) Skips, Expected Failures, and Markers

* **Skip** when a prerequisite is absent (e.g., OS, optional dep). **Xfail** when a known bug exists; flips to fail if it starts passing unexpectedly (configure with `strict=True` when appropriate). ([pytest][9])
* Register **custom markers** in config to avoid warnings and enable `-m` selection. ([pytest][10])

```python
import sys, pytest

@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_win_only(): ...

@pytest.mark.xfail(reason="bug #123", strict=True)
def test_known_bug(): ...
```

---

## 7) Mocking: `unittest.mock` + `pytest-mock`

* The **standard library** `unittest.mock` provides `Mock`, `patch`, `AsyncMock`, call assertions, autospeccing, etc. ([Python documentation][11])
* The **`pytest-mock` plugin** adds a `mocker` fixture that streamlines patching and is idiomatic in `pytest`. ([pytest-mock.readthedocs.io][12])

```python
# stdlib mock, direct
from unittest.mock import patch
with patch("module.api.fetch", return_value={"ok": True}) as fetch:
    assert module.func() == "OK"
    fetch.assert_called_once()

# pytest-mock
def test_ok(mocker):
    mocker.patch("module.api.fetch", return_value={"ok": True})
    assert module.func() == "OK"
```

> Prefer patching **where used**, not where defined; prefer autospeccing for API safety; use `monkeypatch` for environment/attributes. ([pytest][5])

---

## 8) Filesystem, Output, and Logging

* **Filesystem**: write to `tmp_path`; for session-wide heavy assets use `tmp_path_factory`. ([pytest][1])
* **Stdout/Stderr**: `capsys.readouterr()` for CLI verification. **Logs**: assert on `caplog.records` or `caplog.text`. ([pytest][6])

---

## 9) Property-Based Testing (Find Edge Cases Automatically)

Adopt **Hypothesis** to assert *properties* across many randomized inputs—excellent for parsers, math, data validation, and protocol invariants. Seamlessly integrates with `pytest`. ([hypothesis.readthedocs.io][13])

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_reverse_twice_is_identity(xs):
    assert list(reversed(list(reversed(xs)))) == xs
```

---

## 10) Coverage: Measuring What Tests Execute

* Use **coverage.py** for line and **branch** coverage; branch coverage detects missing decision paths. ([coverage.readthedocs.io][14])
* Integrate via **`pytest-cov`** (`--cov=src --cov-report=term-missing`); works with `xdist` and can record **contexts**. ([pytest-cov.readthedocs.io][15])

**Config (example)**

```toml
# pyproject.toml
[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
fail_under = 90
show_missing = true
```

([coverage.readthedocs.io][16])

---

## 11) Mutation Testing: Verify Test *Quality*, Not Just Quantity

Even 100% coverage can miss bugs. Run **mutation testing** (e.g., `mutmut`) to ensure assertions truly guard behavior; killed mutants mean effective tests. ([mutmut.readthedocs.io][17])

```bash
pip install mutmut
mutmut run
mutmut results
```

---

## 12) Scale & Speed: Parallelism, Order, and Flakiness

* **Parallel**: `pytest-xdist` to distribute tests across CPUs: `pytest -n auto`. ([pytest-xdist.readthedocs.io][18])
* **Order-independence**: `pytest-randomly` shuffles test order & reseeds RNGs; fixes order-coupling bugs early. ([PyPI][19])
* **Hermetic randomness**: explicitly seed your own RNGs or let `pytest-randomly` manage them; keep tests deterministic.

---

## 13) CLI Essentials (Day-to-Day)

```bash
pytest -q                                   # quiet, fast feedback
pytest -k "parser and not slow" -vv         # expression-based selection
pytest -m "unit"                            # marker selection
pytest tests/unit/test_parser.py::TestX::test_y
pytest -x --maxfail=1                       # fail fast
pytest -n auto                              # parallel via xdist
pytest --lf                                 # last-failed
pytest --cov=src --cov-report=term-missing  # coverage
pytest --durations=10                       # slowest tests
pytest --pdb -x                             # drop into debugger on first fail
```

(Discovery and invocation rules: official docs). ([pytest][2])

---

## 14) CI Orchestration Across Python Versions

* **tox** and **nox** manage multi-env test matrices locally and in CI; `nox` uses Python code, `tox` uses INI. ([tox.wiki][20])

**`noxfile.py` (concise)**

```python
import nox

@nox.session(python=["3.10","3.11","3.12","3.13"])
def tests(session):
    session.install("-e", ".")
    session.install("pytest","pytest-cov")
    session.run("pytest","-q","--cov=src")
```

([nox.thea.codes][21])

**`tox.ini` (alt.)**

```ini
[tox]
envlist = py310,py311,py312,py313
[testenv]
deps = pytest
commands = pytest -q
```

([tox.wiki][22])

---

## 15) Patterns, Anti-Patterns, and Heuristics

**Do**

* Keep tests **small and specific**; one assertion concept per test.
* Use **fixtures over setUp/tearDown**; share via `conftest.py`.
* Prefer **parametrization** over loops/conditionals within tests. ([pytest][7])
* Mock **behavior at boundaries** (network, time, OS), not concrete internals. Use `mocker`/`patch` with autospeccing. ([pytest-mock.readthedocs.io][12])
* Assert **outputs, state, and interactions** (e.g., `assert_called_once_with`).

**Avoid**

* Hidden dependencies (env vars, real network/time/files).
* Test order dependencies; fix with `pytest-randomly`. ([PyPI][19])
* Over-mocking core logic; favor property-based tests for invariants. ([hypothesis.readthedocs.io][13])

---

## 16) Example: End-to-End of Common Concerns

```python
# src/app/user.py
def age_band(age: int) -> str:
    if age < 0:
        raise ValueError("age must be >= 0")
    return "child" if age < 13 else "adult"
```

```python
# tests/unit/test_user.py
import pytest

CASES = [(-1, ValueError), (0, None), (12, None), (13, None)]
IDS = ["neg->ValueError", "0->child", "12->child", "13->adult"]

@pytest.mark.parametrize(("age", "exc"), CASES, ids=IDS)
def test_age_band(age, exc):
    from app.user import age_band
    if exc:
        with pytest.raises(exc):
            age_band(age)
    else:
        out = age_band(age)
        assert out in {"child","adult"}
```

* Uses parametrization, explicit IDs, and exception assertions—the canonical patterns. ([pytest][7])

---

## 17) Troubleshooting: Fast Answers

* **“Unknown mark: integration” warnings** ? register markers in config or enable `--strict-markers` to catch typos. ([Python Basics][23])
* **Tests relying on cwd** ? pass paths explicitly; prefer `tmp_path`. ([pytest][1])
* **Flaky tests** ? remove time/network randomness; use `monkeypatch` and `pytest-randomly`. ([pytest][5])
* **Slow suite** ? profile slowest tests (`--durations=10`); parallelize (`-n auto`); lift heavyweight setup to session fixtures. ([pytest-xdist.readthedocs.io][18])

---

## 18) Minimal “Genius” Starter Kit (drop-in)

**`pyproject.toml`**

```toml
[project]
name = "yourpkg"
version = "0.0.0"

[tool.pytest.ini_options]
minversion = "8.0"
addopts = ["-q", "--import-mode=importlib", "--strict-markers", "--strict-config"]
testpaths = ["tests"]
markers = ["unit", "integration", "slow"]
```

([pytest][3])

**`requirements-dev.txt`**

```
pytest
pytest-cov
pytest-xdist
pytest-randomly
pytest-mock
hypothesis
```

(Plugins list is tracked centrally by pytest; consult when you need specialized tooling.) ([pytest][24])

---

## 19) Mastery Checklist

* [ ] All test files discover under `tests/`, with clear naming. ([pytest][2])
* [ ] Markers registered; unit/integration selective runs work. ([Python Basics][23])
* [ ] Heavy I/O under `tmp_path` or `tmp_path_factory`; no real network unless explicitly opt-in. ([pytest][1])
* [ ] Parametrization for edge cases; property-based tests for invariants. ([pytest][7])
* [ ] Coverage with **branch** enabled; threshold enforced; mutation tests in CI for critical modules. ([coverage.readthedocs.io][25])
* [ ] Suite is **order-independent** and **parallel-safe**. ([PyPI][19])
* [ ] Multi-Python CI via `nox`/`tox`. ([nox.thea.codes][26])

---

## 20) Reference Index (fast lookup)

* **Core**: Discovery & invocation; Fixtures; Parametrize; Mark/Skip/Xfail; Built-in fixtures; Logging; Tmp paths. ([pytest][2])
* **Mocking**: `unittest.mock`; `pytest-mock`. ([Python documentation][11])
* **Config**: `pyproject.toml` / `pytest.ini`; importlib mode; marker registration. ([pytest][3])
* **Coverage**: coverage.py; branch coverage; pytest-cov. ([coverage.readthedocs.io][14])
* **Scale**: xdist; randomly. ([pytest-xdist.readthedocs.io][18])
* **PBT**: Hypothesis. ([hypothesis.readthedocs.io][13])
* **Orchestration**: nox; tox. ([nox.thea.codes][26])

---

### Want me to tailor this to your current repo?

I can generate a **repo-specific test blueprint** (markers, fixtures, parametrization targets, coverage+mutation plan, xdist safety, and a `noxfile.py`) mapped to your modules and current gaps.

[1]: https://docs.pytest.org/en/stable/how-to/tmp_path.html?utm_source=chatgpt.com "How to use temporary directories and files in tests"
[2]: https://docs.pytest.org/en/stable/how-to/usage.html?utm_source=chatgpt.com "How to invoke pytest"
[3]: https://docs.pytest.org/en/stable/reference/customize.html?utm_source=chatgpt.com "pytest.ini - Configuration"
[4]: https://docs.pytest.org/en/stable/how-to/fixtures.html?utm_source=chatgpt.com "How to use fixtures - pytest documentation"
[5]: https://docs.pytest.org/en/stable/how-to/monkeypatch.html?utm_source=chatgpt.com "How to monkeypatch/mock modules and environments"
[6]: https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html?utm_source=chatgpt.com "How to capture stdout/stderr output"
[7]: https://docs.pytest.org/en/stable/how-to/parametrize.html?utm_source=chatgpt.com "How to parametrize fixtures and test functions"
[8]: https://docs.pytest.org/en/stable/example/parametrize.html?utm_source=chatgpt.com "Parametrizing tests"
[9]: https://docs.pytest.org/en/stable/how-to/skipping.html?utm_source=chatgpt.com "How to use skip and xfail to deal with tests that cannot ..."
[10]: https://docs.pytest.org/en/stable/how-to/mark.html?utm_source=chatgpt.com "How to mark test functions with attributes"
[11]: https://docs.python.org/3/library/unittest.mock.html?utm_source=chatgpt.com "unittest.mock — mock object library"
[12]: https://pytest-mock.readthedocs.io/?utm_source=chatgpt.com "pytest-mock documentation"
[13]: https://hypothesis.readthedocs.io/en/latest/quickstart.html?utm_source=chatgpt.com "Quickstart - Hypothesis 6.140.3 documentation"
[14]: https://coverage.readthedocs.io/?utm_source=chatgpt.com "Coverage.py — Coverage.py 7.10.7 documentation"
[15]: https://pytest-cov.readthedocs.io/?utm_source=chatgpt.com "pytest-cov 7.0.0 documentation"
[16]: https://coverage.readthedocs.io/en/7.10.7/config.html?utm_source=chatgpt.com "Configuration reference — Coverage.py 7.10.7 documentation"
[17]: https://mutmut.readthedocs.io/?utm_source=chatgpt.com "mutmut - python mutation tester — mutmut documentation"
[18]: https://pytest-xdist.readthedocs.io/?utm_source=chatgpt.com "pytest-xdist — pytest-xdist documentation"
[19]: https://pypi.org/project/pytest-randomly/?utm_source=chatgpt.com "pytest-randomly"
[20]: https://tox.wiki/en/latest/user_guide.html?utm_source=chatgpt.com "User Guide"
[21]: https://nox.thea.codes/en/stable/tutorial.html?utm_source=chatgpt.com "Tutorial — Nox 2025.5.1 documentation"
[22]: https://tox.wiki/en/3.27.1/example/pytest.html?utm_source=chatgpt.com "pytest and tox — tox 3.27.1 documentation"
[23]: https://python-basics-tutorial.readthedocs.io/en/latest/test/pytest/markers.html?utm_source=chatgpt.com "Markers - Python Basics 25.1.0"
[24]: https://docs.pytest.org/en/stable/reference/plugin_list.html?utm_source=chatgpt.com "Pytest Plugin List"
[25]: https://coverage.readthedocs.io/en/7.10.7/branch.html?utm_source=chatgpt.com "Branch coverage measurement"
[26]: https://nox.thea.codes/?utm_source=chatgpt.com "Welcome to Nox — Nox 2025.5.1 documentation"
