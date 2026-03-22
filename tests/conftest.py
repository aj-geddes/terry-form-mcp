"""Root conftest.py -- pytest configuration and test isolation.

1. Tells pytest to skip the docs/ directory (vendored Ruby gems contain
   Python test files and a conftest.py that import unavailable packages
   like pytest_pyodide).

2. Prevents sys.modules pollution from test_server_enhanced.py,
   test_config_env_fixes.py, test_frontend_routes_security.py, and
   test_logging_observability_fixes.py. Those modules stub fastmcp,
   terraform_lsp_client, terry-form-mcp, mcp_request_validator, and
   the frontend package at import time so the server/routes modules
   can be loaded without heavy dependencies. Without cleanup those stubs
   poison later test files that need real implementations (e.g.
   test_terraform_lsp_client.py, test_secrets_elimination.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# -- 1. Ignore the docs/ tree during collection --------------------------
collect_ignore_glob = ["docs/*"]


# -- 2. Isolate sys.modules stubs injected by server test modules --------

# Module names that may be stubbed or transiently imported by server tests.
_STUBBED_MODULES = (
    "fastmcp",
    "terraform_lsp_client",
    "terry-form-mcp",
    "mcp_request_validator",
    "server_enhanced_with_lsp",
    # frontend stubs installed by test_frontend_routes_security and
    # test_logging_observability_fixes at import time
    "frontend",
    "frontend.config_manager",
    "frontend.schemas",
    "frontend.routes",
)

# Map collector nodeid -> snapshot taken before that collector ran.
# Used to restore sys.modules after each collector finishes.
_snapshots: dict = {}


def pytest_collectstart(collector) -> None:
    """Snapshot sys.modules before each collector so we can restore stubs."""
    _snapshots[collector.nodeid] = {
        name: sys.modules.get(name) for name in _STUBBED_MODULES
    }


def pytest_collectreport(report) -> None:
    """After collecting a test module, restore original sys.modules entries.

    This ensures that stubs injected at import time do not leak into
    subsequent test modules that need the real implementations.
    """
    saved = _snapshots.pop(report.nodeid, None)
    if saved is None:
        return

    for name in _STUBBED_MODULES:
        current = sys.modules.get(name)
        original = saved.get(name)
        if current is not original:
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
