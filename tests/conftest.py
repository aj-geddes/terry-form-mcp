"""Root conftest.py — pytest configuration and test isolation.

1. Tells pytest to skip the docs/ directory (vendored Ruby gems contain
   Python test files and a conftest.py that import unavailable packages
   like pytest_pyodide).

2. Prevents sys.modules pollution from test_server_enhanced.py.  That
   module stubs fastmcp, terraform_lsp_client, and terry-form-mcp at
   import time so the server module can be loaded without its heavy
   dependencies.  Without cleanup, those stubs poison later test files
   that need the real modules (e.g. test_terraform_lsp_client.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ── 1. Ignore the docs/ tree during collection ──────────────────────────
collect_ignore_glob = ["docs/*"]


# ── 2. Isolate sys.modules stubs injected by test_server_enhanced ───────

# Module names that test_server_enhanced.py may stub.
_STUBBED_MODULES = ("fastmcp", "terraform_lsp_client", "terry-form-mcp")


def pytest_collectstart(collector):
    """Snapshot sys.modules before each collector so we can detect stubs."""
    collector._saved_sysmodules = {
        name: sys.modules.get(name) for name in _STUBBED_MODULES
    }


def pytest_collectreport(report):
    """After collecting test_server_enhanced.py, restore original modules.

    This ensures that stubs injected at import time do not leak into
    subsequent test modules that need the real implementations.
    """
    collector = report.collector if hasattr(report, "collector") else None
    if collector is None:
        return

    saved = getattr(collector, "_saved_sysmodules", None)
    if saved is None:
        return

    # Only restore if this collector actually changed something
    for name in _STUBBED_MODULES:
        current = sys.modules.get(name)
        original = saved.get(name)
        if current is not original:
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
