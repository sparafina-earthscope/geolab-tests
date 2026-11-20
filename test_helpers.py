"""Runs test_notebook.py's checks from test_notebook.ipynb and collects the results.

The checks themselves are listed once, in test_notebook.py (CHECKS and
FUNCTIONAL), which the image build also runs with pytest. These helpers
run them in the notebook and record each result in RESULTS as a
(label, status, version or detail, error) row, for the summary table.
"""

import tempfile
from pathlib import Path

RESULTS = []


def reset():
    """Clear RESULTS -- call before a fresh run in a long-lived kernel."""
    RESULTS.clear()


def _record(label, run):
    """Run run(), which returns a module, version, or detail, and record the result."""
    try:
        result = run()
        detail = getattr(result, '__version__', '') if hasattr(result, '__name__') else result
        RESULTS.append((label, 'OK', str(detail or ''), ''))
    except Exception as exc:
        RESULTS.append((label, 'FAIL', '', f'{type(exc).__name__}: {exc}'))


def run_section(section):
    """Run the package and command-line checks listed under `section` in
    test_notebook.py's CHECKS, in order, recording each one."""
    from test_notebook import CHECKS, run_cli_check, run_py_check

    checks = [c for c in CHECKS if c.section == section]
    if not checks:
        sections = list(dict.fromkeys(c.section for c in CHECKS))
        raise ValueError(f'no checks for section {section!r} in test_notebook.py; it has {sections}')
    for check in checks:
        if check.kind == 'cli':
            def run(check=check):
                with tempfile.TemporaryDirectory() as tmp:
                    return run_cli_check(check, tmp)[:80]
            _record(check.label, run)
        else:
            _record(check.label, lambda check=check: run_py_check(check))


def run_functional():
    """Run the functional tests in test_notebook.py's FUNCTIONAL, each in
    its own temporary directory, recording each one."""
    from test_notebook import FUNCTIONAL

    for label, check in FUNCTIONAL:
        def run(check=check):
            with tempfile.TemporaryDirectory() as tmp:
                return check(Path(tmp))
        _record(label, run)
